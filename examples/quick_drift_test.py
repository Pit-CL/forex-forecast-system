#!/usr/bin/env python
"""
Quick test script for drift detection system.

Usage:
    python examples/quick_drift_test.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forex_core.config import get_settings
from forex_core.data import DataLoader
from forex_core.mlops import DataDriftDetector


def main():
    """Run quick drift detection test on real USD/CLP data."""
    print("\n" + "="*70)
    print("DRIFT DETECTION - Quick Test")
    print("="*70 + "\n")

    # Load data
    print("Loading USD/CLP data...")
    settings = get_settings()
    loader = DataLoader(settings)
    bundle = loader.load()
    print(f"✅ Loaded {len(bundle.usdclp_series)} days of data\n")

    # Run drift detection
    print("Running drift detection...")
    detector = DataDriftDetector(
        baseline_window=90,
        test_window=30,
        alpha=0.05
    )
    report = detector.generate_drift_report(bundle.usdclp_series)

    # Display results
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)

    if report.drift_detected:
        print(f"\n⚠️  DRIFT DETECTED - Severity: {report.severity.value.upper()}")
    else:
        print(f"\n✅ NO DRIFT DETECTED")

    print(f"\nStatistics:")
    print(f"  Baseline (last 90d): {report.baseline_mean:.2f} ± {report.baseline_std:.2f} CLP")
    print(f"  Recent (last 30d):   {report.recent_mean:.2f} ± {report.recent_std:.2f} CLP")

    mean_change = report.recent_mean - report.baseline_mean
    print(f"  Change:              {mean_change:+.2f} CLP ({mean_change/report.baseline_mean*100:+.2f}%)")

    print(f"\nTests:")
    for test_name, result in report.tests.items():
        status = "❌ FAILED" if result.drift_detected else "✅ PASSED"
        print(f"  {test_name:20} {status:12} (p={result.p_value:.4f})")

    print(f"\nRecommendation:")
    print(f"  {report.recommendation}")

    print("\n" + "="*70 + "\n")

    return report


if __name__ == "__main__":
    try:
        report = main()
        sys.exit(0 if not report.drift_detected else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
