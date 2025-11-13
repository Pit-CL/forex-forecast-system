#!/usr/bin/env python3
"""
Test simplificado de Chronos forecasting.
"""

import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forex_core.forecasting.chronos_model import forecast_chronos
from forex_core.data.models import ForecastPackage


def main():
    print("=" * 70)
    print("CHRONOS FORECASTING - Simplified Test")
    print("=" * 70)
    print()

    # Generate synthetic USD/CLP data (120 days)
    print("📊 Generating synthetic USD/CLP data...")
    np.random.seed(42)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=120, freq='D')

    # Simulate realistic USD/CLP with trend + noise
    trend = np.linspace(910, 930, 120)
    noise = np.random.normal(0, 5, 120)
    values = trend + noise

    series = pd.Series(data=values, index=dates)

    print(f"   Generated {len(series)} days of data")
    print(f"   Mean: {series.mean():.2f} CLP")
    print(f"   Std: {series.std():.2f} CLP")
    print(f"   Trend: {values[0]:.2f} -> {values[-1]:.2f} CLP")
    print()

    # Test forecasting with Chronos
    print("=" * 70)
    print("TEST: 7-day Forecast with Chronos-Bolt-Small")
    print("=" * 70)
    print()

    try:
        print("🔮 Running Chronos forecast (this may take 30-60 seconds)...")

        package = forecast_chronos(
            series=series,
            steps=7,
            context_length=90,
            num_samples=50,  # Reduced for faster testing
            validate=False  # Skip validation for faster testing
        )

        print("✅ Forecast completed successfully!")
        print()

        # Display results
        print("📈 Forecast Summary:")
        print(f"   Steps: {len(package.series)}")
        print(f"   Start date: {package.series[0].date}")
        print(f"   End date: {package.series[-1].date}")
        print()

        print("   Predictions:")
        for i, point in enumerate(package.series, 1):
            print(f"   Day {i}: {point.mean:.2f} CLP  "
                  f"[CI95: {point.ci95_low:.2f} - {point.ci95_high:.2f}]")
        print()

        # Validate forecast structure
        print("=" * 70)
        print("VALIDATION")
        print("=" * 70)

        checks = [
            (len(package.series) == 7, "Forecast has 7 days"),
            (isinstance(package, ForecastPackage), "Returns ForecastPackage"),
            (all(p.ci95_low < p.mean < p.ci95_high for p in package.series),
             "Mean within CI95 bounds"),
            (all(p.ci80_low < p.mean < p.ci80_high for p in package.series),
             "Mean within CI80 bounds"),
            (package.series[0].mean > 0, "Positive forecast values"),
        ]

        all_passed = True
        for passed, description in checks:
            status = "✅" if passed else "❌"
            print(f"   {status} {description}")
            if not passed:
                all_passed = False

        print()

        if all_passed:
            print("✅ All validation checks passed!")
            return 0
        else:
            print("❌ Some validation checks failed!")
            return 1

    except Exception as e:
        print(f"❌ Error during forecast: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
