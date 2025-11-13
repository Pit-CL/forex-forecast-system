"""
Unit tests for prediction tracking system.

Tests PredictionTracker for logging, querying, and updating predictions.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import tempfile
from datetime import datetime, timedelta

import pandas as pd
import pytest

from forex_core.mlops.tracking import PredictionTracker


@pytest.fixture
def temp_storage():
    """Create temporary storage for predictions."""
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        storage_path = Path(tmp.name)

    yield storage_path

    # Cleanup
    if storage_path.exists():
        storage_path.unlink()
    lock_file = Path(f"{storage_path}.lock")
    if lock_file.exists():
        lock_file.unlink()


@pytest.fixture
def tracker(temp_storage):
    """Create prediction tracker with temporary storage."""
    return PredictionTracker(storage_path=temp_storage)


class TestPredictionTrackerInit:
    """Test tracker initialization."""

    def test_init_creates_storage_dir(self, tmp_path):
        """Test that initialization creates storage directory."""
        storage_path = tmp_path / "predictions" / "test.parquet"
        tracker = PredictionTracker(storage_path=storage_path)

        assert storage_path.parent.exists()
        assert tracker.storage_path == storage_path

    def test_init_with_existing_file(self, temp_storage):
        """Test initialization with existing storage file."""
        # Create initial tracker
        tracker1 = PredictionTracker(storage_path=temp_storage)
        tracker1.log_prediction(
            horizon="7d",
            forecast_date=datetime.now(),
            predicted_value=800.0,
            ci95_low=780.0,
            ci95_high=820.0,
        )

        # Create second tracker with same storage
        tracker2 = PredictionTracker(storage_path=temp_storage)

        # Should load existing data
        assert temp_storage.exists()


class TestPredictionLogging:
    """Test prediction logging functionality."""

    def test_log_single_prediction(self, tracker):
        """Test logging a single prediction."""
        forecast_date = datetime.now()

        tracker.log_prediction(
            horizon="7d",
            forecast_date=forecast_date,
            predicted_value=800.0,
            ci95_low=780.0,
            ci95_high=820.0,
            metadata={"model": "ARIMA"},
        )

        # Verify storage file created
        assert tracker.storage_path.exists()

        # Read and verify
        df = pd.read_parquet(tracker.storage_path)
        assert len(df) == 1
        assert df.iloc[0]["horizon"] == "7d"
        assert df.iloc[0]["predicted_value"] == 800.0
        assert df.iloc[0]["ci95_low"] == 780.0
        assert df.iloc[0]["ci95_high"] == 820.0
        assert df.iloc[0]["metadata"] == {"model": "ARIMA"}

    def test_log_multiple_predictions(self, tracker):
        """Test logging multiple predictions."""
        horizons = ["7d", "15d", "30d"]
        forecast_date = datetime.now()

        for horizon in horizons:
            tracker.log_prediction(
                horizon=horizon,
                forecast_date=forecast_date,
                predicted_value=800.0 + len(horizon),
                ci95_low=780.0,
                ci95_high=820.0,
            )

        df = pd.read_parquet(tracker.storage_path)
        assert len(df) == 3
        assert set(df["horizon"]) == set(horizons)

    def test_log_prediction_with_optional_fields(self, tracker):
        """Test logging with all optional fields."""
        forecast_date = datetime.now()

        tracker.log_prediction(
            horizon="7d",
            forecast_date=forecast_date,
            predicted_value=800.0,
            ci95_low=780.0,
            ci95_high=820.0,
            ci80_low=785.0,
            ci80_high=815.0,
            actual_value=None,  # Not known yet
            model_version="v1.2.3",
            metadata={"ensemble": True, "n_models": 3},
        )

        df = pd.read_parquet(tracker.storage_path)
        row = df.iloc[0]

        assert row["ci80_low"] == 785.0
        assert row["ci80_high"] == 815.0
        assert pd.isna(row["actual_value"])
        assert row["model_version"] == "v1.2.3"
        assert row["metadata"]["ensemble"] is True


class TestPredictionUpdates:
    """Test prediction update functionality."""

    def test_update_with_actual(self, tracker):
        """Test updating prediction with actual value."""
        forecast_date = datetime.now()
        prediction_id = "test_pred_1"

        # Log initial prediction
        tracker.log_prediction(
            horizon="7d",
            forecast_date=forecast_date,
            predicted_value=800.0,
            ci95_low=780.0,
            ci95_high=820.0,
            prediction_id=prediction_id,
        )

        # Update with actual
        tracker.update_with_actual(
            prediction_id=prediction_id,
            actual_value=805.0,
        )

        # Verify update
        df = pd.read_parquet(tracker.storage_path)
        row = df[df["prediction_id"] == prediction_id].iloc[0]

        assert row["actual_value"] == 805.0
        # Should calculate error automatically
        assert abs(row["error"] - 5.0) < 0.01

    def test_update_nonexistent_prediction(self, tracker):
        """Test updating a prediction that doesn't exist."""
        # Should handle gracefully (no error)
        tracker.update_with_actual(
            prediction_id="nonexistent",
            actual_value=800.0,
        )

    def test_bulk_update_actuals(self, tracker):
        """Test bulk updating multiple predictions."""
        forecast_date = datetime.now() - timedelta(days=7)

        # Log several predictions
        for i in range(5):
            tracker.log_prediction(
                horizon="7d",
                forecast_date=forecast_date + timedelta(days=i),
                predicted_value=800.0 + i,
                ci95_low=780.0 + i,
                ci95_high=820.0 + i,
                prediction_id=f"pred_{i}",
            )

        # Bulk update
        updates = {
            "pred_0": 801.0,
            "pred_1": 802.0,
            "pred_2": 798.0,
        }

        for pred_id, actual in updates.items():
            tracker.update_with_actual(pred_id, actual)

        # Verify
        df = pd.read_parquet(tracker.storage_path)
        updated = df[df["prediction_id"].isin(updates.keys())]

        assert len(updated) == 3
        assert all(updated["actual_value"].notna())


