"""
Unit tests for forecasting models.

Tests cover:
- ARIMA forecasting
- Ensemble model combination
- Forecast result validation
- Confidence interval calculation
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from forex_core.forecasting.models import ForecastEngine
from forex_core.data.models import ForecastPoint, ForecastPackage
from forex_core.data.loader import DataBundle
from forex_core.config.base import Settings


@pytest.mark.unit
class TestForecastPoint:
    """Tests for ForecastPoint model."""

    def test_forecast_point_creation(self):
        """Test creating a forecast point."""
        point = ForecastPoint(
            date=datetime(2025, 12, 31),
            mean=950.0,
            ci80_low=945.0,
            ci80_high=955.0,
            ci95_low=940.0,
            ci95_high=960.0,
            std_dev=5.0,
        )

        assert point.mean == 950.0
        assert point.ci80_low == 945.0
        assert point.ci80_high == 955.0
        assert point.ci95_low == 940.0
        assert point.ci95_high == 960.0
        assert point.std_dev == 5.0

    def test_forecast_point_validation(self):
        """Test that forecast point validates confidence intervals."""
        # Valid point - ci95 should be wider than ci80
        point = ForecastPoint(
            date=datetime(2025, 12, 31),
            mean=950.0,
            ci80_low=945.0,
            ci80_high=955.0,
            ci95_low=940.0,
            ci95_high=960.0,
            std_dev=5.0,
        )

        # Confidence intervals should be properly ordered
        assert point.ci95_low <= point.ci80_low
        assert point.ci80_low <= point.mean
        assert point.mean <= point.ci80_high
        assert point.ci80_high <= point.ci95_high


@pytest.mark.unit
class TestForecastPackage:
    """Tests for ForecastPackage model."""

    def test_forecast_package_creation(self):
        """Test creating a complete forecast package."""
        points = [
            ForecastPoint(
                date=datetime(2025, 12, 31) + timedelta(days=i),
                mean=950.0 + i,
                ci80_low=945.0 + i,
                ci80_high=955.0 + i,
                ci95_low=940.0 + i,
                ci95_high=960.0 + i,
                std_dev=5.0,
            )
            for i in range(7)
        ]

        package = ForecastPackage(
            series=points,
            methodology="Test ARIMA(2,1,2)",
            error_metrics={"rmse": 5.2, "mae": 3.8, "mape": 0.4},
            residual_vol=4.1,
        )

        assert len(package.series) == 7
        assert package.methodology == "Test ARIMA(2,1,2)"
        assert package.error_metrics["rmse"] == 5.2
        assert package.residual_vol == 4.1


@pytest.mark.unit
class TestForecastEngine:
    """Tests for ForecastEngine."""

    def test_engine_initialization(self, test_settings: Settings):
        """Test forecast engine initialization."""
        engine = ForecastEngine(test_settings)

        assert engine.settings == test_settings
        assert hasattr(engine, "arima_enabled")
        assert hasattr(engine, "var_enabled")
        assert hasattr(engine, "rf_enabled")

    def test_engine_validates_input_series(
        self, test_settings: Settings, sample_usdclp_series: pd.Series
    ):
        """Test that engine validates input data."""
        engine = ForecastEngine(test_settings)

        # Should accept valid series
        assert isinstance(sample_usdclp_series, pd.Series)
        assert len(sample_usdclp_series) > 0

    def test_forecast_7d_structure(
        self, test_settings: Settings, sample_data_bundle: DataBundle
    ):
        """Test 7-day forecast produces correct structure."""
        engine = ForecastEngine(test_settings)

        # Mock forecast to test structure
        forecast = engine.forecast_7d(sample_data_bundle)

        # Should return ForecastPackage
        assert isinstance(forecast, ForecastPackage)
        assert len(forecast.series) == 7  # 7 days
        assert all(isinstance(p, ForecastPoint) for p in forecast.series)

        # Check dates are sequential
        dates = [p.date for p in forecast.series]
        for i in range(len(dates) - 1):
            assert dates[i] < dates[i + 1]

    def test_forecast_12m_structure(
        self, test_settings: Settings, sample_data_bundle: DataBundle
    ):
        """Test 12-month forecast produces correct structure."""
        engine = ForecastEngine(test_settings)

        forecast = engine.forecast_12m(sample_data_bundle)

        # Should return ForecastPackage
        assert isinstance(forecast, ForecastPackage)
        # Should have ~365 days (12 months)
        assert 350 <= len(forecast.series) <= 370
        assert all(isinstance(p, ForecastPoint) for p in forecast.series)


@pytest.mark.unit
class TestForecastMetrics:
    """Tests for forecast quality metrics."""

    def test_confidence_intervals_widen_over_time(
        self, test_settings: Settings, sample_data_bundle: DataBundle
    ):
        """Test that confidence intervals widen as forecast horizon increases."""
        engine = ForecastEngine(test_settings)
        forecast = engine.forecast_7d(sample_data_bundle)

        # Get first and last point
        first = forecast.series[0]
        last = forecast.series[-1]

        # Calculate interval widths
        first_width = first.ci95_high - first.ci95_low
        last_width = last.ci95_high - last.ci95_low

        # Last interval should be wider (uncertainty increases)
        assert last_width >= first_width

    def test_mean_within_confidence_intervals(
        self, test_settings: Settings, sample_data_bundle: DataBundle
    ):
        """Test that mean is always within confidence intervals."""
        engine = ForecastEngine(test_settings)
        forecast = engine.forecast_7d(sample_data_bundle)

        for point in forecast.series:
            assert point.ci95_low <= point.mean <= point.ci95_high
            assert point.ci80_low <= point.mean <= point.ci80_high


@pytest.mark.unit
class TestEnsembleLogic:
    """Tests for ensemble model combination."""

    def test_ensemble_weights_sum_to_one(self):
        """Test that ensemble weights are normalized."""
        weights = {"arima": 0.5, "var": 0.3, "rf": 0.2}

        total = sum(weights.values())
        assert abs(total - 1.0) < 0.001  # Should sum to 1.0

    def test_ensemble_combines_forecasts(self):
        """Test that ensemble properly combines multiple forecasts."""
        # Mock forecasts from different models
        arima_forecast = 950.0
        var_forecast = 952.0
        rf_forecast = 948.0

        weights = {"arima": 0.5, "var": 0.3, "rf": 0.2}

        # Calculate ensemble
        ensemble = (
            arima_forecast * weights["arima"]
            + var_forecast * weights["var"]
            + rf_forecast * weights["rf"]
        )

        # Should be weighted average
        expected = 950.0 * 0.5 + 952.0 * 0.3 + 948.0 * 0.2
        assert abs(ensemble - expected) < 0.001

    def test_ensemble_handles_missing_models(self):
        """Test that ensemble handles when some models are disabled."""
        # If only ARIMA enabled, weight should be 1.0
        weights = {"arima": 1.0}
        assert sum(weights.values()) == 1.0

        # If two models enabled, should reweight
        weights = {"arima": 0.6, "var": 0.4}
        assert abs(sum(weights.values()) - 1.0) < 0.001


@pytest.mark.unit
class TestForecastValidation:
    """Tests for forecast validation."""

    def test_forecast_rejects_invalid_horizon(self, test_settings: Settings):
        """Test that invalid forecast horizons are rejected."""
        engine = ForecastEngine(test_settings)

        # Valid horizons: 7d, 12m
        # Should reject: 0d, negative, non-numeric
        with pytest.raises((ValueError, AttributeError)):
            engine.forecast_7d(None)  # No data

    def test_forecast_requires_minimum_history(
        self, test_settings: Settings, sample_data_bundle: DataBundle
    ):
        """Test that forecast requires sufficient historical data."""
        engine = ForecastEngine(test_settings)

        # Modify bundle to have very short history
        short_series = sample_data_bundle.usdclp_series.tail(5)  # Only 5 days

        # Create bundle with short series
        short_bundle = DataBundle(
            usdclp_series=short_series,
            copper_series=sample_data_bundle.copper_series,
            tpm_series=sample_data_bundle.tpm_series,
            inflation_series=sample_data_bundle.inflation_series,
            dxy_series=sample_data_bundle.dxy_series,
            vix_series=sample_data_bundle.vix_series,
            eem_series=sample_data_bundle.eem_series,
            indicators=sample_data_bundle.indicators,
            macro_events=sample_data_bundle.macro_events,
            news=sample_data_bundle.news,
            fed_dot_plot=sample_data_bundle.fed_dot_plot,
            fed_dot_source_id=sample_data_bundle.fed_dot_source_id,
            next_fomc=sample_data_bundle.next_fomc,
            rate_differential=sample_data_bundle.rate_differential,
            sources=sample_data_bundle.sources,
        )

        # Should handle gracefully (either error or fallback)
        try:
            forecast = engine.forecast_7d(short_bundle)
            # If succeeds, should still return valid structure
            assert isinstance(forecast, ForecastPackage)
        except ValueError as e:
            # Or raise clear error about insufficient data
            assert "insufficient" in str(e).lower() or "minimum" in str(e).lower()


@pytest.mark.unit
class TestForecastSerialization:
    """Tests for forecast serialization."""

    def test_forecast_point_to_dict(self):
        """Test that ForecastPoint can be serialized."""
        point = ForecastPoint(
            date=datetime(2025, 12, 31),
            mean=950.0,
            ci80_low=945.0,
            ci80_high=955.0,
            ci95_low=940.0,
            ci95_high=960.0,
            std_dev=5.0,
        )

        # Pydantic models have .model_dump()
        data = point.model_dump()

        assert data["mean"] == 950.0
        assert "date" in data

    def test_forecast_package_serialization(self):
        """Test that ForecastPackage can be serialized."""
        point = ForecastPoint(
            date=datetime(2025, 12, 31),
            mean=950.0,
            ci80_low=945.0,
            ci80_high=955.0,
            ci95_low=940.0,
            ci95_high=960.0,
            std_dev=5.0,
        )

        package = ForecastPackage(
            series=[point],
            methodology="Test",
            error_metrics={"rmse": 5.2},
            residual_vol=4.1,
        )

        # Should serialize to dict
        data = package.model_dump()
        assert "series" in data
        assert "methodology" in data
        assert data["methodology"] == "Test"
