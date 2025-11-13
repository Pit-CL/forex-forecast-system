#!/usr/bin/env python3
"""
Test simplificado de drift detection sin requerir APIs externas.
"""

import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forex_core.mlops.monitoring import DataDriftDetector, DriftSeverity


def main():
    print("=" * 70)
    print("DRIFT DETECTION - Simplified Test")
    print("=" * 70)
    print()

    # Generate synthetic USD/CLP data
    print("📊 Generating synthetic USD/CLP data...")
    np.random.seed(42)

    # Historical data (120 days, stable around 920 CLP)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=120, freq='D')
    historical = pd.Series(
        data=920 + np.random.normal(0, 5, 120),
        index=dates
    )

    print(f"   Generated {len(historical)} days of data")
    print(f"   Mean: {historical.mean():.2f} CLP")
    print(f"   Std: {historical.std():.2f} CLP")
    print()

    # Test 1: No drift (stable series)
    print("=" * 70)
    print("TEST 1: Stable Series (No Drift Expected)")
    print("=" * 70)

    detector = DataDriftDetector(baseline_window=90, test_window=30)
    report = detector.generate_drift_report(historical)

    print(f"   Drift detected: {report.drift_detected}")
    print(f"   Severity: {report.severity.value}")
    print(f"   P-value: {report.p_value:.4f}")
    failed_tests = sum(1 for test in report.tests.values() if test.drift_detected)
    print(f"   Tests failed: {failed_tests}/{len(report.tests)}")
    print()

    # Test 2: Mean shift (last 30 days increased +15 CLP)
    print("=" * 70)
    print("TEST 2: Mean Shift (+15 CLP in last 30 days)")
    print("=" * 70)

    series_with_shift = historical.copy()
    series_with_shift.iloc[-30:] += 15  # Shift last 30 days

    report_shift = detector.generate_drift_report(series_with_shift)

    print(f"   Drift detected: {report_shift.drift_detected}")
    print(f"   Severity: {report_shift.severity.value}")
    print(f"   P-value: {report_shift.p_value:.4f}")
    mean_change = report_shift.recent_mean - report_shift.baseline_mean
    print(f"   Mean change: {mean_change:.2f} CLP")
    failed_tests = sum(1 for test in report_shift.tests.values() if test.drift_detected)
    print(f"   Tests failed: {failed_tests}/{len(report_shift.tests)}")
    print()

    # Test 3: Volatility spike (last 30 days std x3)
    print("=" * 70)
    print("TEST 3: Volatility Spike (3x std in last 30 days)")
    print("=" * 70)

    series_volatile = historical.copy()
    series_volatile.iloc[-30:] += np.random.normal(0, 15, 30)  # 3x volatility

    report_vol = detector.generate_drift_report(series_volatile)

    print(f"   Drift detected: {report_vol.drift_detected}")
    print(f"   Severity: {report_vol.severity.value}")
    print(f"   P-value: {report_vol.p_value:.4f}")
    std_change = report_vol.recent_std - report_vol.baseline_std
    print(f"   Std change: {std_change:.2f} CLP")
    failed_tests = sum(1 for test in report_vol.tests.values() if test.drift_detected)
    print(f"   Tests failed: {failed_tests}/{len(report_vol.tests)}")
    print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    results = [
        ("Test 1 (Stable)", report.drift_detected, report.severity),
        ("Test 2 (Mean Shift)", report_shift.drift_detected, report_shift.severity),
        ("Test 3 (Volatility)", report_vol.drift_detected, report_vol.severity),
    ]

    for name, detected, severity in results:
        status = "❌ DRIFT" if detected else "✅ NO DRIFT"
        print(f"   {name:25} {status:15} Severity: {severity.value}")

    print()

    # Check if tests passed as expected
    expected = [
        (False, DriftSeverity.NONE),      # Stable should have no drift
        (True, DriftSeverity.HIGH),       # Mean shift should trigger
        (True, DriftSeverity.HIGH),       # Volatility should trigger
    ]

    all_passed = all(
        detected == exp[0] and severity == exp[1]
        for (_, detected, severity), exp in zip(results, expected)
    )

    if all_passed:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
