#!/usr/bin/env python3
"""
Test simplificado de prediction tracking.
"""

import numpy as np
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forex_core.mlops.tracking import PredictionTracker


def main():
    print("=" * 70)
    print("PREDICTION TRACKING - Simplified Test")
    print("=" * 70)
    print()

    # Create temporary storage path
    test_dir = Path(__file__).parent / "test_data"
    test_dir.mkdir(exist_ok=True)

    # Remove any existing parquet file
    storage_file = test_dir / "predictions.parquet"
    if storage_file.exists():
        storage_file.unlink()

    print(f"📁 Using test file: {storage_file}")
    print()

    # Initialize tracker (pass file path directly)
    tracker = PredictionTracker(storage_path=storage_file)

    # Test 1: Log predictions
    print("=" * 70)
    print("TEST 1: Logging Predictions")
    print("=" * 70)
    print()

    forecast_date = datetime.now()
    horizon = "7d"

    predictions = []
    for i in range(1, 8):
        target_date = forecast_date + timedelta(days=i)
        predicted_mean = 920.0 + i * 0.5 + np.random.normal(0, 2)
        ci95_low = predicted_mean - 10
        ci95_high = predicted_mean + 10

        tracker.log_prediction(
            forecast_date=forecast_date,
            horizon=horizon,
            target_date=target_date,
            predicted_mean=predicted_mean,
            ci95_low=ci95_low,
            ci95_high=ci95_high,
        )

        predictions.append({
            "target_date": target_date,
            "predicted_mean": predicted_mean,
        })

        print(f"   ✓ Logged prediction for {target_date.date()}: {predicted_mean:.2f} CLP")

    print()
    print(f"✅ Logged {len(predictions)} predictions")
    print()

    # Test 2: Read back predictions
    print("=" * 70)
    print("TEST 2: Reading Stored Predictions")
    print("=" * 70)
    print()

    # Read the parquet file
    df = pd.read_parquet(storage_file)

    print(f"📊 Read {len(df)} predictions from storage")
    print(f"   Columns: {', '.join(df.columns)}")
    print()
    print("   Sample (first 3 rows):")
    for idx in range(min(3, len(df))):
        row = df.iloc[idx]
        print(f"      {row['target_date'].date()}: {row['predicted_mean']:.2f} CLP "
              f"[{row['ci95_low']:.2f} - {row['ci95_high']:.2f}]")
    print()

    # Validation
    print("=" * 70)
    print("VALIDATION")
    print("=" * 70)

    checks = [
        (len(df) == 7, "Stored 7 predictions"),
        ('forecast_date' in df.columns, "Has forecast_date column"),
        ('horizon' in df.columns, "Has horizon column"),
        ('target_date' in df.columns, "Has target_date column"),
        ('predicted_mean' in df.columns, "Has predicted_mean column"),
        ('ci95_low' in df.columns, "Has ci95_low column"),
        ('ci95_high' in df.columns, "Has ci95_high column"),
        ('actual_value' in df.columns, "Has actual_value column"),
        (df['actual_value'].isna().all(), "Actual values are None (not yet available)"),
        (df['horizon'].eq('7d').all(), "All predictions have correct horizon"),
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
        result = 0
    else:
        print("❌ Some validation checks failed!")
        result = 1

    # Cleanup test data
    import shutil
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print(f"🧹 Cleaned up test directory")

    return result


if __name__ == "__main__":
    sys.exit(main())
