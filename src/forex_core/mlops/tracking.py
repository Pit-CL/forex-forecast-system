"""
Prediction tracking system for monitoring real-world forecast performance.

This module implements a production-grade tracking system that:
1. Logs predictions with full metadata (forecast date, horizon, confidence intervals)
2. Updates actual values as they become available
3. Calculates out-of-sample performance metrics (RMSE, MAE, MAPE)
4. Provides calibration diagnostics (CI coverage, directional accuracy)

The system uses Parquet for efficient storage and supports concurrent writes
from multiple forecasting services.

Example:
    >>> from forex_core.mlops.tracking import PredictionTracker
    >>> from datetime import datetime
    >>>
    >>> tracker = PredictionTracker()
    >>>
    >>> # Log a new prediction
    >>> tracker.log_prediction(
    ...     forecast_date=datetime(2025, 1, 10),
    ...     horizon="7d",
    ...     target_date=datetime(2025, 1, 17),
    ...     predicted_mean=950.5,
    ...     ci95_low=945.0,
    ...     ci95_high=956.0
    ... )
    >>>
    >>> # Update actuals when data becomes available
    >>> tracker.update_actuals()
    >>>
    >>> # Get recent performance metrics
    >>> perf = tracker.get_recent_performance(horizon="7d", days=30)
    >>> print(f"RMSE: {perf['rmse']:.2f}")
    >>> print(f"MAPE: {perf['mape']:.2%}")
    >>> print(f"CI95 Coverage: {perf['ci95_coverage']:.2%}")
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from loguru import logger

from forex_core.config import get_settings
from forex_core.data import DataLoader
from forex_core.utils.file_lock import ParquetFileLock


class PredictionTracker:
    """
    Thread-safe prediction tracker for monitoring forecast performance.

    Maintains a persistent Parquet database of predictions with actual outcomes,
    enabling calculation of true out-of-sample performance metrics.

    Attributes:
        storage_path: Path to Parquet file storing predictions.
        lock: Threading lock for concurrent write safety.

    Schema:
        - forecast_date: When the prediction was made (datetime64[ns])
        - horizon: Forecast horizon ("7d", "15d", "30d", "90d")
        - target_date: Date being predicted (datetime64[ns])
        - predicted_mean: Point forecast (float64)
        - ci95_low: Lower bound of 95% CI (float64)
        - ci95_high: Upper bound of 95% CI (float64)
        - actual_value: Realized value when available (float64, nullable)
        - error: predicted_mean - actual_value (float64, nullable)
        - abs_error: |error| (float64, nullable)
        - pct_error: error / actual_value (float64, nullable)
        - logged_at: Record creation timestamp (datetime64[ns])
        - updated_at: Last update timestamp (datetime64[ns])
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize prediction tracker.

        Args:
            storage_path: Custom path for Parquet storage.
                         If None, uses default data/predictions/predictions.parquet.
        """
        if storage_path is None:
            settings = get_settings()
            self.storage_path = settings.data_dir / "predictions" / "predictions.parquet"
        else:
            self.storage_path = storage_path

        # Ensure parent directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Thread safety lock
        self.lock = threading.Lock()

        # Initialize storage if it doesn't exist
        if not self.storage_path.exists():
            self._initialize_storage()

        logger.info(f"PredictionTracker initialized: {self.storage_path}")

    def _initialize_storage(self) -> None:
        """Create empty Parquet file with correct schema."""
        schema = pa.schema([
            ("forecast_date", pa.timestamp("ns")),
            ("horizon", pa.string()),
            ("target_date", pa.timestamp("ns")),
            ("predicted_mean", pa.float64()),
            ("ci95_low", pa.float64()),
            ("ci95_high", pa.float64()),
            ("actual_value", pa.float64()),  # Nullable
            ("error", pa.float64()),  # Nullable
            ("abs_error", pa.float64()),  # Nullable
            ("pct_error", pa.float64()),  # Nullable
            ("logged_at", pa.timestamp("ns")),
            ("updated_at", pa.timestamp("ns")),
        ])

        # Create empty table
        empty_df = pd.DataFrame({
            "forecast_date": pd.Series(dtype="datetime64[ns]"),
            "horizon": pd.Series(dtype="str"),
            "target_date": pd.Series(dtype="datetime64[ns]"),
            "predicted_mean": pd.Series(dtype="float64"),
            "ci95_low": pd.Series(dtype="float64"),
            "ci95_high": pd.Series(dtype="float64"),
            "actual_value": pd.Series(dtype="float64"),
            "error": pd.Series(dtype="float64"),
            "abs_error": pd.Series(dtype="float64"),
            "pct_error": pd.Series(dtype="float64"),
            "logged_at": pd.Series(dtype="datetime64[ns]"),
            "updated_at": pd.Series(dtype="datetime64[ns]"),
        })

        table = pa.Table.from_pandas(empty_df, schema=schema)
        pq.write_table(table, self.storage_path)
        logger.info(f"Initialized prediction storage: {self.storage_path}")

    def log_prediction(
        self,
        forecast_date: datetime,
        horizon: str,
        target_date: datetime,
        predicted_mean: float,
        ci95_low: float,
        ci95_high: float,
    ) -> None:
        """
        Log a new prediction to the tracking database.

        Args:
            forecast_date: Date when forecast was generated.
            horizon: Forecast horizon ("7d", "15d", "30d", "90d").
            target_date: Date being predicted.
            predicted_mean: Point forecast (mean prediction).
            ci95_low: Lower bound of 95% confidence interval.
            ci95_high: Upper bound of 95% confidence interval.

        Raises:
            ValueError: If input validation fails.
            IOError: If storage write fails.

        Example:
            >>> tracker = PredictionTracker()
            >>> tracker.log_prediction(
            ...     forecast_date=datetime(2025, 1, 10),
            ...     horizon="7d",
            ...     target_date=datetime(2025, 1, 17),
            ...     predicted_mean=950.5,
            ...     ci95_low=945.0,
            ...     ci95_high=956.0
            ... )
        """
        # Validation
        if horizon not in ["7d", "15d", "30d", "90d"]:
            raise ValueError(f"Invalid horizon: {horizon}. Must be 7d, 15d, 30d, or 90d")

        if target_date <= forecast_date:
            raise ValueError(f"target_date ({target_date}) must be after forecast_date ({forecast_date})")

        if not (ci95_low <= predicted_mean <= ci95_high):
            raise ValueError(
                f"Invalid confidence interval: ci95_low={ci95_low}, "
                f"mean={predicted_mean}, ci95_high={ci95_high}"
            )

        now = datetime.now()

        # Create new record
        new_record = pd.DataFrame([{
            "forecast_date": forecast_date,
            "horizon": horizon,
            "target_date": target_date,
            "predicted_mean": predicted_mean,
            "ci95_low": ci95_low,
            "ci95_high": ci95_high,
            "actual_value": None,
            "error": None,
            "abs_error": None,
            "pct_error": None,
            "logged_at": now,
            "updated_at": now,
        }])

        # Process-safe append using file lock
        # Note: self.lock is kept for backward compatibility but ParquetFileLock
        # provides true multi-process safety
        with self.lock:
            try:
                # Acquire file lock for multi-process safety
                with ParquetFileLock(self.storage_path, timeout=30.0):
                    # Read existing data
                    if self.storage_path.exists() and self.storage_path.stat().st_size > 0:
                        existing_df = pd.read_parquet(self.storage_path)

                        # Check for duplicate prediction
                        duplicate_mask = (
                            (existing_df["forecast_date"] == forecast_date) &
                            (existing_df["horizon"] == horizon) &
                            (existing_df["target_date"] == target_date)
                        )

                        if duplicate_mask.any():
                            logger.warning(
                                f"Duplicate prediction exists for forecast_date={forecast_date}, "
                                f"horizon={horizon}, target_date={target_date}. Skipping."
                            )
                            return

                        # Append new record
                        combined_df = pd.concat([existing_df, new_record], ignore_index=True)
                    else:
                        combined_df = new_record

                    # Write back to storage (inside lock)
                    combined_df.to_parquet(self.storage_path, index=False)

                    logger.info(
                        f"Logged prediction: horizon={horizon}, "
                        f"target_date={target_date.date()}, "
                        f"predicted_mean={predicted_mean:.2f}"
                    )

            except TimeoutError as e:
                logger.error(f"Timeout acquiring file lock for {self.storage_path}: {e}")
                raise IOError(f"Failed to acquire file lock: {e}") from e
            except Exception as e:
                logger.error(f"Failed to log prediction: {e}")
                raise IOError(f"Failed to write prediction: {e}") from e

    def update_actuals(self, lookback_days: int = 365) -> int:
        """
        Update actual values for predictions whose target dates have passed.

        Fetches latest USD/CLP data and updates predictions that now have
        realized values available. Only updates predictions within lookback window
        to avoid processing very old data.

        Args:
            lookback_days: How far back to look for predictions to update (default: 365).

        Returns:
            Number of predictions updated.

        Example:
            >>> tracker = PredictionTracker()
            >>> updated = tracker.update_actuals()
            >>> print(f"Updated {updated} predictions with actual values")
        """
        with self.lock:
            try:
                # Read existing predictions
                if not self.storage_path.exists() or self.storage_path.stat().st_size == 0:
                    logger.info("No predictions to update")
                    return 0

                df = pd.read_parquet(self.storage_path)

                if len(df) == 0:
                    logger.info("No predictions to update")
                    return 0

                # Filter: predictions without actuals and within lookback window
                cutoff_date = datetime.now() - timedelta(days=lookback_days)
                mask_needs_update = (
                    df["actual_value"].isna() &
                    (df["target_date"] < pd.Timestamp.now()) &
                    (df["forecast_date"] >= pd.Timestamp(cutoff_date))
                )

                if not mask_needs_update.any():
                    logger.info("No predictions need updating")
                    return 0

                # Load actual data
                logger.info("Fetching actual USD/CLP data...")
                settings = get_settings()
                loader = DataLoader(settings)
                bundle = loader.load()
                usdclp_series = bundle.usdclp_series

                # Update each prediction
                updates_count = 0
                for idx in df[mask_needs_update].index:
                    target_date = df.loc[idx, "target_date"]
                    predicted_mean = df.loc[idx, "predicted_mean"]
                    ci95_low = df.loc[idx, "ci95_low"]
                    ci95_high = df.loc[idx, "ci95_high"]

                    # Try to find actual value (match by date)
                    try:
                        # Convert target_date to date for matching
                        target_date_only = pd.Timestamp(target_date).date()

                        # Look for exact match in usdclp_series (index should be dates)
                        if target_date_only in usdclp_series.index.date:
                            actual_value = float(usdclp_series.loc[target_date_only])

                            # Calculate errors
                            error = predicted_mean - actual_value
                            abs_error = abs(error)
                            pct_error = error / actual_value if actual_value != 0 else None

                            # Update record
                            df.loc[idx, "actual_value"] = actual_value
                            df.loc[idx, "error"] = error
                            df.loc[idx, "abs_error"] = abs_error
                            df.loc[idx, "pct_error"] = pct_error
                            df.loc[idx, "updated_at"] = pd.Timestamp.now()

                            updates_count += 1

                            logger.debug(
                                f"Updated: target={target_date_only}, "
                                f"predicted={predicted_mean:.2f}, "
                                f"actual={actual_value:.2f}, "
                                f"error={error:.2f}"
                            )
                        else:
                            # Try to find nearest date (within +/- 3 days)
                            nearest_dates = [
                                target_date_only + timedelta(days=d)
                                for d in range(-3, 4)
                            ]

                            found = False
                            for near_date in nearest_dates:
                                if near_date in usdclp_series.index.date:
                                    actual_value = float(usdclp_series.loc[near_date])

                                    error = predicted_mean - actual_value
                                    abs_error = abs(error)
                                    pct_error = error / actual_value if actual_value != 0 else None

                                    df.loc[idx, "actual_value"] = actual_value
                                    df.loc[idx, "error"] = error
                                    df.loc[idx, "abs_error"] = abs_error
                                    df.loc[idx, "pct_error"] = pct_error
                                    df.loc[idx, "updated_at"] = pd.Timestamp.now()

                                    updates_count += 1
                                    found = True

                                    logger.debug(
                                        f"Updated (nearest): target={target_date_only}, "
                                        f"used={near_date}, predicted={predicted_mean:.2f}, "
                                        f"actual={actual_value:.2f}"
                                    )
                                    break

                            if not found:
                                logger.debug(
                                    f"No actual data available for target_date={target_date_only}"
                                )

                    except Exception as e:
                        logger.warning(
                            f"Failed to update prediction for target_date={target_date}: {e}"
                        )
                        continue

                # Write updated data back (with file lock for process safety)
                if updates_count > 0:
                    with ParquetFileLock(self.storage_path, timeout=30.0):
                        df.to_parquet(self.storage_path, index=False)
                    logger.success(f"Updated {updates_count} predictions with actual values")
                else:
                    logger.info("No predictions could be updated (data not yet available)")

                return updates_count

            except TimeoutError as e:
                logger.error(f"Timeout acquiring file lock for {self.storage_path}: {e}")
                return 0
            except Exception as e:
                logger.error(f"Failed to update actuals: {e}")
                return 0

    def get_recent_performance(
        self,
        horizon: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, float]:
        """
        Calculate out-of-sample performance metrics for recent predictions.

        Computes true performance metrics using only predictions that have
        actual values available. These are genuine out-of-sample metrics,
        unlike in-sample training metrics.

        Args:
            horizon: Filter by specific horizon ("7d", "15d", "30d", "90d").
                    If None, calculates across all horizons.
            days: Look back this many days for forecast_date (default: 30).

        Returns:
            Dictionary with performance metrics:
                - rmse: Root Mean Squared Error
                - mae: Mean Absolute Error
                - mape: Mean Absolute Percentage Error (as decimal, e.g., 0.05 = 5%)
                - ci95_coverage: % of actuals within 95% CI (as decimal)
                - directional_accuracy: % correct direction predictions (as decimal)
                - n_predictions: Number of predictions with actuals
                - n_total: Total predictions in period

        Example:
            >>> tracker = PredictionTracker()
            >>> perf = tracker.get_recent_performance(horizon="7d", days=30)
            >>> print(f"RMSE: {perf['rmse']:.2f} CLP")
            >>> print(f"MAPE: {perf['mape']:.2%}")
            >>> print(f"CI95 Coverage: {perf['ci95_coverage']:.1%}")
            >>> print(f"Sample: {perf['n_predictions']} predictions")
        """
        try:
            # Read predictions
            if not self.storage_path.exists() or self.storage_path.stat().st_size == 0:
                logger.warning("No predictions available for performance calculation")
                return self._empty_metrics()

            df = pd.read_parquet(self.storage_path)

            if len(df) == 0:
                logger.warning("No predictions available for performance calculation")
                return self._empty_metrics()

            # Filter by recent forecasts
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_mask = df["forecast_date"] >= pd.Timestamp(cutoff_date)

            # Filter by horizon if specified
            if horizon is not None:
                if horizon not in ["7d", "15d", "30d", "90d"]:
                    raise ValueError(f"Invalid horizon: {horizon}")
                recent_mask &= df["horizon"] == horizon

            recent_df = df[recent_mask]

            if len(recent_df) == 0:
                logger.info(f"No recent predictions found for horizon={horizon}, days={days}")
                return self._empty_metrics()

            # Filter predictions with actuals
            with_actuals = recent_df[recent_df["actual_value"].notna()].copy()

            if len(with_actuals) == 0:
                logger.info(
                    f"No predictions with actuals yet for horizon={horizon}, days={days}. "
                    f"Total recent predictions: {len(recent_df)}"
                )
                return {
                    "rmse": None,
                    "mae": None,
                    "mape": None,
                    "ci95_coverage": None,
                    "directional_accuracy": None,
                    "n_predictions": 0,
                    "n_total": len(recent_df),
                }

            # Calculate metrics
            rmse = float((with_actuals["error"] ** 2).mean() ** 0.5)
            mae = float(with_actuals["abs_error"].mean())
            mape = float(with_actuals["pct_error"].abs().mean())

            # CI95 coverage: % of actuals within CI
            within_ci = (
                (with_actuals["actual_value"] >= with_actuals["ci95_low"]) &
                (with_actuals["actual_value"] <= with_actuals["ci95_high"])
            )
            ci95_coverage = float(within_ci.mean())

            # Directional accuracy: did we predict up/down correctly?
            # Need previous actual value to determine direction
            with_actuals = with_actuals.sort_values("target_date")

            # Get previous actual for each prediction (shift by target_date)
            directional_correct = []
            for idx in with_actuals.index:
                target_date = with_actuals.loc[idx, "target_date"]
                forecast_date = with_actuals.loc[idx, "forecast_date"]
                predicted_mean = with_actuals.loc[idx, "predicted_mean"]
                actual_value = with_actuals.loc[idx, "actual_value"]

                # Find the actual value at forecast_date (baseline for direction)
                baseline_mask = (
                    df["target_date"] <= pd.Timestamp(forecast_date)
                ) & (
                    df["actual_value"].notna()
                )

                if baseline_mask.any():
                    # Get closest available actual before forecast
                    baseline_df = df[baseline_mask].sort_values("target_date", ascending=False)
                    if len(baseline_df) > 0:
                        baseline_value = baseline_df.iloc[0]["actual_value"]

                        # Compare directions
                        predicted_direction = predicted_mean - baseline_value
                        actual_direction = actual_value - baseline_value

                        # Same sign = correct direction
                        if predicted_direction * actual_direction > 0:
                            directional_correct.append(True)
                        elif predicted_direction * actual_direction < 0:
                            directional_correct.append(False)
                        # If either is exactly 0, skip

            if directional_correct:
                directional_accuracy = sum(directional_correct) / len(directional_correct)
            else:
                directional_accuracy = None

            metrics = {
                "rmse": rmse,
                "mae": mae,
                "mape": mape,
                "ci95_coverage": ci95_coverage,
                "directional_accuracy": directional_accuracy,
                "n_predictions": len(with_actuals),
                "n_total": len(recent_df),
            }

            logger.debug(
                f"Performance calculated: RMSE={rmse:.2f}, MAE={mae:.2f}, "
                f"MAPE={mape:.2%}, CI95_cov={ci95_coverage:.2%}, "
                f"n={len(with_actuals)}/{len(recent_df)}"
            )

            return metrics

        except Exception as e:
            logger.error(f"Failed to calculate performance metrics: {e}")
            return self._empty_metrics()

    def _empty_metrics(self) -> Dict[str, Optional[float]]:
        """Return empty metrics structure."""
        return {
            "rmse": None,
            "mae": None,
            "mape": None,
            "ci95_coverage": None,
            "directional_accuracy": None,
            "n_predictions": 0,
            "n_total": 0,
        }

    def get_predictions_summary(self, days: int = 90) -> pd.DataFrame:
        """
        Get summary of all predictions in recent period.

        Args:
            days: Look back this many days (default: 90).

        Returns:
            DataFrame with all predictions and their status.

        Example:
            >>> tracker = PredictionTracker()
            >>> summary = tracker.get_predictions_summary(days=30)
            >>> print(summary.groupby("horizon")["actual_value"].count())
        """
        try:
            if not self.storage_path.exists() or self.storage_path.stat().st_size == 0:
                logger.info("No predictions available")
                return pd.DataFrame()

            df = pd.read_parquet(self.storage_path)

            # Filter recent
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_df = df[df["forecast_date"] >= pd.Timestamp(cutoff_date)].copy()

            if len(recent_df) == 0:
                logger.info(f"No predictions in last {days} days")
                return pd.DataFrame()

            # Sort by forecast date
            recent_df = recent_df.sort_values("forecast_date", ascending=False)

            return recent_df

        except Exception as e:
            logger.error(f"Failed to get predictions summary: {e}")
            return pd.DataFrame()

    def get_latest_prediction(self, horizon: str) -> Optional[Dict]:
        """
        Get the most recent prediction for a specific horizon.

        Args:
            horizon: Forecast horizon ("7d", "15d", "30d", "90d").

        Returns:
            Dictionary with latest prediction data, or None if no predictions exist.
            Keys: forecast_date, target_date, prediction, ci95_low, ci95_high.

        Example:
            >>> tracker = PredictionTracker()
            >>> latest = tracker.get_latest_prediction("7d")
            >>> if latest:
            ...     print(f"Latest 7d forecast: {latest['prediction']:.2f}")
        """
        try:
            if not self.storage_path.exists() or self.storage_path.stat().st_size == 0:
                logger.debug(f"No predictions available for {horizon}")
                return None

            df = pd.read_parquet(self.storage_path)

            # Filter by horizon
            horizon_df = df[df["horizon"] == horizon].copy()

            if len(horizon_df) == 0:
                logger.debug(f"No predictions found for horizon {horizon}")
                return None

            # Get most recent forecast
            latest_row = horizon_df.loc[horizon_df["forecast_date"].idxmax()]

            return {
                "forecast_date": latest_row["forecast_date"],
                "target_date": latest_row["target_date"],
                "prediction": latest_row["predicted_mean"],
                "ci95_low": latest_row["ci95_low"],
                "ci95_high": latest_row["ci95_high"],
            }

        except Exception as e:
            logger.error(f"Failed to get latest prediction for {horizon}: {e}")
            return None


__all__ = ["PredictionTracker"]
