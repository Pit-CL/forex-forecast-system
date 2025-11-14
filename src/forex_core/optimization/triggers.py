"""
Optimization Trigger Management.

Determines WHEN model optimization should be triggered based on:
1. Performance degradation (RMSE, MAPE increase)
2. Data drift detection (distribution changes)
3. Time-based fallback (minimum days between optimizations)

Example:
    >>> trigger_manager = OptimizationTriggerManager(data_dir=Path("data"))
    >>> report = trigger_manager.should_optimize("7d", usdclp_series)
    >>> if report.should_optimize:
    ...     print(f"Optimization triggered: {report.reasons}")
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger

from ..mlops.monitoring import DataDriftDetector, DriftSeverity
from ..mlops.performance_monitor import PerformanceMonitor, PerformanceStatus


@dataclass
class TriggerReport:
    """
    Report on whether optimization should be triggered.

    Attributes:
        horizon: Forecast horizon being checked.
        should_optimize: Whether optimization should be triggered.
        reasons: List of reasons why optimization was triggered.
        performance_degradation: Performance degradation percentage (if applicable).
        drift_severity: Drift severity level (if applicable).
        days_since_last_optimization: Days since last optimization.
        timestamp: When the check was performed.
    """

    horizon: str
    should_optimize: bool
    reasons: list[str]
    performance_degradation: Optional[float] = None
    drift_severity: Optional[str] = None
    days_since_last_optimization: Optional[int] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class OptimizationTriggerManager:
    """
    Manages optimization trigger logic for model retraining/recalibration.

    Checks multiple conditions to determine if optimization is needed:
    - Performance degradation above threshold
    - Data drift detection
    - Time-based fallback

    Args:
        data_dir: Directory containing predictions and drift history.
        performance_threshold: Degradation % to trigger (default: 15%).
        drift_severity_threshold: Minimum drift severity to trigger.
        min_days_between_optimizations: Minimum days between optimizations.

    Example:
        >>> manager = OptimizationTriggerManager(data_dir=Path("data"))
        >>> report = manager.should_optimize("7d", usdclp_series)
        >>>
        >>> if report.should_optimize:
        ...     print("Reasons:", report.reasons)
        ...     # Proceed with optimization
    """

    def __init__(
        self,
        data_dir: Path,
        performance_threshold: float = 15.0,
        drift_severity_threshold: DriftSeverity = DriftSeverity.MEDIUM,
        min_days_between_optimizations: int = 14,
    ):
        self.data_dir = data_dir
        self.performance_threshold = performance_threshold
        self.drift_severity_threshold = drift_severity_threshold
        self.min_days = min_days_between_optimizations

        # Initialize monitors
        self.perf_monitor = PerformanceMonitor(data_dir=data_dir)
        self.drift_detector = DataDriftDetector(
            baseline_window=90, test_window=30, alpha=0.05
        )

        # Optimization history file
        self.optimization_history_path = (
            data_dir / "optimization_history" / "history.parquet"
        )

        logger.info(
            f"OptimizationTriggerManager initialized: "
            f"perf_threshold={performance_threshold}%, "
            f"min_days={min_days_between_optimizations}"
        )

    def should_optimize(
        self, horizon: str, series: pd.Series
    ) -> TriggerReport:
        """
        Check all triggers and determine if optimization should run.

        Args:
            horizon: Forecast horizon to check (e.g., "7d").
            series: Historical USD/CLP series for drift detection.

        Returns:
            TriggerReport with decision and reasons.

        Example:
            >>> report = manager.should_optimize("7d", usdclp_series)
            >>> print(f"Should optimize: {report.should_optimize}")
            >>> print(f"Reasons: {report.reasons}")
        """
        logger.info(f"Checking optimization triggers for horizon: {horizon}")

        reasons = []
        performance_degradation = None
        drift_severity = None
        days_since_last = None

        # Trigger 1: Performance Degradation
        perf_triggered, perf_reason, perf_deg = self._check_performance_trigger(
            horizon
        )
        if perf_triggered:
            reasons.append(perf_reason)
            performance_degradation = perf_deg

        # Trigger 2: Data Drift
        drift_triggered, drift_reason, drift_sev = self._check_drift_trigger(series)
        if drift_triggered:
            reasons.append(drift_reason)
            drift_severity = drift_sev

        # Trigger 3: Time-Based Fallback
        time_triggered, time_reason, days_since = self._check_time_trigger(horizon)
        if time_triggered:
            reasons.append(time_reason)
            days_since_last = days_since

        # Optimize if ANY trigger fires
        should_optimize = len(reasons) > 0

        report = TriggerReport(
            horizon=horizon,
            should_optimize=should_optimize,
            reasons=reasons,
            performance_degradation=performance_degradation,
            drift_severity=drift_severity,
            days_since_last_optimization=days_since_last,
        )

        if should_optimize:
            logger.warning(
                f"Optimization TRIGGERED for {horizon}: {', '.join(reasons)}"
            )
        else:
            logger.info(f"No optimization needed for {horizon}")

        return report

    def _check_performance_trigger(
        self, horizon: str
    ) -> tuple[bool, str, Optional[float]]:
        """
        Check if performance has degraded beyond threshold.

        Returns:
            (triggered: bool, reason: str, degradation_pct: float)
        """
        try:
            report = self.perf_monitor.check_performance(horizon)

            if not report.degradation_detected:
                return False, "", None

            # Check RMSE degradation
            rmse_deg = report.degradation_pct.get("rmse", 0)

            if rmse_deg >= self.performance_threshold:
                reason = (
                    f"Performance degraded: RMSE +{rmse_deg:.1f}% "
                    f"(threshold: {self.performance_threshold}%)"
                )
                return True, reason, rmse_deg

            return False, "", None

        except Exception as e:
            logger.warning(f"Performance check failed: {e}")
            return False, "", None

    def _check_drift_trigger(
        self, series: pd.Series
    ) -> tuple[bool, str, Optional[str]]:
        """
        Check if data drift has been detected.

        Returns:
            (triggered: bool, reason: str, severity: str)
        """
        try:
            drift_report = self.drift_detector.generate_drift_report(series)

            if not drift_report.drift_detected:
                return False, "", None

            # Check severity threshold
            severity_levels = {
                DriftSeverity.NONE: 0,
                DriftSeverity.LOW: 1,
                DriftSeverity.MEDIUM: 2,
                DriftSeverity.HIGH: 3,
            }

            current_severity = severity_levels.get(drift_report.severity, 0)
            threshold_severity = severity_levels.get(
                self.drift_severity_threshold, 2
            )

            if current_severity >= threshold_severity:
                reason = (
                    f"Data drift detected: {drift_report.severity.value.upper()} "
                    f"(p={drift_report.p_value:.4f})"
                )
                return True, reason, drift_report.severity.value

            return False, "", None

        except Exception as e:
            logger.warning(f"Drift check failed: {e}")
            return False, "", None

    def _check_time_trigger(
        self, horizon: str
    ) -> tuple[bool, str, Optional[int]]:
        """
        Check if minimum time has passed since last optimization.

        Returns:
            (triggered: bool, reason: str, days_since: int)
        """
        try:
            last_optimization_date = self._get_last_optimization_date(horizon)

            if last_optimization_date is None:
                reason = "Never optimized - initial optimization recommended"
                return True, reason, None

            days_since = (datetime.now() - last_optimization_date).days

            if days_since >= self.min_days:
                reason = (
                    f"Time-based trigger: {days_since} days since last optimization "
                    f"(threshold: {self.min_days} days)"
                )
                return True, reason, days_since

            return False, "", days_since

        except Exception as e:
            logger.warning(f"Time check failed: {e}")
            return False, "", None

    def _get_last_optimization_date(self, horizon: str) -> Optional[datetime]:
        """
        Get the date of the last optimization for a given horizon.

        Returns:
            datetime of last optimization, or None if never optimized.
        """
        if not self.optimization_history_path.exists():
            return None

        try:
            history = pd.read_parquet(self.optimization_history_path)

            # Filter by horizon
            horizon_history = history[history["horizon"] == horizon]

            if len(horizon_history) == 0:
                return None

            # Get most recent optimization date
            last_date = horizon_history["optimization_date"].max()

            return pd.to_datetime(last_date).to_pydatetime()

        except Exception as e:
            logger.warning(f"Failed to read optimization history: {e}")
            return None

    def record_optimization(
        self,
        horizon: str,
        trigger_report: TriggerReport,
        success: bool,
    ) -> None:
        """
        Record an optimization attempt in history.

        Args:
            horizon: Forecast horizon optimized.
            trigger_report: The trigger report that initiated optimization.
            success: Whether optimization succeeded.

        Example:
            >>> manager.record_optimization("7d", trigger_report, success=True)
        """
        # Ensure directory exists
        self.optimization_history_path.parent.mkdir(parents=True, exist_ok=True)

        # Create record
        record = {
            "horizon": horizon,
            "optimization_date": datetime.now(),
            "triggered_by": ", ".join(trigger_report.reasons),
            "performance_degradation_pct": trigger_report.performance_degradation,
            "drift_severity": trigger_report.drift_severity,
            "days_since_last": trigger_report.days_since_last_optimization,
            "success": success,
        }

        # Append to history
        if self.optimization_history_path.exists():
            history = pd.read_parquet(self.optimization_history_path)
            history = pd.concat([history, pd.DataFrame([record])], ignore_index=True)
        else:
            history = pd.DataFrame([record])

        # Save
        history.to_parquet(self.optimization_history_path, index=False)

        logger.info(
            f"Optimization recorded: {horizon}, success={success}, "
            f"triggers={trigger_report.reasons}"
        )


__all__ = ["OptimizationTriggerManager", "TriggerReport"]
