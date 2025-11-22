#!/usr/bin/env python3
"""
Live USD/CLP Alert Monitor - Standalone Version

Fetches real-time USD/CLP price from yfinance and monitors for sharp movements.
Runs every 30 minutes during market hours (9 AM - 6 PM Chile, Mon-Fri).

Author: Senior Developer
Date: 2025-11-20
"""
import sys
import os
import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed. Run: pip install yfinance")
    sys.exit(1)


# Configuration
BASE_PATH = Path("/opt/forex-forecast-system")
CACHE_PATH = BASE_PATH / "data" / "live_prices_cache.json"
LOG_PATH = BASE_PATH / "logs" / "live_alerts.log"
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

# Thresholds based on statistical analysis (P75, P90, P95, P99)
THRESHOLDS = {
    "15min": {"INFO": 0.30, "WARNING": 0.50, "CRITICAL": 0.80, "EMERGENCY": 1.20},
    "1h": {"INFO": 0.50, "WARNING": 0.90, "CRITICAL": 1.30, "EMERGENCY": 2.00},
    "3h": {"INFO": 0.80, "WARNING": 1.40, "CRITICAL": 1.80, "EMERGENCY": 2.50},
    "daily": {"INFO": 0.94, "WARNING": 1.64, "CRITICAL": 2.08, "EMERGENCY": 3.03}
}

SEVERITY_EMOJIS = {"INFO": "ℹ️", "WARNING": "⚠️", "CRITICAL": "🔴", "EMERGENCY": "🚨"}
SEVERITY_COLORS = {"INFO": "#36a64f", "WARNING": "#ff9900", "CRITICAL": "#ff0000", "EMERGENCY": "#8B0000"}

# Configure logging
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def is_market_hours() -> bool:
    """Check if current time is within market hours (9 AM - 6 PM Chile)"""
    try:
        from zoneinfo import ZoneInfo
        chile_tz = ZoneInfo("America/Santiago")
    except:
        # Fallback: assume UTC-3
        from datetime import timezone
        chile_tz = timezone(timedelta(hours=-3))

    now = datetime.now(chile_tz)
    if now.weekday() >= 5:  # Saturday or Sunday
        return False
    if now.hour < 9 or now.hour >= 18:
        return False
    return True


def load_price_cache() -> List[Dict]:
    """Load historical prices from cache"""
    if not CACHE_PATH.exists():
        return []
    try:
        with open(CACHE_PATH, 'r') as f:
            data = json.load(f)
            return data.get('prices', [])
    except Exception as e:
        logger.error(f"Error loading cache: {e}")
        return []