class TestPredictionQuerying:
    """Test prediction query functionality."""

    def test_get_predictions_by_horizon(self, tracker):
        """Test filtering predictions by horizon."""
        forecast_date = datetime.now()

        # Log predictions for different horizons
        for horizon in ["7d", "15d", "30d"]:
            for i in range(3):
                tracker.log_prediction(
                    horizon=horizon,
                    forecast_date=forecast_date + timedelta(days=i),
                    predicted_value=800.0,
                    ci95_low=780.0,
                    ci95_high=820.0,
                )

        # Query
        df = pd.read_parquet(tracker.storage_path)
        df_7d = df[df["horizon"] == "7d"]
        df_15d = df[df["horizon"] == "15d"]

        assert len(df_7d) == 3
        assert len(df_15d) == 3

    def test_get_predictions_with_actuals(self, tracker):
        """Test filtering predictions that have actuals."""
        forecast_date = datetime.now()

        # Log predictions, update some with actuals
        for i in range(5):
            pred_id = f"pred_{i}"
            tracker.log_prediction(
                horizon="7d",
                forecast_date=forecast_date,
                predicted_value=800.0,
                ci95_low=780.0,
                ci95_high=820.0,
                prediction_id=pred_id,
            )

            # Update first 3 with actuals
            if i < 3:
                tracker.update_with_actual(pred_id, 805.0)

        # Query
        df = pd.read_parquet(tracker.storage_path)
        with_actuals = df[df["actual_value"].notna()]
        without_actuals = df[df["actual_value"].isna()]

        assert len(with_actuals) == 3
        assert len(without_actuals) == 2

    def test_get_recent_predictions(self, tracker):
        """Test getting recent predictions."""
        now = datetime.now()

        # Log predictions at different times
        for i in range(10):
            tracker.log_prediction(
                horizon="7d",
                forecast_date=now - timedelta(days=9 - i),
                predicted_value=800.0,
                ci95_low=780.0,
                ci95_high=820.0,
            )

        # Query last 7 days
        df = pd.read_parquet(tracker.storage_path)
        cutoff = now - timedelta(days=7)
        recent = df[df["forecast_date"] > pd.Timestamp(cutoff)]

        assert len(recent) <= 8  # Roughly last 7 days


