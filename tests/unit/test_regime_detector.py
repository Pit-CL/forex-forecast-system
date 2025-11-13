"""
Unit tests for market regime detector.

Tests MarketRegimeDetector for regime classification and volatility multipliers.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from forex_core.mlops.regime_detector import (
    MarketRegime,
    MarketRegimeDetector,
    RegimeReport,
    RegimeSignals,
)


@pytest.fixture
def detector():
    """Create regime detector with default settings."""
    return MarketRegimeDetector(
        lookback_days=90,
        vol_threshold_high=2.0,
        copper_threshold=5.0,
        bcch_meeting_days=3,
    )


@pytest.fixture
def normal_series():
    """Generate normal market data (low volatility)."""
    dates = pd.date_range(end=datetime.now(), periods=120, freq="D")
    values = 800 + np.random.normal(0, 2, 120)  # 0.25% daily volatility
    return pd.Series(values, index=dates, name="USD/CLP")


@pytest.fixture
def high_vol_series():
    """Generate high volatility market data."""
    dates = pd.date_range(end=datetime.now(), periods=120, freq="D")
    # First 90 days normal, last 30 high vol
    normal = 800 + np.random.normal(0, 2, 90)
    high_vol = normal[-1] + np.cumsum(np.random.normal(0, 10, 30))
    values = np.concatenate([normal, high_vol])
    return pd.Series(values, index=dates, name="USD/CLP")


@pytest.fixture
def copper_series():
    """Generate copper price series."""
    dates = pd.date_range(end=datetime.now(), periods=120, freq="D")
    values = 4.0 + np.random.normal(0, 0.1, 120)
    return pd.Series(values, index=dates, name="Copper")


class TestRegimeDetectorInit:
    """Test regime detector initialization."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        detector = MarketRegimeDetector()

        assert detector.lookback_days == 90
        assert detector.vol_threshold_high == 2.0
        assert detector.copper_threshold == 5.0
        assert detector.bcch_meeting_days == 3

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        detector = MarketRegimeDetector(
            lookback_days=60,
            vol_threshold_high=1.5,
            copper_threshold=3.0,
            bcch_meeting_days=2,
        )

        assert detector.lookback_days == 60
        assert detector.vol_threshold_high == 1.5
        assert detector.copper_threshold == 3.0
        assert detector.bcch_meeting_days == 2


class TestRegimeDetection:
    """Test regime detection logic."""

    def test_detect_normal_regime(self, detector, normal_series, copper_series):
        """Test detection of normal market regime."""
        report = detector.detect(normal_series, copper_series)

        assert isinstance(report, RegimeReport)
        assert report.regime == MarketRegime.NORMAL
        assert 0.0 <= report.confidence <= 100.0
        assert report.volatility_multiplier == 1.0

    def test_detect_high_vol_regime(self, detector, high_vol_series, copper_series):
        """Test detection of high volatility regime."""
        report = detector.detect(high_vol_series, copper_series)

        # Should detect high volatility in recent period
        assert isinstance(report, RegimeReport)
        assert report.signals.vol_z_score > 0  # Some volatility signal

    def test_detect_without_copper(self, detector, normal_series):
        """Test detection works without copper data."""
        report = detector.detect(normal_series, copper_series=None)

        assert isinstance(report, RegimeReport)
        assert report.regime in [MarketRegime.NORMAL, MarketRegime.HIGH_VOL, MarketRegime.UNKNOWN]

    def test_detect_insufficient_data(self, detector):
        """Test detection with insufficient data."""
        # Only 30 days of data (need 90)
        dates = pd.date_range(end=datetime.now(), periods=30, freq="D")
        short_series = pd.Series(800 + np.random.normal(0, 2, 30), index=dates)

        report = detector.detect(short_series)

        # Should handle gracefully - returns UNKNOWN or NORMAL with low confidence
        assert isinstance(report, RegimeReport)


