#!/usr/bin/env python3
"""
Demonstration script for Market Shock Detector.

This script shows how to use the MarketShockDetector to identify
market events that could impact USD/CLP forecasts.

Usage:
    python examples/test_market_shock_detector.py
"""

import sys
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forex_core.alerts import (
    Alert,
    AlertSeverity,
    AlertType,
    MarketShockDetector,
)


def create_sample_data(scenario: str = "normal") -> pd.DataFrame:
    """
    Create sample market data for demonstration.

    Args:
        scenario: Type of scenario to simulate
            - "normal": Normal market conditions
            - "copper_crash": Major copper price decline
            - "vix_spike": Market stress event
            - "multiple": Multiple concurrent shocks

    Returns:
        DataFrame with market data
    """
    dates = pd.date_range(start="2025-10-01", end="2025-11-29", freq="D")
    n = len(dates)

    # Base data (normal conditions)
    np.random.seed(42)
    data = pd.DataFrame(
        {
            "date": dates,
            "usdclp": 950 + np.cumsum(np.random.randn(n) * 2),  # Random walk
            "copper_price": 4.0 + np.random.randn(n) * 0.05,
            "dxy": 103.0 + np.random.randn(n) * 0.3,
            "vix": 15.0 + np.abs(np.random.randn(n) * 1.5),
            "tpm": np.ones(n) * 5.75,
        }
    )

    # Apply scenario-specific shocks
    if scenario == "copper_crash":
        # Simulate major copper decline in last week
        data.loc[data.index[-7:], "copper_price"] = np.linspace(
            4.0, 3.5, 7  # -12.5% decline over week
        )
        data.loc[data.index[-1], "copper_price"] = 3.45  # Additional -7% on last day

    elif scenario == "vix_spike":
        # Simulate market stress event
        data.loc[data.index[-3:], "vix"] = [18, 28, 36]  # Rapid VIX increase
        data.loc[data.index[-1], "dxy"] = 106.5  # Flight to USD

    elif scenario == "multiple":
        # Multiple concurrent shocks (worst case)
        data.loc[data.index[-1], "usdclp"] = (
            data.loc[data.index[-2], "usdclp"] * 1.03
        )  # +3% spike
        data.loc[data.index[-1], "copper_price"] = 3.6  # -10% copper
        data.loc[data.index[-1], "vix"] = 38  # High VIX
        data.loc[data.index[-1], "dxy"] = 107  # Strong USD
        data.loc[data.index[-1], "tpm"] = 6.50  # +75bp TPM surprise

    # Add optional intraday data
    data["usdclp_high"] = data["usdclp"] * (1 + np.random.rand(n) * 0.01)
    data["usdclp_low"] = data["usdclp"] * (1 - np.random.rand(n) * 0.01)

    return data