def save_price_cache(prices: List[Dict]):
    """Save historical prices to cache"""
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {'last_updated': datetime.now().isoformat(), 'prices': prices[-200:]}
        with open(CACHE_PATH, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving cache: {e}")


def get_price_at_time(prices: List[Dict], minutes_ago: int) -> Optional[float]:
    """Get price from N minutes ago"""
    target_time = datetime.now() - timedelta(minutes=minutes_ago)
    closest_price, min_diff = None, float('inf')

    for entry in prices:
        entry_time = datetime.fromisoformat(entry['timestamp'])
        diff = abs((entry_time - target_time).total_seconds())
        if diff < min_diff and diff < 600:  # Within 10 minutes
            min_diff, closest_price = diff, entry['price']
    return closest_price


def calculate_change_pct(current: float, previous: Optional[float]) -> Optional[float]:
    """Calculate percentage change"""
    if previous is None or previous == 0:
        return None
    return ((current - previous) / previous) * 100


def evaluate_severity(change_pct: float, window: str) -> Optional[str]:
    """Evaluate severity level"""
    if window not in THRESHOLDS:
        return None
    abs_change = abs(change_pct)
    thresholds = THRESHOLDS[window]

    if abs_change >= thresholds["EMERGENCY"]: return "EMERGENCY"
    elif abs_change >= thresholds["CRITICAL"]: return "CRITICAL"
    elif abs_change >= thresholds["WARNING"]: return "WARNING"
    elif abs_change >= thresholds["INFO"]: return "INFO"
    return None


def check_all_windows(current_price: float, prices: List[Dict]) -> List[Dict]:
    """Check all time windows for significant changes"""
    alerts = []
    windows = [("15min", 15), ("1h", 60), ("3h", 180), ("daily", 1440)]

    for window_name, minutes in windows:
        previous_price = get_price_at_time(prices, minutes)
        if previous_price is None:
            continue

        change_pct = calculate_change_pct(current_price, previous_price)
        if change_pct is None:
            continue

        severity = evaluate_severity(change_pct, window_name)
        if severity:
            alerts.append({
                'window': window_name,
                'change_pct': round(change_pct, 2),
                'change_abs': round(current_price - previous_price, 2),
                'current_price': round(current_price, 2),
                'previous_price': round(previous_price, 2),
                'severity': severity,
                'threshold': THRESHOLDS[window_name][severity]
            })
    return alerts


def send_slack_alert(alerts: List[Dict], current_price: float):
    """Send formatted alert to Slack"""
    if not alerts:
        return

    severity_order = ["INFO", "WARNING", "CRITICAL", "EMERGENCY"]
    highest_alert = max(alerts, key=lambda x: severity_order.index(x['severity']))

    severity = highest_alert['severity']
    emoji, color = SEVERITY_EMOJIS[severity], SEVERITY_COLORS[severity]

    title = f"{emoji} ALERTA {severity}: USD/CLP"
    main_alert = highest_alert
    change_dir = "+" if main_alert['change_pct'] > 0 else ""

    description = f"*Precio actual:* ${current_price:.2f}\n"
    description += f"*Cambio {main_alert['window']}:* {change_dir}{main_alert['change_pct']:.2f}% "
    description += f"(${change_dir}{main_alert['change_abs']:.2f})\n"
    description += f"*Precio anterior:* ${main_alert['previous_price']:.2f}\n"
    description += f"*Severidad:* {severity} (>{main_alert['threshold']:.2f}%)\n"

    if len(alerts) > 1:
        description += "\n*Otras ventanas alertadas:*\n"
        for alert in alerts:
            if alert != main_alert:
                cd = "+" if alert['change_pct'] > 0 else ""
                description += f"• {alert['window']}: {cd}{alert['change_pct']:.2f}% ({alert['severity']})\n"

    frequency_map = {
        "INFO": "~15 días/mes", "WARNING": "~1-2 veces/mes",
        "CRITICAL": "~1 cada 2-3 meses", "EMERGENCY": "~1-2 veces/año"
    }
    description += f"\n*Frecuencia esperada:* {frequency_map.get(severity, 'N/A')}"

    payload = {
        "attachments": [{
            "color": color, "title": title, "text": description,
            "footer": "Forex Forecast System - Real-time Monitoring",
            "ts": int(datetime.now().timestamp())
        }]
    }

    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info(f"✅ Slack alert sent: {severity}")
        else:
            logger.error(f"❌ Slack alert failed: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Error sending Slack alert: {e}")


def get_current_usdclp_price() -> tuple:
    """Fetch current USD/CLP price from yfinance"""
    try:
        ticker = yf.Ticker("CLP=X")
        info = ticker.info
        price = info.get('regularMarketPrice') or info.get('currentPrice') or info.get('previousClose')

        if price and price > 0:
            logger.info(f"✅ Fetched USD/CLP: ${price:.2f}")
            return float(price), datetime.now()
        else:
            logger.warning("⚠️  yfinance returned invalid price")
            return None, None
    except Exception as e:
        logger.error(f"❌ Error fetching price: {e}")
        return None, None


def main():
    """Main monitoring loop"""
    logger.info("=" * 80)
    logger.info("USD/CLP LIVE ALERT MONITOR - Starting")
    logger.info("=" * 80)

    # Check market hours
    if not is_market_hours():
        logger.info("⏰ Outside market hours (Mon-Fri, 9 AM - 6 PM Chile)")
        return 0

    # Fetch current price
    current_price, timestamp = get_current_usdclp_price()
    if current_price is None:
        logger.error("❌ Failed to fetch price - aborting")
        return 1

    # Load cache and check for alerts
    prices = load_price_cache()
    alerts = check_all_windows(current_price, prices)

    # Save current price to cache
    prices.append({'price': current_price, 'timestamp': timestamp.isoformat()})
    save_price_cache(prices)

    # Log and send alerts
    logger.info(f"📊 Monitoring complete:")
    logger.info(f"   Price: ${current_price:.2f}")
    logger.info(f"   Alerts: {len(alerts)}")
    logger.info(f"   Cache size: {len(prices)} prices")

    if alerts:
        logger.warning("🚨 ALERTS DETECTED:")
        for alert in alerts:
            logger.warning(
                f"   [{alert['severity']}] {alert['window']}: "
                f"{alert['change_pct']:+.2f}% (threshold: >{alert['threshold']:.2f}%)"
            )
        send_slack_alert(alerts, current_price)
    else:
        logger.info("✅ No alerts - all changes within normal range")

    logger.info("=" * 80)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"❌ Unexpected error: {e}")
        sys.exit(1)
