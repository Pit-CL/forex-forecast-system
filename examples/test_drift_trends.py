"""
Test DriftTrendAnalyzer with historical data.

This script tests the drift trend analysis system by:
1. Loading historical USD/CLP data
2. Simulating drift detection over time
3. Recording drift reports
4. Analyzing drift trends
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timedelta

import pandas as pd
from loguru import logger

from forex_core.data.loader import DataLoader
from forex_core.mlops.drift_trends import DriftTrendAnalyzer
from forex_core.mlops.monitoring import DataDriftDetector


def test_drift_trends():
    """Test drift trend analysis with historical data."""
    logger.info("=" * 60)
    logger.info("Testing DriftTrendAnalyzer")
    logger.info("=" * 60)

    # Initialize components
    data_loader = DataLoader()
    drift_detector = DataDriftDetector(
        baseline_window=90, test_window=30, alpha=0.05
    )

    # Use test storage path
    test_storage_path = Path("data/drift_history/drift_history_test.parquet")
    trend_analyzer = DriftTrendAnalyzer(
        storage_path=test_storage_path,
        drift_detector=drift_detector,
    )

    # Load historical data
    logger.info("\n1. Loading historical USD/CLP data...")
    try:
        bundle = data_loader.load()
        series = bundle.usdclp_series
        logger.info(f"Loaded {len(series)} data points")
        logger.info(f"Date range: {series.index[0]} to {series.index[-1]}")
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return

    # Simulate drift detection over multiple time windows
    logger.info("\n2. Simulating drift detection over time...")

    # Use the last 180 days of data, check every 7 days
    lookback = 180
    step = 7

    if len(series) < lookback + 120:  # Need baseline + lookback
        logger.warning(f"Insufficient data for simulation: {len(series)} points")
        return

    # Start from 180 days ago
    start_idx = len(series) - lookback

    drift_count = 0
    for i in range(0, lookback, step):
        # Get data up to this point
        cutoff_idx = start_idx + i
        current_series = series.iloc[:cutoff_idx]

        # Generate drift report
        try:
            report = drift_detector.generate_drift_report(current_series)

            # Record drift (simulate different dates)
            simulated_date = series.index[cutoff_idx - 1]
            report.timestamp = simulated_date

            trend_analyzer.record_drift(report, horizon="7d")

            if report.drift_detected:
                drift_count += 1
                logger.info(
                    f"  {simulated_date.date()}: Drift detected "
                    f"(severity={report.severity.value})"
                )

        except Exception as e:
            logger.warning(f"Failed to generate report at idx {cutoff_idx}: {e}")

    logger.info(f"\nRecorded {lookback // step} drift checks, {drift_count} detected drift")

    # Analyze drift trend
    logger.info("\n3. Analyzing drift trend...")
    try:
        trend_report = trend_analyzer.analyze_trend("7d", lookback_days=90)

        logger.info(f"\n{'=' * 60}")
        logger.info("DRIFT TREND ANALYSIS REPORT")
        logger.info(f"{'=' * 60}")
        logger.info(f"Trend: {trend_report.trend.value.upper()}")
        logger.info(f"Current Score: {trend_report.current_score:.1f}/100")
        logger.info(f"30-day Average: {trend_report.avg_score_30d:.1f}/100")
        logger.info(f"90-day Average: {trend_report.avg_score_90d:.1f}/100")
        logger.info(f"Trend Slope: {trend_report.trend_slope:+.2f} points/day")
        logger.info(f"Trend R²: {trend_report.trend_r2:.3f}")
        logger.info(f"Consecutive HIGH: {trend_report.consecutive_high} days")

        if trend_report.last_stable_date:
            days_ago = (datetime.now() - trend_report.last_stable_date).days
            logger.info(f"Last Stable: {days_ago} days ago")
        else:
            logger.info("Last Stable: Never")

        logger.info(f"\n{trend_report.recommendation}")
        logger.info(f"{'=' * 60}")

        if trend_report.requires_action():
            logger.warning("⚠️  ACTION REQUIRED")
        else:
            logger.info("✅ No immediate action needed")

    except Exception as e:
        logger.error(f"Failed to analyze trend: {e}")
        import traceback
        traceback.print_exc()

    # Show drift history
    logger.info("\n4. Checking drift history...")
    try:
        history = trend_analyzer.get_drift_history(horizon="7d", days=30)

        if not history.empty:
            logger.info(f"\nLast 5 drift records:")
            logger.info("-" * 60)

            for _, row in history.tail(5).iterrows():
                timestamp = pd.to_datetime(row["timestamp"]).strftime("%Y-%m-%d")
                logger.info(
                    f"{timestamp}: score={row['drift_score']:.1f}, "
                    f"severity={row['severity']}, "
                    f"drift={row['drift_detected']}"
                )
        else:
            logger.warning("No drift history found")

    except Exception as e:
        logger.error(f"Failed to retrieve history: {e}")

    logger.info("\n✅ DriftTrendAnalyzer test complete!")
    logger.info(f"Test storage: {test_storage_path}")


if __name__ == "__main__":
    test_drift_trends()
