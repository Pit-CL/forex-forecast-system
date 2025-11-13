#!/usr/bin/env python3
"""
Test Regime Detector with Historical Data.

This script tests the MarketRegimeDetector with historical USD/CLP and copper data
to verify regime detection logic works correctly.

Usage:
    python examples/test_regime_detector.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from forex_core.mlops.regime_detector import MarketRegimeDetector

console = Console()


def generate_test_data():
    """
    Generate test USD/CLP and copper price series.

    Uses realistic patterns for testing:
    - Normal period (low volatility)
    - High volatility period
    - Copper shock (sudden price change)
    - BCCh meeting proximity

    Returns:
        Tuple of (usdclp_series, copper_series)
    """
    # Generate 360 days of data (enough for 90-day lookback)
    dates = pd.date_range(end=datetime.now(), periods=360, freq="D")

    # Scenario 1: Normal market (first 150 days)
    # USD/CLP around 800 with 0.3% daily volatility
    normal_period = 800 + np.random.normal(0, 2.4, 150)  # 0.3% of 800

    # Scenario 2: High volatility (days 150-210)
    # USD/CLP with 1.5% daily volatility (5x normal)
    high_vol_period = normal_period[-1] + np.cumsum(np.random.normal(0, 12, 60))  # 1.5% of 800

    # Scenario 3: Copper shock (days 210-270)
    # Return to normal vol but with copper correlation break
    shock_period = high_vol_period[-1] + np.cumsum(np.random.normal(0, 2.4, 60))

    # Scenario 4: Normal recovery (days 270-360)
    recovery_period = shock_period[-1] + np.cumsum(np.random.normal(0, 2.4, 90))

    # Combine all periods
    usdclp_values = np.concatenate([
        normal_period,
        high_vol_period,
        shock_period,
        recovery_period
    ])

    # Copper prices (normally inversely correlated with USD/CLP)
    # Correlation ~-0.65
    copper_base = 4.0 - (usdclp_values - 800) * 0.003  # Inverse relationship

    # Add noise and shock
    copper_values = copper_base + np.random.normal(0, 0.1, 360)

    # Copper shock at day 210: sudden +8% increase
    copper_values[210:] += 0.32  # 8% of 4.0

    # Create series
    usdclp_series = pd.Series(usdclp_values, index=dates, name="USD/CLP")
    copper_series = pd.Series(copper_values, index=dates, name="Copper")

    return usdclp_series, copper_series


def test_regime_detector():
    """Test regime detector with various scenarios."""
    console.print("\n[bold cyan]Testing Market Regime Detector[/bold cyan]\n")

    # Generate test data
    usdclp_series, copper_series = generate_test_data()

    console.print("[yellow]Generated Test Data:[/yellow]")
    console.print(f"  USD/CLP: {len(usdclp_series)} days")
    console.print(f"  Copper:  {len(copper_series)} days")
    console.print(f"  Range:   {usdclp_series.index[0].date()} to {usdclp_series.index[-1].date()}")
    console.print()

    # Initialize detector
    detector = MarketRegimeDetector(
        lookback_days=90,
        vol_threshold_high=2.0,
        copper_threshold=5.0,
        bcch_meeting_days=3,
    )

    # Test different time windows (must be at least 90 days for lookback)
    test_scenarios = [
        ("Normal Period", usdclp_series[:150], copper_series[:150]),
        ("High Volatility", usdclp_series[120:210], copper_series[120:210]),
        ("Copper Shock", usdclp_series[180:270], copper_series[180:270]),
        ("Recent Period", usdclp_series[-90:], copper_series[-90:]),
    ]

    results_table = Table(title="Regime Detection Results", show_header=True)
    results_table.add_column("Scenario", style="cyan")
    results_table.add_column("Regime", style="bold")
    results_table.add_column("Confidence", justify="right")
    results_table.add_column("Vol Z-score", justify="right")
    results_table.add_column("Vol Multiplier", justify="right")

    console.print("[yellow]Running Regime Detection Tests...[/yellow]\n")

    for scenario_name, usdclp_window, copper_window in test_scenarios:
        # Detect regime
        report = detector.detect(usdclp_window, copper_window)

        # Color code by regime
        if report.regime.value == "normal":
            regime_style = "green"
        elif report.regime.value == "high_vol":
            regime_style = "yellow"
        elif report.regime.value == "copper_shock":
            regime_style = "orange1"
        elif report.regime.value == "bcch_intervention":
            regime_style = "red"
        else:
            regime_style = "dim"

        results_table.add_row(
            scenario_name,
            f"[{regime_style}]{report.regime.value.upper()}[/{regime_style}]",
            f"{report.confidence:.0%}",
            f"{report.signals.vol_z_score:.2f}",
            f"{report.volatility_multiplier:.2f}x",
        )

        # Show detailed signals for interesting cases
        if report.regime.value != "normal":
            console.print(f"\n[bold]{scenario_name} - Detailed Signals:[/bold]")

            signals_table = Table(show_header=False, box=None)
            signals_table.add_column("Signal", style="dim")
            signals_table.add_column("Value")

            signals_table.add_row("Volatility Z-score", f"{report.signals.vol_z_score:.2f}")
            signals_table.add_row("Volatility Percentile", f"{report.signals.vol_percentile:.1f}%")

            if report.signals.copper_change is not None:
                signals_table.add_row("Copper 30d Change", f"{report.signals.copper_change:+.2%}")

            if report.signals.correlation_break is not None:
                signals_table.add_row("Correlation Break", f"{report.signals.correlation_break}")

            if report.signals.bcch_meeting_proximity is not None:
                signals_table.add_row("BCCh Meeting Days", f"{report.signals.bcch_meeting_proximity}")

            console.print(signals_table)

            console.print(Panel(
                report.recommendation,
                title=f"Recommendation ({report.regime.value.upper()})",
                border_style=regime_style
            ))
            console.print()

    console.print(results_table)
    console.print()


def test_bcch_meeting_detection():
    """Test BCCh meeting proximity detection."""
    console.print("[bold cyan]Testing BCCh Meeting Proximity Detection[/bold cyan]\n")

    detector = MarketRegimeDetector()

    # Test dates around known BCCh meetings
    # BCCh meets 3rd Tuesday of each month
    test_dates = [
        datetime(2025, 11, 18),  # 3rd Tuesday November 2025
        datetime(2025, 11, 17),  # Day before
        datetime(2025, 11, 19),  # Day after
        datetime(2025, 11, 11),  # Week before
        datetime(2025, 11, 25),  # Week after
    ]

    proximity_table = Table(show_header=True)
    proximity_table.add_column("Date", style="cyan")
    proximity_table.add_column("Days to Meeting", justify="right")
    proximity_table.add_column("Within Window", justify="center")

    for test_date in test_dates:
        days_to_meeting = detector._get_bcch_meeting_proximity()
        within_window = abs(days_to_meeting) <= detector.bcch_meeting_days

        proximity_table.add_row(
            test_date.strftime("%Y-%m-%d (%A)"),
            str(days_to_meeting) if days_to_meeting is not None else "N/A",
            "✓" if within_window else "○",
        )

    console.print(proximity_table)
    console.print()


def test_volatility_multiplier():
    """Test volatility multiplier calculation."""
    console.print("[bold cyan]Testing Volatility Multiplier Calculation[/bold cyan]\n")

    from forex_core.mlops.regime_detector import MarketRegime, RegimeSignals

    detector = MarketRegimeDetector()

    # Test different regime configurations
    # RegimeSignals(vol_z_score, vol_percentile, copper_change, usdclp_change, correlation_break, bcch_meeting_proximity)
    test_cases = [
        (MarketRegime.NORMAL, RegimeSignals(0.5, 30, 0.01, 0.01, False, 10)),
        (MarketRegime.HIGH_VOL, RegimeSignals(2.5, 85, 0.02, 0.03, False, 10)),
        (MarketRegime.HIGH_VOL, RegimeSignals(3.5, 95, 0.01, 0.04, False, 10)),
        (MarketRegime.COPPER_SHOCK, RegimeSignals(1.5, 70, 0.08, 0.03, True, 10)),
        (MarketRegime.BCCH_INTERVENTION, RegimeSignals(3.0, 90, 0.02, 0.05, False, 1)),
    ]

    mult_table = Table(show_header=True)
    mult_table.add_column("Regime", style="cyan")
    mult_table.add_column("Vol Z-score", justify="right")
    mult_table.add_column("Percentile", justify="right")
    mult_table.add_column("Multiplier", justify="right")
    mult_table.add_column("CI Impact", justify="right", style="dim")

    for regime, signals in test_cases:
        multiplier = detector._calculate_volatility_multiplier(regime, signals)

        # Example: if base CI width is 20 points
        base_width = 20.0
        adjusted_width = base_width * multiplier
        impact = adjusted_width - base_width

        mult_table.add_row(
            regime.value.upper(),
            f"{signals.vol_z_score:.1f}",
            f"{signals.vol_percentile:.0f}%",
            f"{multiplier:.2f}x",
            f"+{impact:.1f} pts",
        )

    console.print(mult_table)
    console.print("\n[dim]Example based on 20-point base CI width[/dim]\n")


def main():
    """Run all regime detector tests."""
    try:
        # Test 1: Main regime detection
        test_regime_detector()

        # Test 2: BCCh meeting detection
        test_bcch_meeting_detection()

        # Test 3: Volatility multiplier
        test_volatility_multiplier()

        console.print("[green bold]✓ All tests completed successfully![/green bold]\n")

    except Exception as e:
        console.print(f"\n[red bold]✗ Test failed: {e}[/red bold]\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
