"""
Tests for drift detection system.

Tests the DataDriftDetector class and related functionality to ensure
proper detection of distribution changes in time series data.
"""

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta

from forex_core.mlops import DataDriftDetector, DriftReport, DriftSeverity


class TestDataDriftDetector:
    """Test suite for DataDriftDetector."""

    @pytest.fixture
    def detector(self):
        """Create a standard detector with default parameters."""
        return DataDriftDetector(
            baseline_window=90,
            test_window=30,
            alpha=0.05,
        )

    @pytest.fixture
    def stable_series(self):
        """
        Create a stable time series with no drift.

        Generates 120 days of data from normal distribution with
        constant mean and variance.
        """
        np.random.seed(42)
        dates = pd.date_range(end=datetime.now(), periods=120, freq='D')
        values = np.random.normal(loc=950, scale=10, size=120)
        return pd.Series(values, index=dates)

    @pytest.fixture
    def mean_shift_series(self):
        """
        Create a series with mean shift.

        First 90 days: mean=950, last 30 days: mean=970
        """
        np.random.seed(42)
        dates = pd.date_range(end=datetime.now(), periods=120, freq='D')

        # Baseline: mean=950
        baseline = np.random.normal(loc=950, scale=10, size=90)

        # Recent: mean=970 (shifted up)
        recent = np.random.normal(loc=970, scale=10, size=30)

        values = np.concatenate([baseline, recent])
        return pd.Series(values, index=dates)

    @pytest.fixture
    def variance_change_series(self):
        """
        Create a series with variance change.

        First 90 days: std=10, last 30 days: std=20
        """
        np.random.seed(42)
        dates = pd.date_range(end=datetime.now(), periods=120, freq='D')

        # Baseline: std=10
        baseline = np.random.normal(loc=950, scale=10, size=90)

        # Recent: std=20 (higher volatility)
        recent = np.random.normal(loc=950, scale=20, size=30)

        values = np.concatenate([baseline, recent])
        return pd.Series(values, index=dates)

    def test_no_drift_detected_stable_series(self, detector, stable_series):
        """Test that stable series shows no drift."""
        report = detector.generate_drift_report(stable_series)

        assert isinstance(report, DriftReport)
        assert report.drift_detected is False
        assert report.severity == DriftSeverity.NONE
        assert report.baseline_size == 90
        assert report.recent_size == 30

    def test_mean_shift_detected(self, detector, mean_shift_series):
        """Test that mean shift is detected."""
        report = detector.generate_drift_report(mean_shift_series)

        assert report.drift_detected is True
        assert report.severity in [DriftSeverity.LOW, DriftSeverity.MEDIUM, DriftSeverity.HIGH]

        # Check that t-test detected the shift
        t_test = report.tests.get("t_test")
        assert t_test is not None
        assert t_test.drift_detected is True

    def test_variance_change_detected(self, detector, variance_change_series):
        """Test that variance change is detected."""
        report = detector.generate_drift_report(variance_change_series)

        assert report.drift_detected is True

        # Check that Levene test detected the change
        levene_test = report.tests.get("levene_test")
        assert levene_test is not None
        assert levene_test.drift_detected is True

    def test_insufficient_data_handling(self, detector):
        """Test that insufficient data is handled gracefully."""
        # Only 50 points, need 120 (90 + 30)
        dates = pd.date_range(end=datetime.now(), periods=50, freq='D')
        values = np.random.normal(loc=950, scale=10, size=50)
        short_series = pd.Series(values, index=dates)

        report = detector.generate_drift_report(short_series)

        assert report.drift_detected is False
        assert report.baseline_size == 0
        assert report.recent_size == 0
        assert "Insufficient data" in report.recommendation

    def test_detect_drift_method(self, detector, mean_shift_series):
        """Test the detect_drift method directly."""
        result = detector.detect_drift(mean_shift_series)

        assert isinstance(result, dict)
        assert "drift_detected" in result
        assert "p_value" in result
        assert "statistic" in result
        assert "severity" in result

        assert isinstance(result["p_value"], float)
        assert 0 <= result["p_value"] <= 1
        assert result["statistic"] >= 0

    def test_volatility_regime_change(self, detector, variance_change_series):
        """Test volatility regime change detection."""
        regime_change = detector.detect_volatility_regime_change(variance_change_series)

        assert isinstance(regime_change, bool)
        # With 2x variance change, should detect regime change
        assert regime_change is True

    def test_mean_shift_detection_method(self, detector, mean_shift_series):
        """Test mean shift detection method."""
        result = detector.detect_mean_shift(mean_shift_series)

        assert result.test_name == "T-test (Mean Shift)"
        assert result.drift_detected is True
        assert 0 <= result.p_value <= 1
        assert result.description is not None

    def test_variance_change_method(self, detector, variance_change_series):
        """Test variance change detection method."""
        result = detector.detect_variance_change(variance_change_series)

        assert result.test_name == "Levene Test (Variance Change)"
        assert result.drift_detected is True
        assert 0 <= result.p_value <= 1

    def test_report_structure(self, detector, stable_series):
        """Test that report has all expected fields."""
        report = detector.generate_drift_report(stable_series)

        # Check all required fields
        assert hasattr(report, "drift_detected")
        assert hasattr(report, "severity")
        assert hasattr(report, "p_value")
        assert hasattr(report, "statistic")
        assert hasattr(report, "baseline_mean")
        assert hasattr(report, "recent_mean")
        assert hasattr(report, "baseline_std")
        assert hasattr(report, "recent_std")
        assert hasattr(report, "baseline_size")
        assert hasattr(report, "recent_size")
        assert hasattr(report, "tests")
        assert hasattr(report, "recommendation")
        assert hasattr(report, "timestamp")

        # Check tests dictionary
        assert len(report.tests) >= 4
        assert "ks_test" in report.tests
        assert "t_test" in report.tests
        assert "levene_test" in report.tests
        assert "ljungbox_test" in report.tests

    def test_custom_parameters(self):
        """Test detector with custom parameters."""
        custom_detector = DataDriftDetector(
            baseline_window=60,
            test_window=20,
            alpha=0.01,  # More stringent
        )

        dates = pd.date_range(end=datetime.now(), periods=80, freq='D')
        values = np.random.normal(loc=950, scale=10, size=80)
        series = pd.Series(values, index=dates)

        report = custom_detector.generate_drift_report(series)

        assert report.baseline_size == 60
        assert report.recent_size == 20

    def test_severity_levels(self, detector):
        """Test that severity is correctly calculated."""
        # Create series with progressively stronger drift
        dates = pd.date_range(end=datetime.now(), periods=120, freq='D')

        # Strong drift: mean shift + variance change
        np.random.seed(42)
        baseline = np.random.normal(loc=900, scale=8, size=90)
        recent = np.random.normal(loc=950, scale=20, size=30)  # Large change
        strong_drift = pd.Series(np.concatenate([baseline, recent]), index=dates)

        report = detector.generate_drift_report(strong_drift)

        # With such a large change, should be MEDIUM or HIGH
        assert report.severity in [DriftSeverity.MEDIUM, DriftSeverity.HIGH]
        assert report.drift_detected is True

    def test_recommendation_content(self, detector, mean_shift_series):
        """Test that recommendations contain useful information."""
        report = detector.generate_drift_report(mean_shift_series)

        assert report.recommendation is not None
        assert len(report.recommendation) > 0

        # Should mention action based on severity
        if report.severity == DriftSeverity.HIGH:
            assert "CRITICAL" in report.recommendation or "immediate" in report.recommendation.lower()
        elif report.severity == DriftSeverity.MEDIUM:
            assert "WARNING" in report.recommendation or "consider" in report.recommendation.lower()
        elif report.severity == DriftSeverity.LOW:
            assert "ADVISORY" in report.recommendation or "monitor" in report.recommendation.lower()