class TestVolatilitySignals:
    """Test volatility signal calculation."""

    def test_vol_z_score_calculation(self, detector, normal_series):
        """Test volatility z-score calculation."""
        report = detector.detect(normal_series)

        # Z-score should be defined
        assert isinstance(report.signals.vol_z_score, float)
        # For normal data, should be around 0 (±2σ)
        assert -3.0 <= report.signals.vol_z_score <= 3.0

    def test_vol_percentile_calculation(self, detector, normal_series):
        """Test volatility percentile calculation."""
        report = detector.detect(normal_series)

        # Percentile should be in [0, 100]
        assert 0.0 <= report.signals.vol_percentile <= 100.0

    def test_high_vol_detection(self, detector):
        """Test detection of high volatility periods."""
        # Create series with spike in recent period
        dates = pd.date_range(end=datetime.now(), periods=120, freq="D")
        normal = 800 + np.random.normal(0, 2, 110)
        spike = normal[-1] + np.cumsum(np.random.normal(0, 15, 10))  # High vol
        values = np.concatenate([normal, spike])
        series = pd.Series(values, index=dates)

        report = detector.detect(series)

        # Should have high vol_z_score
        assert report.signals.vol_z_score > 1.0


class TestCopperSignals:
    """Test copper-related signal calculation."""

    def test_copper_change_calculation(self, detector, normal_series):
        """Test copper 5-day change calculation."""
        # Create copper series with known change
        dates = pd.date_range(end=datetime.now(), periods=120, freq="D")
        copper = np.full(120, 4.0)
        copper[-5:] = 4.3  # +7.5% in last 5 days
        copper_series = pd.Series(copper, index=dates)

        report = detector.detect(normal_series, copper_series)

        # Should detect copper change
        assert report.signals.copper_change is not None
        assert abs(report.signals.copper_change) > 0.05  # >5% change

    def test_correlation_break_detection(self, detector):
        """Test USD/CLP-Copper correlation break detection."""
        dates = pd.date_range(end=datetime.now(), periods=120, freq="D")

        # Create inversely correlated series
        usdclp = 800 + np.cumsum(np.random.normal(0, 2, 120))
        copper = 4.0 - (usdclp - 800) * 0.003  # Inverse correlation

        # Break correlation in last 30 days
        copper[-30:] = 4.0 + np.cumsum(np.random.normal(0, 0.1, 30))  # Independent

        usdclp_series = pd.Series(usdclp, index=dates)
        copper_series = pd.Series(copper, index=dates)

        report = detector.detect(usdclp_series, copper_series)

        # May or may not detect break depending on magnitude
        assert isinstance(report.signals.correlation_break, bool)


class TestVolatilityMultiplier:
    """Test volatility multiplier calculation."""

    def test_normal_regime_multiplier(self, detector):
        """Test multiplier for normal regime."""
        signals = RegimeSignals(
            vol_z_score=0.5,
            vol_percentile=30.0,
            copper_change=0.01,
            usdclp_change=0.01,
            correlation_break=False,
            bcch_meeting_proximity=10,
        )

        multiplier = detector._calculate_volatility_multiplier(
            MarketRegime.NORMAL, signals
        )

        assert multiplier == 1.0

    def test_high_vol_multiplier_scaling(self, detector):
        """Test multiplier scales with volatility z-score."""
        # Low high-vol
        signals_low = RegimeSignals(
            vol_z_score=2.1,
            vol_percentile=80.0,
            copper_change=0.01,
            usdclp_change=0.01,
            correlation_break=False,
            bcch_meeting_proximity=10,
        )

        # High high-vol
        signals_high = RegimeSignals(
            vol_z_score=3.5,
            vol_percentile=95.0,
            copper_change=0.01,
            usdclp_change=0.01,
            correlation_break=False,
            bcch_meeting_proximity=10,
        )

        mult_low = detector._calculate_volatility_multiplier(
            MarketRegime.HIGH_VOL, signals_low
        )
        mult_high = detector._calculate_volatility_multiplier(
            MarketRegime.HIGH_VOL, signals_high
        )

        # Higher vol should have higher multiplier
        assert mult_high > mult_low
        # Both should be in valid range
        assert 1.2 <= mult_low <= 1.9
        assert 1.2 <= mult_high <= 1.9

    def test_copper_shock_multiplier(self, detector):
        """Test fixed multiplier for copper shock."""
        signals = RegimeSignals(
            vol_z_score=1.5,
            vol_percentile=70.0,
            copper_change=0.08,
            usdclp_change=0.03,
            correlation_break=True,
            bcch_meeting_proximity=10,
        )

        multiplier = detector._calculate_volatility_multiplier(
            MarketRegime.COPPER_SHOCK, signals
        )

        assert multiplier == 1.5

    def test_bcch_intervention_multiplier(self, detector):
        """Test maximum multiplier for BCCh intervention."""
        signals = RegimeSignals(
            vol_z_score=3.0,
            vol_percentile=90.0,
            copper_change=0.02,
            usdclp_change=0.05,
            correlation_break=False,
            bcch_meeting_proximity=1,
        )

        multiplier = detector._calculate_volatility_multiplier(
            MarketRegime.BCCH_INTERVENTION, signals
        )

        assert multiplier == 2.0


