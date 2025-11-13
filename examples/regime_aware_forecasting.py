#!/usr/bin/env python3
"""
Regime-Aware Forecasting Example.

This script demonstrates how to integrate market regime detection
with forecasting to adjust confidence intervals dynamically.

The regime detector analyzes market conditions and returns a
volatility multiplier (1.0-2.5x) to widen CIs during turbulent periods:

- NORMAL regime: 1.0x (no adjustment)
- HIGH_VOL regime: 1.2-1.9x (based on z-score)
- COPPER_SHOCK regime: 1.5x (fixed adjustment)
- BCCH_INTERVENTION regime: 2.0x (maximum caution)

Usage:
    python examples/regime_aware_forecasting.py
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


def generate_historical_data():
    """
    Generate sample USD/CLP and copper historical data.

    Returns:
        Tuple of (usdclp_series, copper_series)
    """
    # Generate 120 days of historical data for baseline
    dates = pd.date_range(end=datetime.now(), periods=120, freq="D")

    # USD/CLP with some volatility patterns
    base_price = 800
    trend = np.linspace(0, 20, 120)  # Upward trend
    volatility = np.random.normal(0, 3, 120)
    usdclp = base_price + trend + volatility

    # Add a volatility spike in recent days (last 10 days)
    usdclp[-10:] += np.random.normal(0, 10, 10)

    # Copper prices (inversely correlated)
    copper_base = 4.0
    copper = copper_base - (usdclp - 800) * 0.003 + np.random.normal(0, 0.1, 120)

    usdclp_series = pd.Series(usdclp, index=dates, name="USD/CLP")
    copper_series = pd.Series(copper, index=dates, name="Copper")

    return usdclp_series, copper_series


def simulate_forecast_with_regime(
    current_price: float,
    base_ci_width: float,
    regime_multiplier: float,
) -> dict:
    """
    Simulate a forecast with regime-adjusted confidence intervals.

    Args:
        current_price: Current USD/CLP price.
        base_ci_width: Base CI width before regime adjustment.
        regime_multiplier: Multiplier from regime detector (1.0-2.5x).

    Returns:
        Dictionary with forecast details.
    """
    # Simple forecast: current price with small drift
    forecast_mean = current_price + np.random.normal(0, 5)

    # Adjust CI width based on regime
    adjusted_ci_width = base_ci_width * regime_multiplier

    ci95_low = forecast_mean - adjusted_ci_width
    ci95_high = forecast_mean + adjusted_ci_width

    return {
        "mean": forecast_mean,
        "ci95_low": ci95_low,
        "ci95_high": ci95_high,
        "base_width": base_ci_width,
        "adjusted_width": adjusted_ci_width,
        "multiplier": regime_multiplier,
    }


def main():
    """Demonstrate regime-aware forecasting."""
    console.print("\n[bold cyan]Regime-Aware Forecasting Demo[/bold cyan]\n")

    # Step 1: Load historical data
    console.print("[yellow]Step 1: Loading Historical Data[/yellow]")
    usdclp_series, copper_series = generate_historical_data()

    current_price = usdclp_series.iloc[-1]
    console.print(f"  Current USD/CLP: {current_price:.2f}")
    console.print(f"  Data range: {usdclp_series.index[0].date()} to {usdclp_series.index[-1].date()}")
    console.print(f"  Days of history: {len(usdclp_series)}\n")

    # Step 2: Detect market regime
    console.print("[yellow]Step 2: Detecting Market Regime[/yellow]")
    detector = MarketRegimeDetector(
        lookback_days=90,
        vol_threshold_high=2.0,
        copper_threshold=5.0,
    )

    report = detector.detect(usdclp_series, copper_series)

    # Display regime detection results
    regime_color = {
        "normal": "green",
        "high_vol": "yellow",
        "copper_shock": "orange1",
        "bcch_intervention": "red",
        "unknown": "dim",
    }.get(report.regime.value, "white")

    console.print(Panel(
        f"[bold]Detected Regime:[/bold] [{regime_color}]{report.regime.value.upper()}[/{regime_color}]\n"
        f"[bold]Confidence:[/bold] {report.confidence:.1f}%\n"
        f"[bold]Volatility Multiplier:[/bold] {report.volatility_multiplier:.2f}x\n\n"
        f"[dim]{report.recommendation}[/dim]",
        title="Regime Detection",
        border_style=regime_color,
    ))

    # Display signals
    console.print("[yellow]Regime Signals:[/yellow]")
    signals_table = Table(show_header=False, box=None)
    signals_table.add_column("Signal", style="cyan")
    signals_table.add_column("Value")

    signals_table.add_row("Volatility Z-score", f"{report.signals.vol_z_score:.2f}")
    signals_table.add_row("Volatility Percentile", f"{report.signals.vol_percentile:.1f}%")
    signals_table.add_row("USD/CLP 5d Change", f"{report.signals.usdclp_change:+.2%}")

    if report.signals.copper_change is not None:
        signals_table.add_row("Copper 5d Change", f"{report.signals.copper_change:+.2%}")

    signals_table.add_row("Correlation Break", str(report.signals.correlation_break))
    signals_table.add_row("BCCh Meeting Days", str(report.signals.bcch_meeting_proximity))

    console.print(signals_table)
    console.print()

    # Step 3: Generate forecast with regime adjustment
    console.print("[yellow]Step 3: Generating Regime-Adjusted Forecast[/yellow]\n")

    # Base CI width (from historical model performance)
    base_ci_width = 20.0  # Example: ±20 pesos

    # Generate forecasts with and without regime adjustment
    forecast_base = simulate_forecast_with_regime(current_price, base_ci_width, 1.0)
    forecast_adjusted = simulate_forecast_with_regime(
        current_price, base_ci_width, report.volatility_multiplier
    )

    # Comparison table
    compare_table = Table(title="Forecast Comparison", show_header=True)
    compare_table.add_column("Approach", style="cyan")
    compare_table.add_column("Mean", justify="right")
    compare_table.add_column("CI95 Low", justify="right")
    compare_table.add_column("CI95 High", justify="right")
    compare_table.add_column("CI Width", justify="right")
    compare_table.add_column("Multiplier", justify="right")

    compare_table.add_row(
        "Standard (no regime)",
        f"{forecast_base['mean']:.2f}",
        f"{forecast_base['ci95_low']:.2f}",
        f"{forecast_base['ci95_high']:.2f}",
        f"{forecast_base['adjusted_width']:.1f}",
        f"{forecast_base['multiplier']:.2f}x",
    )

    compare_table.add_row(
        f"Regime-Aware ({report.regime.value})",
        f"{forecast_adjusted['mean']:.2f}",
        f"{forecast_adjusted['ci95_low']:.2f}",
        f"{forecast_adjusted['ci95_high']:.2f}",
        f"[bold]{forecast_adjusted['adjusted_width']:.1f}[/bold]",
        f"[bold]{forecast_adjusted['multiplier']:.2f}x[/bold]",
    )

    console.print(compare_table)
    console.print()

    # Impact summary
    width_increase = forecast_adjusted['adjusted_width'] - forecast_base['adjusted_width']
    width_increase_pct = (width_increase / forecast_base['adjusted_width']) * 100

    console.print(Panel(
        f"[bold]CI Width Impact:[/bold]\n\n"
        f"Base width: {base_ci_width:.1f} pesos\n"
        f"Adjusted width: {forecast_adjusted['adjusted_width']:.1f} pesos\n"
        f"Increase: +{width_increase:.1f} pesos ({width_increase_pct:+.1f}%)\n\n"
        f"[dim]This wider interval reflects increased market uncertainty\n"
        f"in the {report.regime.value.upper()} regime, improving forecast\n"
        f"reliability during volatile conditions.[/dim]",
        title="Forecast Adjustment Summary",
        border_style="blue",
    ))

    # Recommendation
    if report.volatility_multiplier > 1.2:
        console.print(
            "[yellow]⚠ Recommendation:[/yellow] Use conservative position sizing "
            "due to elevated market volatility.\n"
        )
    else:
        console.print("[green]✓ Normal market conditions - standard forecasting applicable.[/green]\n")


if __name__ == "__main__":
    main()
