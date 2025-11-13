"""
Automated Performance Monitoring for Forecasting Models.

This module provides automated detection of model performance degradation
by comparing recent performance metrics against historical baselines.

Features:
- Automatic baseline establishment from historical performance
- Sliding window performance tracking
- Statistical significance testing for degradation
- Alert generation for performance drops
- Multi-horizon monitoring

Example:
    >>> monitor = PerformanceMonitor(data_dir=Path("data"))
    >>> report = monitor.check_performance(horizon="7d")
    >>> if report.degradation_detected:
    ...     print(f"Alert: {report.recommendation}")
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats


class PerformanceStatus(str, Enum):
    """Performance status levels."""

    EXCELLENT = "excellent"  # Better than baseline
    GOOD = "good"  # Within expected range
    DEGRADED = "degraded"  # Statistically worse than baseline
    CRITICAL = "critical"  # Severe degradation


@dataclass
class PerformanceBaseline:
    """
    Historical performance baseline for comparison.

    Attributes:
        metric: Metric name (rmse, mape, mae, etc.).
        mean: Baseline mean value.
        std: Baseline standard deviation.
        n_samples: Number of samples in baseline.
        period_start: Start of baseline period.
        period_end: End of baseline period.
    """

    metric: str
    mean: float
    std: float
    n_samples: int
    period_start: datetime
    period_end: datetime


@dataclass
class PerformanceMetrics:
    """
    Current performance metrics.

    Attributes:
        rmse: Root mean squared error.
        mae: Mean absolute error.
        mape: Mean absolute percentage error.
        ci95_coverage: CI95 coverage rate (0-1).
        bias: Mean bias (positive = over-prediction).
        n_predictions: Number of predictions evaluated.
    """

    rmse: float
    mae: float
    mape: float
    ci95_coverage: float
    bias: float
    n_predictions: int


@dataclass
class DegradationReport:
    """
    Performance degradation analysis report.

    Attributes:
        horizon: Forecast horizon being monitored.
        status: Current performance status.
        degradation_detected: Whether degradation is detected.
        recent_metrics: Recent performance metrics.
        baseline_metrics: Baseline metrics for comparison.
        degradation_pct: Percentage degradation vs baseline.
        p_value: Statistical significance (lower = more significant).
        recommendation: Action recommendation.
        timestamp: When check was performed.
    """

    horizon: str
    status: PerformanceStatus
    degradation_detected: bool
    recent_metrics: PerformanceMetrics
    baseline_metrics: Dict[str, PerformanceBaseline]
    degradation_pct: Dict[str, float]
    p_value: Dict[str, float]
    recommendation: str
    timestamp: datetime


class PerformanceMonitor:
    """
    Automated performance monitoring and degradation detection.

    Monitors forecast accuracy metrics (RMSE, MAPE, MAE) and compares
    recent performance against historical baseline to detect degradation.

    Args:
        data_dir: Directory containing predictions parquet file.
        baseline_days: Days of history for baseline (default: 60).
        recent_days: Days of recent data to check (default: 14).
        degradation_threshold: % degradation to trigger alert (default: 15%).
        significance_level: P-value threshold for statistical tests (default: 0.05).

    Example:
        >>> monitor = PerformanceMonitor(data_dir=Path("data"))
        >>> report = monitor.check_performance(horizon="7d")
        >>>
        >>> if report.degradation_detected:
        ...     print(f"Status: {report.status.value}")
        ...     print(f"RMSE degradation: {report.degradation_pct['rmse']:.1f}%")
        ...     print(report.recommendation)
    """

    def __init__(
        self,
        data_dir: Path,
        baseline_days: int = 60,
        recent_days: int = 14,
        degradation_threshold: float = 0.15,
        significance_level: float = 0.05,
    ):
        self.data_dir = data_dir
        self.baseline_days = baseline_days
        self.recent_days = recent_days
        self.degradation_threshold = degradation_threshold
        self.significance_level = significance_level

        self.predictions_path = data_dir / "predictions" / "predictions.parquet"

        logger.info(
            f"PerformanceMonitor initialized: baseline={baseline_days}d, "
            f"recent={recent_days}d, threshold={degradation_threshold:.0%}"
        )

    def check_performance(self, horizon: str) -> DegradationReport:
        """
        Check for performance degradation for a specific horizon.

        Args:
            horizon: Forecast horizon to check (e.g., "7d", "15d").

        Returns:
            DegradationReport with degradation analysis.

        Example:
            >>> report = monitor.check_performance("7d")
            >>> print(f"Status: {report.status.value}")
            >>> print(f"Degradation: {report.degradation_detected}")
        """
        logger.info(f"Checking performance for horizon: {horizon}")

        # Load predictions with actuals
        predictions = self._load_predictions_with_actuals(horizon)

        if len(predictions) == 0:
            logger.warning(f"No predictions with actuals for {horizon}")
            return self._create_no_data_report(horizon)

        # Split into baseline and recent periods
        baseline_df, recent_df = self._split_baseline_recent(predictions)

        if len(baseline_df) < 10:
            logger.warning(f"Insufficient baseline data for {horizon}: {len(baseline_df)} samples")
            return self._create_insufficient_baseline_report(horizon, recent_df)

        if len(recent_df) < 5:
            logger.warning(f"Insufficient recent data for {horizon}: {len(recent_df)} samples")
            return self._create_insufficient_recent_report(horizon, baseline_df)

        # Calculate metrics
        baseline_metrics = self._calculate_metrics(baseline_df)
        recent_metrics = self._calculate_metrics(recent_df)

        # Build baselines
        baselines = self._build_baselines(baseline_df, baseline_metrics)

        # Detect degradation
        degradation_pct, p_values = self._detect_degradation(
            recent_df, baseline_df, recent_metrics, baselines
        )

        # Determine status
        status, degradation_detected = self._determine_status(degradation_pct, p_values)

        # Generate recommendation
        recommendation = self._generate_recommendation(
            status, degradation_pct, p_values, recent_metrics, baselines
        )

        report = DegradationReport(
            horizon=horizon,
            status=status,
            degradation_detected=degradation_detected,
            recent_metrics=recent_metrics,
            baseline_metrics=baselines,
            degradation_pct=degradation_pct,
            p_value=p_values,
            recommendation=recommendation,
            timestamp=datetime.now(),
        )

        logger.info(
            f"Performance check complete: {horizon} - {status.value} "
            f"(degradation={degradation_detected})"
        )

        return report

    def check_all_horizons(self) -> Dict[str, DegradationReport]:
        """
        Check performance for all horizons.

        Returns:
            Dictionary mapping horizon to degradation report.

        Example:
            >>> reports = monitor.check_all_horizons()
            >>> for horizon, report in reports.items():
            ...     if report.degradation_detected:
            ...         print(f"{horizon}: {report.recommendation}")
        """
        horizons = ["7d", "15d", "30d", "90d"]
        reports = {}

        for horizon in horizons:
            try:
                reports[horizon] = self.check_performance(horizon)
            except Exception as e:
                logger.error(f"Failed to check {horizon}: {e}")

        return reports

    def _load_predictions_with_actuals(self, horizon: str) -> pd.DataFrame:
        """Load predictions that have actual values."""
        if not self.predictions_path.exists():
            return pd.DataFrame()

        df = pd.read_parquet(self.predictions_path)

        # Filter by horizon
        df = df[df["horizon"] == horizon]

        # Only predictions with actuals
        df = df[df["actual_value"].notna()]

        # Sort by forecast date
        df = df.sort_values("forecast_date")

        return df

    def _split_baseline_recent(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Split data into baseline and recent periods."""
        now = pd.Timestamp.now()

        # Recent period
        recent_cutoff = now - timedelta(days=self.recent_days)
        recent_df = df[df["forecast_date"] > recent_cutoff]

        # Baseline period (before recent period)
        baseline_end = recent_cutoff
        baseline_start = baseline_end - timedelta(days=self.baseline_days)
        baseline_df = df[
            (df["forecast_date"] > baseline_start) & (df["forecast_date"] <= baseline_end)
        ]

        logger.debug(
            f"Split: baseline={len(baseline_df)} ({baseline_start.date()} to {baseline_end.date()}), "
            f"recent={len(recent_df)} (last {self.recent_days} days)"
        )

        return baseline_df, recent_df

    def _calculate_metrics(self, df: pd.DataFrame) -> PerformanceMetrics:
        """Calculate performance metrics from predictions."""
        errors = df["actual_value"] - df["predicted_value"]
        abs_errors = np.abs(errors)
        pct_errors = abs_errors / np.abs(df["actual_value"])

        rmse = np.sqrt(np.mean(errors**2))
        mae = np.mean(abs_errors)
        mape = np.mean(pct_errors) * 100  # Percentage

        # CI95 coverage
        in_ci = (df["actual_value"] >= df["ci95_low"]) & (df["actual_value"] <= df["ci95_high"])
        ci95_coverage = in_ci.mean()

        # Bias (mean error)
        bias = np.mean(errors)

        return PerformanceMetrics(
            rmse=rmse,
            mae=mae,
            mape=mape,
            ci95_coverage=ci95_coverage,
            bias=bias,
            n_predictions=len(df),
        )

    def _build_baselines(
        self, baseline_df: pd.DataFrame, metrics: PerformanceMetrics
    ) -> Dict[str, PerformanceBaseline]:
        """Build baseline statistics for each metric."""
        # Calculate per-prediction errors for std calculation
        errors = baseline_df["actual_value"] - baseline_df["predicted_value"]
        abs_errors = np.abs(errors)
        pct_errors = abs_errors / np.abs(baseline_df["actual_value"])

        baselines = {
            "rmse": PerformanceBaseline(
                metric="rmse",
                mean=metrics.rmse,
                std=np.std(np.sqrt(errors**2)),  # Std of squared errors
                n_samples=len(baseline_df),
                period_start=baseline_df["forecast_date"].min().to_pydatetime(),
                period_end=baseline_df["forecast_date"].max().to_pydatetime(),
            ),
            "mae": PerformanceBaseline(
                metric="mae",
                mean=metrics.mae,
                std=np.std(abs_errors),
                n_samples=len(baseline_df),
                period_start=baseline_df["forecast_date"].min().to_pydatetime(),
                period_end=baseline_df["forecast_date"].max().to_pydatetime(),
            ),
            "mape": PerformanceBaseline(
                metric="mape",
                mean=metrics.mape,
                std=np.std(pct_errors) * 100,  # Percentage
                n_samples=len(baseline_df),
                period_start=baseline_df["forecast_date"].min().to_pydatetime(),
                period_end=baseline_df["forecast_date"].max().to_pydatetime(),
            ),
        }

        return baselines

    def _detect_degradation(
        self,
        recent_df: pd.DataFrame,
        baseline_df: pd.DataFrame,
        recent_metrics: PerformanceMetrics,
        baselines: Dict[str, PerformanceBaseline],
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Detect degradation using statistical tests.

        Returns:
            Tuple of (degradation_pct, p_values) dictionaries.
        """
        degradation_pct = {}
        p_values = {}

        # Calculate recent errors
        recent_errors = recent_df["actual_value"] - recent_df["predicted_value"]
        recent_abs_errors = np.abs(recent_errors)
        recent_pct_errors = recent_abs_errors / np.abs(recent_df["actual_value"])

        # Baseline errors
        baseline_errors = baseline_df["actual_value"] - baseline_df["predicted_value"]
        baseline_abs_errors = np.abs(baseline_errors)
        baseline_pct_errors = baseline_abs_errors / np.abs(baseline_df["actual_value"])

        # RMSE degradation
        degradation_pct["rmse"] = (
            (recent_metrics.rmse - baselines["rmse"].mean) / baselines["rmse"].mean
        ) * 100

        # Mann-Whitney U test (non-parametric, robust to outliers)
        _, p_rmse = stats.mannwhitneyu(
            np.abs(recent_errors), np.abs(baseline_errors), alternative="greater"
        )
        p_values["rmse"] = p_rmse

        # MAE degradation
        degradation_pct["mae"] = (
            (recent_metrics.mae - baselines["mae"].mean) / baselines["mae"].mean
        ) * 100

        _, p_mae = stats.mannwhitneyu(
            recent_abs_errors, baseline_abs_errors, alternative="greater"
        )
        p_values["mae"] = p_mae

        # MAPE degradation
        degradation_pct["mape"] = (
            (recent_metrics.mape - baselines["mape"].mean) / baselines["mape"].mean
        ) * 100

        _, p_mape = stats.mannwhitneyu(
            recent_pct_errors, baseline_pct_errors, alternative="greater"
        )
        p_values["mape"] = p_mape

        logger.debug(
            f"Degradation: RMSE={degradation_pct['rmse']:+.1f}% (p={p_rmse:.3f}), "
            f"MAE={degradation_pct['mae']:+.1f}% (p={p_mae:.3f}), "
            f"MAPE={degradation_pct['mape']:+.1f}% (p={p_mape:.3f})"
        )

        return degradation_pct, p_values

    def _determine_status(
        self, degradation_pct: Dict[str, float], p_values: Dict[str, float]
    ) -> Tuple[PerformanceStatus, bool]:
        """Determine overall performance status."""
        # Check if any metric shows statistically significant degradation
        significant_degradation = any(
            (degradation_pct[metric] > self.degradation_threshold * 100)
            and (p_values[metric] < self.significance_level)
            for metric in ["rmse", "mae", "mape"]
        )

        # Find max degradation
        max_degradation = max(degradation_pct.values())
        min_p_value = min(p_values.values())

        if significant_degradation:
            # Critical if >30% degradation with high significance
            if max_degradation > 30 and min_p_value < 0.01:
                return PerformanceStatus.CRITICAL, True
            else:
                return PerformanceStatus.DEGRADED, True

        # Check for improvement
        if max_degradation < -5 and all(d < 0 for d in degradation_pct.values()):
            return PerformanceStatus.EXCELLENT, False

        # Normal range
        return PerformanceStatus.GOOD, False

    def _generate_recommendation(
        self,
        status: PerformanceStatus,
        degradation_pct: Dict[str, float],
        p_values: Dict[str, float],
        recent_metrics: PerformanceMetrics,
        baselines: Dict[str, PerformanceBaseline],
    ) -> str:
        """Generate action recommendation based on status."""
        if status == PerformanceStatus.EXCELLENT:
            return (
                "✅ EXCELLENT: Performance better than baseline. "
                "Model is performing well - continue monitoring."
            )

        elif status == PerformanceStatus.GOOD:
            return (
                "✓ GOOD: Performance within expected range. "
                "No action needed - continue normal monitoring."
            )

        elif status == PerformanceStatus.DEGRADED:
            # Find worst metric
            worst_metric = max(degradation_pct, key=degradation_pct.get)
            worst_degradation = degradation_pct[worst_metric]
            worst_p_value = p_values[worst_metric]

            return (
                f"⚠ DEGRADED: Performance decline detected ({worst_metric.upper()}: "
                f"+{worst_degradation:.1f}%, p={worst_p_value:.3f}). "
                f"Recommendations: (1) Review recent predictions for systematic errors, "
                f"(2) Check for data quality issues, (3) Consider model retraining, "
                f"(4) Increase monitoring frequency."
            )

        else:  # CRITICAL
            worst_metric = max(degradation_pct, key=degradation_pct.get)
            worst_degradation = degradation_pct[worst_metric]

            return (
                f"✗ CRITICAL: Severe performance degradation ({worst_metric.upper()}: "
                f"+{worst_degradation:.1f}%). "
                f"IMMEDIATE ACTION REQUIRED: (1) Stop using affected model for decisions, "
                f"(2) Investigate root cause (data drift, market regime change), "
                f"(3) Retrain model with recent data, (4) Consider ensemble fallback."
            )

    def _create_no_data_report(self, horizon: str) -> DegradationReport:
        """Create report when no data available."""
        return DegradationReport(
            horizon=horizon,
            status=PerformanceStatus.GOOD,  # No news is good news
            degradation_detected=False,
            recent_metrics=PerformanceMetrics(0, 0, 0, 0, 0, 0),
            baseline_metrics={},
            degradation_pct={},
            p_value={},
            recommendation="No predictions with actuals available yet - unable to assess performance.",
            timestamp=datetime.now(),
        )

    def _create_insufficient_baseline_report(
        self, horizon: str, recent_df: pd.DataFrame
    ) -> DegradationReport:
        """Create report when baseline data insufficient."""
        recent_metrics = self._calculate_metrics(recent_df) if len(recent_df) > 0 else PerformanceMetrics(0, 0, 0, 0, 0, 0)

        return DegradationReport(
            horizon=horizon,
            status=PerformanceStatus.GOOD,
            degradation_detected=False,
            recent_metrics=recent_metrics,
            baseline_metrics={},
            degradation_pct={},
            p_value={},
            recommendation=f"Insufficient baseline data ({len(recent_df)} samples) - need {self.baseline_days} days of history.",
            timestamp=datetime.now(),
        )

    def _create_insufficient_recent_report(
        self, horizon: str, baseline_df: pd.DataFrame
    ) -> DegradationReport:
        """Create report when recent data insufficient."""
        baseline_metrics_calc = self._calculate_metrics(baseline_df)
        baselines = self._build_baselines(baseline_df, baseline_metrics_calc)

        return DegradationReport(
            horizon=horizon,
            status=PerformanceStatus.GOOD,
            degradation_detected=False,
            recent_metrics=PerformanceMetrics(0, 0, 0, 0, 0, 0),
            baseline_metrics=baselines,
            degradation_pct={},
            p_value={},
            recommendation=f"Insufficient recent data - need {self.recent_days} days of predictions with actuals.",
            timestamp=datetime.now(),
        )


__all__ = [
    "PerformanceMonitor",
    "DegradationReport",
    "PerformanceStatus",
    "PerformanceMetrics",
    "PerformanceBaseline",
]