def print_alert(alert: Alert, index: int = 0) -> None:
    """Pretty print an alert."""
    severity_emoji = {
        AlertSeverity.INFO: "ℹ️",
        AlertSeverity.WARNING: "⚠️",
        AlertSeverity.CRITICAL: "🚨",
    }

    print(f"\n{index + 1}. {severity_emoji[alert.severity]} {alert.severity.value.upper()}")
    print(f"   Type: {alert.alert_type.value}")
    print(f"   Message: {alert.message}")
    print(f"   Timestamp: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

    if alert.metrics:
        print("   Metrics:")
        for key, value in alert.metrics.items():
            if isinstance(value, float):
                print(f"     - {key}: {value:.2f}")
            else:
                print(f"     - {key}: {value}")

    if alert.recommendation:
        print(f"   ⚡ Recommendation: {alert.recommendation}")


def demo_normal_conditions():
    """Demonstrate detector with normal market conditions."""
    print("\n" + "=" * 80)
    print("SCENARIO 1: Normal Market Conditions")
    print("=" * 80)

    detector = MarketShockDetector()
    data = create_sample_data("normal")

    print(f"\nData range: {data['date'].min()} to {data['date'].max()}")
    print(f"Latest USD/CLP: {data['usdclp'].iloc[-1]:.2f}")
    print(f"Latest Copper: ${data['copper_price'].iloc[-1]:.2f}/lb")
    print(f"Latest DXY: {data['dxy'].iloc[-1]:.2f}")
    print(f"Latest VIX: {data['vix'].iloc[-1]:.1f}")

    alerts = detector.detect_all(data)

    if not alerts:
        print("\n✅ No alerts detected - Market conditions are normal")
    else:
        print(f"\n📊 Detected {len(alerts)} alert(s):")
        for i, alert in enumerate(alerts):
            print_alert(alert, i)

    summary = detector.get_alert_summary(alerts)
    print(f"\n📧 Email Subject: {summary}")


def demo_copper_crash():
    """Demonstrate detector with copper price crash."""
    print("\n" + "=" * 80)
    print("SCENARIO 2: Copper Price Crash")
    print("=" * 80)

    detector = MarketShockDetector()
    data = create_sample_data("copper_crash")

    print(f"\nData range: {data['date'].min()} to {data['date'].max()}")
    print(f"Copper 7 days ago: ${data['copper_price'].iloc[-7]:.2f}/lb")
    print(f"Latest Copper: ${data['copper_price'].iloc[-1]:.2f}/lb")
    print(
        f"Weekly change: {((data['copper_price'].iloc[-1] / data['copper_price'].iloc[-7]) - 1) * 100:.1f}%"
    )

    alerts = detector.detect_all(data)

    print(f"\n🔴 Detected {len(alerts)} alert(s):")
    for i, alert in enumerate(alerts):
        print_alert(alert, i)

    # Group by severity
    grouped = detector.get_alerts_by_severity(alerts)
    print(
        f"\nBy severity: CRITICAL={len(grouped[AlertSeverity.CRITICAL])}, "
        f"WARNING={len(grouped[AlertSeverity.WARNING])}, "
        f"INFO={len(grouped[AlertSeverity.INFO])}"
    )

    summary = detector.get_alert_summary(alerts)
    print(f"\n📧 Email Subject: {summary}")


def demo_vix_spike():
    """Demonstrate detector with VIX spike."""
    print("\n" + "=" * 80)
    print("SCENARIO 3: VIX Fear Spike")
    print("=" * 80)

    detector = MarketShockDetector()
    data = create_sample_data("vix_spike")

    print(f"\nData range: {data['date'].min()} to {data['date'].max()}")
    print(f"VIX 3 days ago: {data['vix'].iloc[-3]:.1f}")
    print(f"Latest VIX: {data['vix'].iloc[-1]:.1f}")
    print(f"Latest DXY: {data['dxy'].iloc[-1]:.2f}")

    alerts = detector.detect_all(data)

    print(f"\n🔴 Detected {len(alerts)} alert(s):")
    for i, alert in enumerate(alerts):
        print_alert(alert, i)

    summary = detector.get_alert_summary(alerts)
    print(f"\n📧 Email Subject: {summary}")


def demo_multiple_shocks():
    """Demonstrate detector with multiple concurrent shocks."""
    print("\n" + "=" * 80)
    print("SCENARIO 4: Multiple Concurrent Shocks (Worst Case)")
    print("=" * 80)

    detector = MarketShockDetector()
    data = create_sample_data("multiple")

    print(f"\nData range: {data['date'].min()} to {data['date'].max()}")
    print("\nLatest values:")
    print(f"  USD/CLP: {data['usdclp'].iloc[-1]:.2f} (prev: {data['usdclp'].iloc[-2]:.2f})")
    print(
        f"  Copper: ${data['copper_price'].iloc[-1]:.2f}/lb (prev: ${data['copper_price'].iloc[-2]:.2f})"
    )
    print(f"  DXY: {data['dxy'].iloc[-1]:.2f} (prev: {data['dxy'].iloc[-2]:.2f})")
    print(f"  VIX: {data['vix'].iloc[-1]:.1f} (prev: {data['vix'].iloc[-2]:.1f})")
    print(f"  TPM: {data['tpm'].iloc[-1]:.2f}% (prev: {data['tpm'].iloc[-2]:.2f}%)")

    alerts = detector.detect_all(data)

    print(f"\n🚨 CRITICAL SITUATION: Detected {len(alerts)} alert(s):")
    for i, alert in enumerate(alerts):
        print_alert(alert, i)

    # Group by severity
    grouped = detector.get_alerts_by_severity(alerts)
    critical_count = len(grouped[AlertSeverity.CRITICAL])
    warning_count = len(grouped[AlertSeverity.WARNING])

    if critical_count > 0:
        print(f"\n⚠️  URGENT: {critical_count} critical alert(s) require immediate action!")

    summary = detector.get_alert_summary(alerts)
    print(f"\n📧 Email Subject: {summary}")


def demo_custom_thresholds():
    """Demonstrate custom threshold configuration."""
    print("\n" + "=" * 80)
    print("SCENARIO 5: Custom Thresholds (Conservative vs Sensitive)")
    print("=" * 80)

    # Create data with moderate changes
    data = create_sample_data("normal")
    data.loc[data.index[-1], "usdclp"] = (
        data.loc[data.index[-2], "usdclp"] * 1.018
    )  # +1.8% change

    print(f"\nUSD/CLP change: +1.8% (between default 2% and sensitive 1.5%)")

    # Default detector
    print("\n--- Default Detector (2% threshold) ---")
    default_detector = MarketShockDetector()
    default_alerts = default_detector.detect_all(data)
    print(
        f"Alerts: {len(default_alerts)} (should be 0, since 1.8% < 2% threshold)"
    )

    # Sensitive detector
    print("\n--- Sensitive Detector (1.5% threshold) ---")
    sensitive_detector = MarketShockDetector(usdclp_daily_threshold=1.5)
    sensitive_alerts = sensitive_detector.detect_all(data)
    print(
        f"Alerts: {len(sensitive_alerts)} (should be 1+, since 1.8% > 1.5% threshold)"
    )

    if sensitive_alerts:
        for i, alert in enumerate(sensitive_alerts):
            print_alert(alert, i)


def main():
    """Run all demonstration scenarios."""
    print("\n" + "#" * 80)
    print("# Market Shock Detector - Demonstration")
    print("#" * 80)

    try:
        demo_normal_conditions()
        demo_copper_crash()
        demo_vix_spike()
        demo_multiple_shocks()
        demo_custom_thresholds()

        print("\n" + "=" * 80)
        print("DEMONSTRATION COMPLETE ✅")
        print("=" * 80)
        print("\nKey Takeaways:")
        print("1. Detector identifies 6 types of market shocks affecting USD/CLP")
        print("2. Severity levels (INFO/WARNING/CRITICAL) prioritize urgent events")
        print("3. Thresholds are configurable to tune sensitivity")
        print("4. Recommendations provided for critical alerts")
        print("5. Ready for production integration with email system")

    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
