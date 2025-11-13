"""
Example script demonstrating the PredictionTracker system.

This script shows how to:
1. Initialize the tracker
2. Log sample predictions
3. Update actuals
4. Calculate out-of-sample performance metrics
5. View predictions summary

Usage:
    python examples/test_prediction_tracking.py
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forex_core.mlops import PredictionTracker


def demo_prediction_tracking():
    """Demonstrate the prediction tracking workflow."""
    print("=" * 80)
    print("PREDICTION TRACKING SYSTEM DEMO")
    print("=" * 80)
    print()

    # Initialize tracker
    print("1. Initializing PredictionTracker...")
    tracker = PredictionTracker()
    print(f"   Storage location: {tracker.storage_path}")
    print()

    # Log sample predictions
    print("2. Logging sample predictions...")
    today = datetime.now()

    # Simulate 7-day forecast
    for i in range(7):
        target_date = today + timedelta(days=i + 1)
        predicted_mean = 950.0 + i * 2  # Simulate trend
        ci_width = 10.0

        tracker.log_prediction(
            forecast_date=today,
            horizon="7d",
            target_date=target_date,
            predicted_mean=predicted_mean,
            ci95_low=predicted_mean - ci_width,
            ci95_high=predicted_mean + ci_width,
        )
        print(f"   Logged: {target_date.date()} -> {predicted_mean:.2f} CLP")

    print()

    # Simulate older predictions from 30 days ago
    print("3. Simulating historical predictions (30 days ago)...")
    past_date = today - timedelta(days=30)

    for i in range(7):
        target_date = past_date + timedelta(days=i + 1)
        predicted_mean = 945.0 + i * 1.5

        tracker.log_prediction(
            forecast_date=past_date,
            horizon="7d",
            target_date=target_date,
            predicted_mean=predicted_mean,
            ci95_low=predicted_mean - 8,
            ci95_high=predicted_mean + 8,
        )
        print(f"   Logged historical: {target_date.date()} -> {predicted_mean:.2f} CLP")

    print()

    # Update actuals
    print("4. Updating actual values...")
    updated = tracker.update_actuals(lookback_days=60)
    print(f"   Updated {updated} predictions with actual values")
    print()

    # Get performance metrics
    print("5. Calculating out-of-sample performance...")
    perf = tracker.get_recent_performance(horizon="7d", days=60)

    print(f"\n   === Performance Metrics (7d horizon, last 60 days) ===")
    print(f"   Sample size: {perf['n_predictions']}/{perf['n_total']} predictions")

    if perf["n_predictions"] > 0:
        if perf["rmse"] is not None:
            print(f"   RMSE: {perf['rmse']:.2f} CLP")
        if perf["mae"] is not None:
            print(f"   MAE: {perf['mae']:.2f} CLP")
        if perf["mape"] is not None:
            print(f"   MAPE: {perf['mape']:.2%}")
        if perf["ci95_coverage"] is not None:
            print(f"   CI95 Coverage: {perf['ci95_coverage']:.1%}")
        if perf["directional_accuracy"] is not None:
            print(f"   Directional Accuracy: {perf['directional_accuracy']:.1%}")
    else:
        print("   No actuals available yet for performance calculation")

    print()

    # Get predictions summary
    print("6. Retrieving predictions summary...")
    summary = tracker.get_predictions_summary(days=90)

    if not summary.empty:
        print(f"   Total predictions in last 90 days: {len(summary)}")
        print(f"\n   Breakdown by horizon:")
        print(summary.groupby("horizon").size())
        print(f"\n   Predictions with actuals:")
        print(summary.groupby("horizon")["actual_value"].count())
    else:
        print("   No predictions found in last 90 days")

    print()
    print("=" * 80)
    print("DEMO COMPLETED")
    print("=" * 80)


def show_usage_example():
    """Show code example for integration."""
    print("\n" + "=" * 80)
    print("INTEGRATION EXAMPLE")
    print("=" * 80)
    print("""
# In your forecasting pipeline:

from datetime import datetime
from forex_core.mlops import PredictionTracker

# Initialize tracker
tracker = PredictionTracker()

# Before forecasting: update actuals for existing predictions
updated = tracker.update_actuals(lookback_days=180)
logger.info(f"Updated {updated} predictions with actual values")

# After generating forecast: log new predictions
for point in forecast.series:
    tracker.log_prediction(
        forecast_date=datetime.now(),
        horizon="7d",  # or "15d", "30d", "90d"
        target_date=point.date,
        predicted_mean=point.mean,
        ci95_low=point.ci95_low,
        ci95_high=point.ci95_high,
    )

# Get recent performance
perf = tracker.get_recent_performance(horizon="7d", days=60)
logger.info(f"Recent RMSE: {perf['rmse']:.2f} CLP")
logger.info(f"CI95 Coverage: {perf['ci95_coverage']:.1%}")
    """)
    print("=" * 80)


if __name__ == "__main__":
    try:
        demo_prediction_tracking()
        show_usage_example()
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()