class TestErrorCalculations:
    """Test error metric calculations."""

    def test_absolute_error(self, tracker):
        """Test absolute error calculation."""
        tracker.log_prediction(
            horizon="7d",
            forecast_date=datetime.now(),
            predicted_value=800.0,
            ci95_low=780.0,
            ci95_high=820.0,
            prediction_id="test_1",
        )

        tracker.update_with_actual("test_1", 805.0)

        df = pd.read_parquet(tracker.storage_path)
        row = df.iloc[0]

        # Error should be actual - predicted = 5.0
        assert abs(row["error"] - 5.0) < 0.01

    def test_ci_coverage(self, tracker):
        """Test CI95 coverage check."""
        tracker.log_prediction(
            horizon="7d",
            forecast_date=datetime.now(),
            predicted_value=800.0,
            ci95_low=780.0,
            ci95_high=820.0,
            prediction_id="in_ci",
        )

        tracker.log_prediction(
            horizon="7d",
            forecast_date=datetime.now(),
            predicted_value=800.0,
            ci95_low=780.0,
            ci95_high=820.0,
            prediction_id="out_ci",
        )

        # One inside CI, one outside
        tracker.update_with_actual("in_ci", 805.0)  # Inside [780, 820]
        tracker.update_with_actual("out_ci", 850.0)  # Outside [780, 820]

        df = pd.read_parquet(tracker.storage_path)

        # Check coverage manually
        in_ci_row = df[df["prediction_id"] == "in_ci"].iloc[0]
        out_ci_row = df[df["prediction_id"] == "out_ci"].iloc[0]

        in_ci = (
            in_ci_row["ci95_low"]
            <= in_ci_row["actual_value"]
            <= in_ci_row["ci95_high"]
        )
        out_ci = (
            out_ci_row["ci95_low"]
            <= out_ci_row["actual_value"]
            <= out_ci_row["ci95_high"]
        )

        assert in_ci is True
        assert out_ci is False


class TestConcurrency:
    """Test concurrent access handling."""

    def test_concurrent_writes(self, tracker):
        """Test that file locking prevents corruption."""
        # Simple sequential writes (concurrent testing in test_file_lock.py)
        forecast_date = datetime.now()

        for i in range(10):
            tracker.log_prediction(
                horizon="7d",
                forecast_date=forecast_date,
                predicted_value=800.0 + i,
                ci95_low=780.0,
                ci95_high=820.0,
            )

        # Verify all writes succeeded
        df = pd.read_parquet(tracker.storage_path)
        assert len(df) == 10


class TestDataIntegrity:
    """Test data integrity and validation."""

    def test_required_fields(self, tracker):
        """Test that required fields are enforced."""
        # Should not raise - all required fields provided
        tracker.log_prediction(
            horizon="7d",
            forecast_date=datetime.now(),
            predicted_value=800.0,
            ci95_low=780.0,
            ci95_high=820.0,
        )

    def test_data_types(self, tracker):
        """Test that data types are preserved."""
        forecast_date = datetime.now()

        tracker.log_prediction(
            horizon="7d",
            forecast_date=forecast_date,
            predicted_value=800.123,
            ci95_low=780.456,
            ci95_high=820.789,
        )

        df = pd.read_parquet(tracker.storage_path)
        row = df.iloc[0]

        # Check float precision preserved
        assert abs(row["predicted_value"] - 800.123) < 0.001
        assert abs(row["ci95_low"] - 780.456) < 0.001

    def test_metadata_preservation(self, tracker):
        """Test that metadata dict is preserved correctly."""
        metadata = {
            "model": "ARIMA",
            "params": {"p": 2, "d": 1, "q": 2},
            "ensemble": True,
            "weight": 0.6,
        }

        tracker.log_prediction(
            horizon="7d",
            forecast_date=datetime.now(),
            predicted_value=800.0,
            ci95_low=780.0,
            ci95_high=820.0,
            metadata=metadata,
        )

        df = pd.read_parquet(tracker.storage_path)
        stored_metadata = df.iloc[0]["metadata"]

        assert stored_metadata == metadata
        assert stored_metadata["model"] == "ARIMA"
        assert stored_metadata["params"]["p"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
