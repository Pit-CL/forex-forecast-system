"""
USD/CLP Alert System - Real-time monitoring and Slack notifications

Monitors live USD/CLP prices from yfinance and detects sharp movements
across multiple time windows (15min, 1h, 3h, daily).

Author: Senior Developer
Date: 2025-11-20
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests

logger = logging.getLogger(__name__)


class USDCLPAlertSystem:
    """
    Real-time alert system for USD/CLP price movements

    Monitors price changes across multiple time windows and sends
    Slack notifications when thresholds are exceeded.
    """

    # Thresholds based on statistical analysis (P75, P90, P95, P99)
    THRESHOLDS = {
        "15min": {
            "INFO": 0.30,      # ~P75 adjusted for short window
            "WARNING": 0.50,    # ~P85
            "CRITICAL": 0.80,   # ~P95
            "EMERGENCY": 1.20   # ~P99
        },
        "1h": {
            "INFO": 0.50,
            "WARNING": 0.90,
            "CRITICAL": 1.30,
            "EMERGENCY": 2.00
        },
        "3h": {
            "INFO": 0.80,
            "WARNING": 1.40,
            "CRITICAL": 1.80,
            "EMERGENCY": 2.50
        },
        "daily": {
            "INFO": 0.94,      # P75 from expert analysis
            "WARNING": 1.64,    # P90
            "CRITICAL": 2.08,   # P95
            "EMERGENCY": 3.03   # P99
        }
    }

    SEVERITY_EMOJIS = {
        "INFO": "ℹ️",
        "WARNING": "⚠️",
        "CRITICAL": "🔴",
        "EMERGENCY": "🚨"
    }

    SEVERITY_COLORS = {
        "INFO": "#36a64f",      # Green
        "WARNING": "#ff9900",    # Orange
        "CRITICAL": "#ff0000",   # Red
        "EMERGENCY": "#8B0000"   # Dark Red
    }

    def __init__(self, cache_path: Path, slack_webhook_url: Optional[str] = None):
        """
        Initialize alert system

        Args:
            cache_path: Path to JSON file for price history cache
            slack_webhook_url: Slack webhook URL for notifications
        """
        self.cache_path = cache_path
        self.slack_webhook_url = slack_webhook_url
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

    def load_price_cache(self) -> List[Dict]:
        """Load historical prices from cache"""
        if not self.cache_path.exists():
            return []

        try:
            with open(self.cache_path, 'r') as f:
                data = json.load(f)
                return data.get('prices', [])
        except Exception as e:
            logger.error(f"Error loading price cache: {e}")
            return []

    def save_price_cache(self, prices: List[Dict]):
        """Save historical prices to cache"""
        try:
            data = {
                'last_updated': datetime.now().isoformat(),
                'prices': prices[-200:]  # Keep last 200 prices (~ 4 days at 30min intervals)
            }
            with open(self.cache_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving price cache: {e}")

    def add_price_to_cache(self, price: float, timestamp: datetime) -> List[Dict]:
        """Add new price to cache and return updated list"""
        prices = self.load_price_cache()

        prices.append({
            'price': price,
            'timestamp': timestamp.isoformat()
        })

        self.save_price_cache(prices)
        return prices

    def get_price_at_time(self, prices: List[Dict], minutes_ago: int) -> Optional[float]:
        """Get price from N minutes ago"""
        target_time = datetime.now() - timedelta(minutes=minutes_ago)

        # Find closest price within +/- 10 minutes window
        closest_price = None
        min_diff = float('inf')

        for entry in prices:
            entry_time = datetime.fromisoformat(entry['timestamp'])
            diff = abs((entry_time - target_time).total_seconds())

            if diff < min_diff and diff < 600:  # Within 10 minutes
                min_diff = diff
                closest_price = entry['price']

        return closest_price

    def calculate_change_pct(self, current: float, previous: Optional[float]) -> Optional[float]:
        """Calculate percentage change"""
        if previous is None or previous == 0:
            return None
        return ((current - previous) / previous) * 100

    def evaluate_severity(self, change_pct: float, window: str) -> Optional[str]:
        """
        Evaluate severity level based on change percentage and time window

        Returns:
            Severity level (INFO, WARNING, CRITICAL, EMERGENCY) or None
        """
        if window not in self.THRESHOLDS:
            return None

        abs_change = abs(change_pct)
        thresholds = self.THRESHOLDS[window]

        if abs_change >= thresholds["EMERGENCY"]:
            return "EMERGENCY"
        elif abs_change >= thresholds["CRITICAL"]:
            return "CRITICAL"
        elif abs_change >= thresholds["WARNING"]:
            return "WARNING"
        elif abs_change >= thresholds["INFO"]:
            return "INFO"

        return None

    def check_all_windows(self, current_price: float, prices: List[Dict]) -> List[Dict]:
        """
        Check all time windows for significant changes

        Returns:
            List of alerts with window, change_pct, severity
        """
        alerts = []

        windows = [
            ("15min", 15),
            ("1h", 60),
            ("3h", 180),
            ("daily", 1440)  # 24 hours
        ]

        for window_name, minutes in windows:
            previous_price = self.get_price_at_time(prices, minutes)

            if previous_price is None:
                continue

            change_pct = self.calculate_change_pct(current_price, previous_price)

            if change_pct is None:
                continue

            severity = self.evaluate_severity(change_pct, window_name)

            if severity:
                alerts.append({
                    'window': window_name,
                    'change_pct': round(change_pct, 2),
                    'change_abs': round(current_price - previous_price, 2),
                    'current_price': round(current_price, 2),
                    'previous_price': round(previous_price, 2),
                    'severity': severity,
                    'threshold': self.THRESHOLDS[window_name][severity]
                })

        return alerts

    def send_slack_alert(self, alerts: List[Dict], current_price: float):
        """Send formatted alert to Slack"""
        if not self.slack_webhook_url or not alerts:
            return

        # Get highest severity alert
        severity_order = ["INFO", "WARNING", "CRITICAL", "EMERGENCY"]
        highest_alert = max(alerts, key=lambda x: severity_order.index(x['severity']))

        severity = highest_alert['severity']
        emoji = self.SEVERITY_EMOJIS[severity]
        color = self.SEVERITY_COLORS[severity]

        # Build message
        title = f"{emoji} ALERTA {severity}: USD/CLP"

        # Main alert info
        main_alert = highest_alert
        change_direction = "+" if main_alert['change_pct'] > 0 else ""

        description = f"*Precio actual:* ${current_price:.2f}\n"
        description += f"*Cambio {main_alert['window']}:* {change_direction}{main_alert['change_pct']:.2f}% "
        description += f"(${change_direction}{main_alert['change_abs']:.2f})\n"
        description += f"*Precio anterior:* ${main_alert['previous_price']:.2f}\n"
        description += f"*Severidad:* {severity} (>{main_alert['threshold']:.2f}%)\n"

        # Add other alerts if any
        if len(alerts) > 1:
            description += f"\n*Otras ventanas alertadas:*\n"
            for alert in alerts:
                if alert != main_alert:
                    change_dir = "+" if alert['change_pct'] > 0 else ""
                    description += f"• {alert['window']}: {change_dir}{alert['change_pct']:.2f}% ({alert['severity']})\n"

        # Expected frequency (based on statistical analysis)
        frequency_map = {
            "INFO": "~15 días/mes",
            "WARNING": "~1-2 veces/mes",
            "CRITICAL": "~1 cada 2-3 meses",
            "EMERGENCY": "~1-2 veces/año"
        }
        description += f"\n*Frecuencia esperada:* {frequency_map.get(severity, 'N/A')}"

        payload = {
            "attachments": [{
                "color": color,
                "title": title,
                "text": description,
                "footer": "Forex Forecast System - Real-time Monitoring",
                "ts": int(datetime.now().timestamp())
            }]
        }

        try:
            response = requests.post(
                self.slack_webhook_url,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                logger.info(f"Slack alert sent successfully: {severity}")
            else:
                logger.error(f"Slack alert failed: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Error sending Slack alert: {e}")

    def monitor(self, current_price: float, timestamp: datetime) -> Dict:
        """
        Main monitoring function

        Args:
            current_price: Current USD/CLP price from yfinance
            timestamp: Timestamp of the price

        Returns:
            Dictionary with monitoring results and alerts
        """
        logger.info(f"Monitoring USD/CLP: ${current_price:.2f} at {timestamp}")

        # Load historical prices
        prices = self.load_price_cache()

        # Check for alerts across all time windows
        alerts = self.check_all_windows(current_price, prices)

        # Add current price to cache
        self.add_price_to_cache(current_price, timestamp)

        # Send Slack notification if alerts exist
        if alerts:
            logger.warning(f"ALERTS DETECTED: {len(alerts)} window(s)")
            for alert in alerts:
                logger.warning(f"  {alert['window']}: {alert['change_pct']:+.2f}% ({alert['severity']})")

            self.send_slack_alert(alerts, current_price)
        else:
            logger.info("No alerts - all changes within normal range")

        return {
            'timestamp': timestamp.isoformat(),
            'current_price': current_price,
            'alerts': alerts,
            'cache_size': len(prices) + 1
        }
