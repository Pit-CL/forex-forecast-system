"""
Demo script for drift detection system.

This script demonstrates how to use the DataDriftDetector to monitor
USD/CLP exchange rate data for distribution changes.

Usage:
    python examples/drift_detection_demo.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from forex_core.config import get_settings
from forex_core.data import DataLoader
from forex_core.mlops import DataDriftDetector, DriftSeverity


def demo_with_real_data():
    """
    Demonstrate drift detection with real USD/CLP data.
    """
    print("=" * 80)
    print("DRIFT DETECTION DEMO - Real USD/CLP Data")
    print("=" * 80)
    print()

    # Load configuration and data
    print("Loading configuration and data...")
    settings = get_settings()
    loader = DataLoader(settings)
    bundle = loader.load()

    print(f"Loaded {len(bundle.usdclp_series)} days of USD/CLP data")
    print(f"Date range: {bundle.usdclp_series.index[0]} to {bundle.usdclp_series.index[-1]}")
    print()

    # Create detector with default settings
    print("Initializing drift detector...")
    detector = DataDriftDetector(
        baseline_window=settings.drift_baseline_window,
        test_window=settings.drift_test_window,
        alpha=settings.drift_alpha,
    )
    print(f"  Baseline window: {settings.drift_baseline_window} days")
    print(f"  Test window: {settings.drift_test_window} days")
    print(f"  Significance level: {settings.drift_alpha}")
    print()

    # Run drift detection
    print("Running drift detection analysis...")
    print("-" * 80)
    report = detector.generate_drift_report(bundle.usdclp_series)

    # Display results
    print()
    print("DRIFT DETECTION RESULTS")
    print("=" * 80)
    print()

    print(f"Drift Detected: {'YES' if report.drift_detected else 'NO'}")
    print(f"Severity Level: {report.severity.value.upper()}")
    print(f"Overall P-value: {report.p_value:.6f}")
    print(f"KS Statistic: {report.statistic:.4f}")
    print()

    print("SUMMARY STATISTICS")
    print("-" * 80)
    print(f"Baseline Period (last {report.baseline_size} days):")
    print(f"  Mean:   {report.baseline_mean:.2f} CLP")
    print(f"  Std Dev: {report.baseline_std:.2f} CLP")
    print()
    print(f"Recent Period (last {report.recent_size} days):")
    print(f"  Mean:   {report.recent_mean:.2f} CLP")
    print(f"  Std Dev: {report.recent_std:.2f} CLP")
    print()

    # Calculate changes
    mean_change = report.recent_mean - report.baseline_mean
    mean_change_pct = (mean_change / report.baseline_mean) * 100
    std_change = report.recent_std - report.baseline_std
    std_change_pct = (std_change / report.baseline_std) * 100 if report.baseline_std > 0 else 0

    print(f"Change in Mean:   {mean_change:+.2f} CLP ({mean_change_pct:+.2f}%)")
    print(f"Change in Std Dev: {std_change:+.2f} CLP ({std_change_pct:+.2f}%)")
    print()

    print("STATISTICAL TESTS")
    print("-" * 80)
    for test_name, result in report.tests.items():
        status = "FAILED" if result.drift_detected else "PASSED"
        emoji = "❌" if result.drift_detected else "✅"
        print(f"{emoji} {result.test_name:<35} [{status}]")
        print(f"   Statistic: {result.statistic:.4f}, P-value: {result.p_value:.6f}")
        print(f"   {result.description}")
        print()

    print("RECOMMENDATION")
    print("-" * 80)
    print(report.recommendation)
    print()

    # Color-coded severity message
    if report.severity == DriftSeverity.HIGH:
        print("⚠️  ACTION REQUIRED: Immediate model retraining recommended")
    elif report.severity == DriftSeverity.MEDIUM:
        print("⚠️  WARNING: Monitor closely and consider retraining soon")
    elif report.severity == DriftSeverity.LOW:
        print("ℹ️  ADVISORY: Continue monitoring")
    else:
        print("✅ OK: No action required")
    print()

    print("=" * 80)
    print(f"Analysis completed at: {report.timestamp}")
    print("=" * 80)


def demo_with_synthetic_data():
    """
    Demonstrate drift detection with synthetic data showing various drift types.
    """
    print()
    print("=" * 80)
    print("DRIFT DETECTION DEMO - Synthetic Data Examples")
    print("=" * 80)
    print()

    detector = DataDriftDetector(baseline_window=90, test_window=30, alpha=0.05)

    # Example 1: No drift
    print("Example 1: Stable series (no drift)")
    print("-" * 80)
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=120, freq='D')
    stable = pd.Series(np.random.normal(950, 10, 120), index=dates)

    report = detector.generate_drift_report(stable)
    print(f"Drift detected: {report.drift_detected}")
    print(f"Severity: {report.severity.value}")
    print()

    # Example 2: Mean shift
    print("Example 2: Mean shift (+20 CLP)")
    print("-" * 80)
    baseline_data = np.random.normal(950, 10, 90)
    recent_data = np.random.normal(970, 10, 30)  # +20 mean shift
    mean_shift = pd.Series(np.concatenate([baseline_data, recent_data]), index=dates)

    report = detector.generate_drift_report(mean_shift)
    print(f"Drift detected: {report.drift_detected}")
    print(f"Severity: {report.severity.value}")
    print(f"Mean change: {report.recent_mean - report.baseline_mean:.2f} CLP")
    print()

    # Example 3: Volatility regime change
    print("Example 3: Volatility regime change (2x increase)")
    print("-" * 80)
    baseline_data = np.random.normal(950, 10, 90)
    recent_data = np.random.normal(950, 20, 30)  # 2x volatility
    vol_change = pd.Series(np.concatenate([baseline_data, recent_data]), index=dates)

    report = detector.generate_drift_report(vol_change)
    print(f"Drift detected: {report.drift_detected}")
    print(f"Severity: {report.severity.value}")
    print(f"Std dev change: {report.recent_std - report.baseline_std:.2f} CLP")
    print()

    # Example 4: Combined drift
    print("Example 4: Combined drift (mean shift + volatility change)")
    print("-" * 80)
    baseline_data = np.random.normal(940, 8, 90)
    recent_data = np.random.normal(960, 18, 30)  # Both changes
    combined = pd.Series(np.concatenate([baseline_data, recent_data]), index=dates)

    report = detector.generate_drift_report(combined)
    print(f"Drift detected: {report.drift_detected}")
    print(f"Severity: {report.severity.value}")
    print(f"Mean change: {report.recent_mean - report.baseline_mean:.2f} CLP")
    print(f"Std dev change: {report.recent_std - report.baseline_std:.2f} CLP")
    failed_tests = sum(1 for test in report.tests.values() if test.drift_detected)
    print(f"Tests failed: {failed_tests}/{len(report.tests)}")
    print()


def demo_custom_configuration():
    """
    Demonstrate custom drift detector configuration.
    """
    print()
    print("=" * 80)
    print("DRIFT DETECTION DEMO - Custom Configuration")
    print("=" * 80)
    print()

    # More sensitive detector (lower alpha)
    print("Configuration 1: High sensitivity (alpha=0.01)")
    print("-" * 80)
    sensitive_detector = DataDriftDetector(
        baseline_window=60,
        test_window=20,
        alpha=0.01,  # More stringent
    )
    print(f"  Baseline: 60 days, Test: 20 days, Alpha: 0.01")
    print("  Result: Will detect smaller changes")
    print()

    # Less sensitive detector (higher alpha)
    print("Configuration 2: Low sensitivity (alpha=0.10)")
    print("-" * 80)
    relaxed_detector = DataDriftDetector(
        baseline_window=90,
        test_window=30,
        alpha=0.10,  # Less stringent
    )
    print(f"  Baseline: 90 days, Test: 30 days, Alpha: 0.10")
    print("  Result: Only detects larger changes")
    print()

    # Longer windows
    print("Configuration 3: Long-term monitoring")
    print("-" * 80)
    longterm_detector = DataDriftDetector(
        baseline_window=180,
        test_window=60,
        alpha=0.05,
    )
    print(f"  Baseline: 180 days, Test: 60 days, Alpha: 0.05")
    print("  Result: Better for detecting gradual long-term drift")
    print()


if __name__ == "__main__":
    try:
        # Run all demos
        demo_with_real_data()
        demo_with_synthetic_data()
        demo_custom_configuration()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