class TestBCChMeetingDetection:
    """Test BCCh meeting proximity detection."""

    def test_bcch_meeting_proximity(self, detector):
        """Test BCCh meeting proximity calculation."""
        # Just verify it returns an integer
        proximity = detector._get_bcch_meeting_proximity()

        assert isinstance(proximity, int)
        # Should be reasonable (within ~30 days)
        assert abs(proximity) <= 30

    def test_bcch_meeting_in_regime(self, detector):
        """Test BCCh meeting affects regime classification."""
        # Create high vol near meeting
        dates = pd.date_range(end=datetime.now(), periods=120, freq="D")
        values = 800 + np.cumsum(np.random.normal(0, 8, 120))  # High vol
        series = pd.Series(values, index=dates)

        report = detector.detect(series)

        # Proximity should be set
        assert isinstance(report.signals.bcch_meeting_proximity, int)


class TestRegimeReport:
    """Test RegimeReport functionality."""

    def test_report_structure(self, detector, normal_series):
        """Test report contains all required fields."""
        report = detector.detect(normal_series)

        assert hasattr(report, "regime")
        assert hasattr(report, "confidence")
        assert hasattr(report, "signals")
        assert hasattr(report, "timestamp")
        assert hasattr(report, "recommendation")
        assert hasattr(report, "volatility_multiplier")

    def test_requires_wider_ci(self):
        """Test requires_wider_ci() method."""
        # Normal regime - no wider CI
        report_normal = RegimeReport(
            regime=MarketRegime.NORMAL,
            confidence=100.0,
            signals=RegimeSignals(0.5, 30, 0.01, 0.01, False, 10),
            timestamp=datetime.now(),
            recommendation="Normal conditions",
            volatility_multiplier=1.0,
        )

        # High vol regime - wider CI
        report_high_vol = RegimeReport(
            regime=MarketRegime.HIGH_VOL,
            confidence=80.0,
            signals=RegimeSignals(2.5, 85, 0.01, 0.01, False, 10),
            timestamp=datetime.now(),
            recommendation="High volatility",
            volatility_multiplier=1.6,
        )

        assert report_normal.requires_wider_ci() is False
        assert report_high_vol.requires_wider_ci() is True

    def test_to_dict_serialization(self, detector, normal_series):
        """Test report can be serialized to dict."""
        report = detector.detect(normal_series)

        report_dict = report.to_dict()

        assert isinstance(report_dict, dict)
        assert "regime" in report_dict
        assert "confidence" in report_dict
        assert "volatility_multiplier" in report_dict
        assert report_dict["regime"] == report.regime.value


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_series(self, detector):
        """Test with empty series."""
        empty_series = pd.Series([], dtype=float)

        # Should handle gracefully
        report = detector.detect(empty_series)
        assert isinstance(report, RegimeReport)

    def test_nan_values(self, detector):
        """Test with NaN values in series."""
        dates = pd.date_range(end=datetime.now(), periods=120, freq="D")
        values = 800 + np.random.normal(0, 2, 120)
        values[50:60] = np.nan  # Inject NaNs

        series = pd.Series(values, index=dates)

        # Should handle gracefully (may drop NaNs or return UNKNOWN)
        report = detector.detect(series)
        assert isinstance(report, RegimeReport)

    def test_constant_series(self, detector):
        """Test with constant price series."""
        dates = pd.date_range(end=datetime.now(), periods=120, freq="D")
        constant_series = pd.Series(np.full(120, 800.0), index=dates)

        report = detector.detect(constant_series)

        # Zero volatility - should be NORMAL with z-score around 0
        assert report.regime in [MarketRegime.NORMAL, MarketRegime.UNKNOWN]
        assert report.volatility_multiplier == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
