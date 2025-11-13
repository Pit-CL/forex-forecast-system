"""
Test script demonstrating dynamic chart interpretation functions.

This script shows how the new dynamic interpretation functions generate
contextual text based on real data inputs, replacing static hardcoded values.

Run from project root:
    python examples/test_dynamic_interpretations.py
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forex_core.reporting.chart_interpretations import (
    interpret_hist_overview,
    interpret_tactical_zoom,
    interpret_forecast_bands,
    interpret_correlation_matrix,
    extract_correlation_metrics,
)
from forex_core.data.models import ForecastPoint, ForecastResult, Indicator
from forex_core.data.loader import DataBundle
from forex_core.data.registry import SourceRegistry


def create_mock_bundle() -> DataBundle:
    """Create mock DataBundle with realistic USD/CLP data."""
    # Generate mock USD/CLP historical series (30 days)
    dates = pd.date_range(end=datetime.now(), periods=30, freq="D")

    # Simulate realistic USD/CLP values with trend and noise
    base_value = 938.0
    trend = np.linspace(0, 5, 30)  # Slight upward trend
    noise = np.random.normal(0, 2, 30)
    usdclp_values = base_value + trend + noise

    usdclp_series = pd.Series(usdclp_values, index=dates)

    # Generate correlated copper prices (inverse correlation ~-0.65)
    copper_base = 4.30
    copper_values = copper_base - 0.05 * (trend + noise * 0.5) + np.random.normal(0, 0.05, 30)
    copper_series = pd.Series(copper_values, index=dates)

    # Generate DXY (positive correlation ~0.75)
    dxy_base = 99.5
    dxy_values = dxy_base + 0.1 * (trend + noise * 0.3) + np.random.normal(0, 0.3, 30)
    dxy_series = pd.Series(dxy_values, index=dates)

    # Generate VIX (positive correlation ~0.3)
    vix_base = 16.0
    vix_values = vix_base + 0.05 * trend + np.random.normal(0, 1.5, 30)
    vix_series = pd.Series(vix_values, index=dates)

    # Generate EEM (negative correlation ~-0.45)
    eem_base = 42.0
    eem_values = eem_base - 0.03 * trend + np.random.normal(0, 0.5, 30)
    eem_series = pd.Series(eem_values, index=dates)

    # Create TPM and inflation series
    tpm_series = pd.Series([5.75] * 30, index=dates)
    inflation_series = pd.Series(np.random.uniform(0.2, 0.5, 30), index=dates)

    # Create indicators
    indicators = {
        "usdclp_spot": Indicator(
            name="USD/CLP spot",
            value=usdclp_values[-1],
            unit="CLP",
            timestamp=datetime.now(),
            source_id=1,
        ),
        "copper": Indicator(
            name="Copper",
            value=copper_values[-1],
            unit="USD/lb",
            timestamp=datetime.now(),
            source_id=2,
        ),
        "dxy": Indicator(
            name="DXY",
            value=dxy_values[-1],
            unit="pts",
            timestamp=datetime.now(),
            source_id=3,
        ),
        "tpm": Indicator(
            name="TPM",
            value=5.75,
            unit="%",
            timestamp=datetime.now(),
            source_id=4,
        ),
    }

    # Create source registry
    sources = SourceRegistry()
    sources.register(
        name="Mindicador",
        url="https://mindicador.cl",
        description="Banco Central de Chile",
    )
    sources.register(
        name="Yahoo Finance",
        url="https://finance.yahoo.com",
        description="Market data provider",
    )

    # Create DataBundle
    bundle = DataBundle(
        usdclp_series=usdclp_series,
        copper_series=copper_series,
        tpm_series=tpm_series,
        inflation_series=inflation_series,
        indicators=indicators,
        sources=sources,
    )

    # Add optional series as attributes
    bundle.dxy_series = dxy_series
    bundle.vix_series = vix_series
    bundle.eem_series = eem_series

    return bundle


def create_mock_forecast(current_price: float, horizon_days: int = 7) -> ForecastResult:
    """Create mock ForecastResult with realistic projections."""
    forecast_dates = pd.date_range(
        start=datetime.now() + timedelta(days=1),
        periods=horizon_days,
        freq="D",
    )

    # Simulate forecast with slight upward bias and expanding uncertainty
    base_forecast = current_price
    trend = 0.05 * np.arange(horizon_days)  # +0.05 per day
    noise = np.random.normal(0, 0.3, horizon_days)

    forecast_points = []
    for i, date in enumerate(forecast_dates):
        mean_val = base_forecast + trend[i] + noise[i]

        # Expanding confidence intervals
        std_dev = 2.0 + 0.3 * i  # Increasing uncertainty

        point = ForecastPoint(
            date=date,
            mean=mean_val,
            ci80_low=mean_val - 1.28 * std_dev,
            ci80_high=mean_val + 1.28 * std_dev,
            ci95_low=mean_val - 1.96 * std_dev,
            ci95_high=mean_val + 1.96 * std_dev,
            std_dev=std_dev,
        )
        forecast_points.append(point)

    forecast = ForecastResult(
        series=forecast_points,
        methodology="Ensemble ARIMA-GARCH + VAR + Random Forest",
        error_metrics={"rmse": 2.5, "mae": 1.8, "mape": 0.19},
        residual_vol=2.1,
    )

    return forecast


def main():
    """Run demonstration of dynamic interpretation functions."""
    print("=" * 80)
    print("DYNAMIC CHART INTERPRETATION FUNCTIONS - DEMONSTRATION")
    print("=" * 80)
    print()

    # Create mock data
    print("Creating mock data bundle and forecast...")
    bundle = create_mock_bundle()
    current_price = bundle.usdclp_series.iloc[-1]
    forecast = create_mock_forecast(current_price, horizon_days=7)

    print(f"Current USD/CLP: {current_price:.2f}")
    print(f"Forecast endpoint: {forecast.series[-1].mean:.2f}")
    print(f"30-day range: {bundle.usdclp_series.min():.2f} - {bundle.usdclp_series.max():.2f}")
    print()

    # Test 1: Historical Overview
    print("=" * 80)
    print("CHART 1A - HISTORICAL OVERVIEW (30d + forecast, no bands)")
    print("=" * 80)
    interpretation_1a = interpret_hist_overview(bundle, forecast, "7d")
    print(interpretation_1a)
    print()

    # Test 2: Tactical Zoom
    print("=" * 80)
    print("CHART 1B - TACTICAL ZOOM (Last 5d + forecast WITH IC bands)")
    print("=" * 80)
    interpretation_1b = interpret_tactical_zoom(bundle, forecast, "7d")
    print(interpretation_1b)
    print()

    # Test 3: Forecast Bands
    print("=" * 80)
    print("CHART 2 - FORECAST BANDS (IC 80% / IC 95%)")
    print("=" * 80)
    interpretation_2 = interpret_forecast_bands(forecast, bundle, "7d")
    print(interpretation_2)
    print()

    # Test 4: Correlation Matrix
    print("=" * 80)
    print("CHART 4 - CORRELATION MATRIX")
    print("=" * 80)
    interpretation_4 = interpret_correlation_matrix(bundle, "7d")
    print(interpretation_4)
    print()

    # Test 5: Extract correlation metrics
    print("=" * 80)
    print("CORRELATION METRICS EXTRACTION")
    print("=" * 80)
    corr_metrics = extract_correlation_metrics(bundle)
    for pair, corr_value in corr_metrics.items():
        print(f"{pair:20s}: {corr_value:+.3f}")
    print()

    print("=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print()
    print("Key Features Demonstrated:")
    print("- All interpretations use REAL data values (no hardcoded numbers)")
    print("- Dynamic calculation of trading levels based on forecast IC bands")
    print("- Professional trader-to-trader language with specific actionable levels")
    print("- Risk/reward ratios calculated from actual confidence intervals")
    print("- Position sizing guidance adapts to volatility regime")
    print("- Correlation-based hedge strategies with real correlation coefficients")
    print()


if __name__ == "__main__":
    main()