class TestDriftSeverity:
    """Test DriftSeverity enum."""

    def test_severity_values(self):
        """Test that all severity levels exist."""
        assert DriftSeverity.NONE.value == "none"
        assert DriftSeverity.LOW.value == "low"
        assert DriftSeverity.MEDIUM.value == "medium"
        assert DriftSeverity.HIGH.value == "high"

    def test_severity_comparison(self):
        """Test that severities can be compared."""
        severity_order = [
            DriftSeverity.NONE,
            DriftSeverity.LOW,
            DriftSeverity.MEDIUM,
            DriftSeverity.HIGH,
        ]

        # All values should be unique
        assert len(set(s.value for s in severity_order)) == len(severity_order)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_series(self):
        """Test handling of empty series."""
        detector = DataDriftDetector()
        empty_series = pd.Series([], dtype=float)

        report = detector.generate_drift_report(empty_series)

        assert report.drift_detected is False
        assert report.baseline_size == 0

    def test_series_with_nans(self):
        """Test handling of series with NaN values."""
        detector = DataDriftDetector()

        dates = pd.date_range(end=datetime.now(), periods=120, freq='D')
        values = np.random.normal(loc=950, scale=10, size=120)
        values[50:60] = np.nan  # Add some NaNs

        series = pd.Series(values, index=dates)

        # Should handle NaNs gracefully (scipy functions typically drop them)
        report = detector.generate_drift_report(series)

        # Should still generate a report
        assert isinstance(report, DriftReport)

    def test_constant_series(self):
        """Test handling of constant series (zero variance)."""
        detector = DataDriftDetector()

        dates = pd.date_range(end=datetime.now(), periods=120, freq='D')
        values = np.full(120, 950.0)  # All same value
        series = pd.Series(values, index=dates)

        # Should not crash
        report = detector.generate_drift_report(series)

        assert isinstance(report, DriftReport)
        # Constant series should have zero std
        assert report.baseline_std == 0.0

    def test_extreme_values(self):
        """Test handling of extreme outliers."""
        detector = DataDriftDetector()

        dates = pd.date_range(end=datetime.now(), periods=120, freq='D')
        values = np.random.normal(loc=950, scale=10, size=120)

        # Add extreme outliers
        values[50] = 10000  # Extreme high
        values[80] = 100    # Extreme low

        series = pd.Series(values, index=dates)

        # Should still work
        report = detector.generate_drift_report(series)

        assert isinstance(report, DriftReport)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
