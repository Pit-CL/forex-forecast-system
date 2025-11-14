"""
Model Performance Alert System for USD/CLP Forecasting.

This module monitors model health, performance degradation, training status,
and optimization results. It generates alerts when models need attention,
re-training completes, or performance degrades beyond acceptable thresholds.

Key Features:
- Performance degradation detection (RMSE, MAE, directional accuracy)
- Re-training status monitoring (success/failure tracking)
- Model failure detection (NaN predictions, convergence issues)
- Hyperparameter optimization tracking
- Baseline management per model and horizon
- Configurable alert thresholds

Alert Types:
1. DEGRADATION_WARNING: Model performance declining (>15% RMSE increase)
2. DEGRADATION_CRITICAL: Severe degradation (>30% RMSE increase)
3. RETRAINING_SUCCESS: Model re-trained successfully
4. RETRAINING_FAILURE: Re-training failed
5. TRAINING_FAILURE: Model training convergence issues
6. PREDICTION_FAILURE: NaN or infinite values in predictions
7. DATA_QUALITY_ISSUE: Missing values exceed threshold
8. OPTIMIZATION_COMPLETE: Hyperparameter optimization finished

Example:
    >>> monitor = ModelPerformanceMonitor(baseline_dir=Path("data/baselines"))
    >>>
    >>> # Check for degradation
    >>> current_metrics = ForecastMetrics(rmse=12.5, mae=9.2, mape=1.1,
    ...                                    directional_accuracy=0.58,
    ...                                    train_size=180, test_size=30)
    >>> alerts = monitor.check_degradation(
    ...     model_name="xgboost_7d",
    ...     current_metrics=current_metrics,
    ...     horizon="7d"
    ... )
    >>>
    >>> # Log re-training completion
    >>> monitor.log_retraining_success(
    ...     model_name="xgboost_7d",
    ...     metrics=current_metrics,
    ...     hyperparameters={"learning_rate": 0.1, "max_depth": 5}
    ... )
    >>>
    >>> # Get alert summary for email
    >>> summary = monitor.get_alert_summary()
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from loguru import logger


class AlertType(str, Enum):
    """Type of model performance alert."""

    DEGRADATION_WARNING = "degradation_warning"
    DEGRADATION_CRITICAL = "degradation_critical"
    RETRAINING_SUCCESS = "retraining_success"
    RETRAINING_FAILURE = "retraining_failure"
    TRAINING_FAILURE = "training_failure"
    PREDICTION_FAILURE = "prediction_failure"
    DATA_QUALITY_ISSUE = "data_quality_issue"
    OPTIMIZATION_COMPLETE = "optimization_complete"
    DIRECTIONAL_ACCURACY_LOW = "directional_accuracy_low"
    BASELINE_MISSING = "baseline_missing"


class AlertSeverity(str, Enum):
    """Severity level of alert."""

    INFO = "info"          # Informational, no action needed
    WARNING = "warning"    # Attention recommended
    CRITICAL = "critical"  # Immediate action required


@dataclass
class ModelAlert:
    """
    Alert for model performance issues.

    Attributes:
        alert_type: Type of alert (degradation, failure, etc.).
        severity: Severity level (INFO, WARNING, CRITICAL).
        model_name: Model identifier (e.g., "xgboost_7d", "ensemble_15d").
        horizon: Forecast horizon (7d, 15d, 30d, 90d).
        message: Human-readable alert message.
        current_metrics: Current performance metrics.
        baseline_metrics: Baseline metrics for comparison (if applicable).
        degradation_pct: Percentage degradation vs baseline (if applicable).
        details: Additional details (hyperparameters, error messages, etc.).
        recommendations: List of recommended actions.
        timestamp: When alert was generated.
    """

    alert_type: AlertType
    severity: AlertSeverity
    model_name: str
    horizon: str
    message: str
    current_metrics: Optional[Dict[str, Any]] = None
    baseline_metrics: Optional[Dict[str, Any]] = None
    degradation_pct: Optional[Dict[str, float]] = None
    details: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None
    timestamp: str = ""

    def __post_init__(self):
        """Set timestamp if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    def is_critical(self) -> bool:
        """Check if alert is critical severity."""
        return self.severity == AlertSeverity.CRITICAL

    def is_actionable(self) -> bool:
        """Check if alert requires action (WARNING or CRITICAL)."""
        return self.severity in [AlertSeverity.WARNING, AlertSeverity.CRITICAL]


@dataclass
class BaselineMetrics:
    """
    Baseline performance metrics for comparison.

    Attributes:
        rmse: Baseline RMSE.
        mae: Baseline MAE.
        mape: Baseline MAPE.
        directional_accuracy: Baseline directional accuracy.
        n_samples: Number of samples in baseline.
        established_date: When baseline was established.
        last_updated: When baseline was last updated.
    """

    rmse: float
    mae: float
    mape: float
    directional_accuracy: float
    n_samples: int
    established_date: str
    last_updated: str = ""

    def __post_init__(self):
        """Set last_updated if not provided."""
        if not self.last_updated:
            self.last_updated = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BaselineMetrics:
        """Create from dictionary."""
        return cls(**data)


class ModelPerformanceMonitor:
    """
    Monitor model performance and generate alerts.

    Tracks model health across multiple dimensions:
    - Performance degradation (RMSE, MAE, MAPE, directional accuracy)
    - Re-training status (success/failure)
    - Model failures (NaN predictions, convergence issues)
    - Data quality issues
    - Hyperparameter optimization results

    Args:
        baseline_dir: Directory to store/load baseline metrics.
        degradation_warning_threshold: % increase to trigger warning (default: 15%).
        degradation_critical_threshold: % increase to trigger critical (default: 30%).
        directional_accuracy_threshold: Minimum acceptable accuracy (default: 55%).
        data_quality_threshold: Max % missing values allowed (default: 5%).

    Example:
        >>> monitor = ModelPerformanceMonitor(
        ...     baseline_dir=Path("data/baselines"),
        ...     degradation_warning_threshold=0.15,
        ...     degradation_critical_threshold=0.30
        ... )
        >>>
        >>> alerts = monitor.check_all(
        ...     model_name="xgboost_7d",
        ...     current_metrics=metrics,
        ...     horizon="7d"
        ... )
    """

    def __init__(
        self,
        baseline_dir: Path = Path("data/baselines"),
        degradation_warning_threshold: float = 0.15,
        degradation_critical_threshold: float = 0.30,
        directional_accuracy_threshold: float = 0.55,
        data_quality_threshold: float = 0.05,
    ):
        """Initialize model performance monitor."""
        self.baseline_dir = baseline_dir
        self.degradation_warning_threshold = degradation_warning_threshold
        self.degradation_critical_threshold = degradation_critical_threshold
        self.directional_accuracy_threshold = directional_accuracy_threshold
        self.data_quality_threshold = data_quality_threshold

        # Create baseline directory if it doesn't exist
        self.baseline_dir.mkdir(parents=True, exist_ok=True)

        # Cache for loaded baselines
        self._baseline_cache: Dict[str, BaselineMetrics] = {}

        logger.info(
            f"ModelPerformanceMonitor initialized: "
            f"warning={degradation_warning_threshold:.0%}, "
            f"critical={degradation_critical_threshold:.0%}, "
            f"directional={directional_accuracy_threshold:.0%}"
        )

    def check_degradation(
        self,
        model_name: str,
        current_metrics: Dict[str, Any],
        horizon: str,
    ) -> List[ModelAlert]:
        """
        Check for performance degradation vs baseline.

        Args:
            model_name: Model identifier (e.g., "xgboost_7d").
            current_metrics: Current performance metrics dict with keys:
                             rmse, mae, mape, directional_accuracy.
            horizon: Forecast horizon (7d, 15d, 30d, 90d).

        Returns:
            List of alerts (empty if no degradation detected).

        Example:
            >>> metrics = {"rmse": 12.5, "mae": 9.2, "mape": 1.1,
            ...            "directional_accuracy": 0.58}
            >>> alerts = monitor.check_degradation("xgboost_7d", metrics, "7d")
        """
        alerts = []

        # Load baseline
        baseline = self.load_baseline(model_name, horizon)

        if baseline is None:
            # No baseline exists - warn but don't alert as error
            alerts.append(
                ModelAlert(
                    alert_type=AlertType.BASELINE_MISSING,
                    severity=AlertSeverity.WARNING,
                    model_name=model_name,
                    horizon=horizon,
                    message=f"No baseline exists for {model_name} ({horizon}). "
                            f"This is expected on first run. Baseline will be created.",
                    current_metrics=current_metrics,
                    recommendations=[
                        "Monitor next few forecasts to establish baseline",
                        "After 10+ successful forecasts, save baseline metrics",
                    ],
                )
            )
            return alerts

        # Calculate degradation percentages
        degradation = {}
        for metric in ["rmse", "mae", "mape"]:
            if metric in current_metrics:
                current_val = current_metrics[metric]
                baseline_val = getattr(baseline, metric)

                # Higher is worse for error metrics
                degradation[metric] = (
                    (current_val - baseline_val) / baseline_val
                ) if baseline_val > 0 else 0

        # Check directional accuracy (lower is worse)
        if "directional_accuracy" in current_metrics:
            current_da = current_metrics["directional_accuracy"]
            baseline_da = baseline.directional_accuracy

            # For directional accuracy, negative degradation means improvement
            degradation["directional_accuracy"] = (
                (baseline_da - current_da) / baseline_da
            ) if baseline_da > 0 else 0

        # Find worst degradation
        worst_metric = max(degradation, key=lambda k: degradation[k])
        worst_degradation = degradation[worst_metric]

        # Check for critical degradation
        if worst_degradation >= self.degradation_critical_threshold:
            alerts.append(
                ModelAlert(
                    alert_type=AlertType.DEGRADATION_CRITICAL,
                    severity=AlertSeverity.CRITICAL,
                    model_name=model_name,
                    horizon=horizon,
                    message=f"CRITICAL: {model_name} ({horizon}) - "
                            f"{worst_metric.upper()} degraded by "
                            f"{worst_degradation:.1%} vs baseline",
                    current_metrics=current_metrics,
                    baseline_metrics=baseline.to_dict(),
                    degradation_pct=degradation,
                    recommendations=[
                        "IMMEDIATE: Stop using this model for production forecasts",
                        "Investigate root cause (data drift, regime change, outliers)",
                        "Trigger emergency re-training with recent data",
                        "Consider using ensemble fallback or previous model version",
                        "Review last 7 days of predictions for patterns",
                    ],
                )
            )

        # Check for warning-level degradation
        elif worst_degradation >= self.degradation_warning_threshold:
            alerts.append(
                ModelAlert(
                    alert_type=AlertType.DEGRADATION_WARNING,
                    severity=AlertSeverity.WARNING,
                    model_name=model_name,
                    horizon=horizon,
                    message=f"WARNING: {model_name} ({horizon}) - "
                            f"{worst_metric.upper()} degraded by "
                            f"{worst_degradation:.1%} vs baseline",
                    current_metrics=current_metrics,
                    baseline_metrics=baseline.to_dict(),
                    degradation_pct=degradation,
                    recommendations=[
                        "Monitor closely over next 3-5 forecasts",
                        "Check for data quality issues or missing values",
                        "Review recent prediction errors for systematic bias",
                        f"Consider re-training if degradation persists",
                        "Increase monitoring frequency",
                    ],
                )
            )

        # Check directional accuracy separately (always important)
        if "directional_accuracy" in current_metrics:
            da = current_metrics["directional_accuracy"]
            if da < self.directional_accuracy_threshold:
                alerts.append(
                    ModelAlert(
                        alert_type=AlertType.DIRECTIONAL_ACCURACY_LOW,
                        severity=AlertSeverity.WARNING,
                        model_name=model_name,
                        horizon=horizon,
                        message=f"Directional accuracy below threshold: "
                                f"{da:.1%} < {self.directional_accuracy_threshold:.1%}",
                        current_metrics=current_metrics,
                        baseline_metrics=baseline.to_dict(),
                        recommendations=[
                            "Model not reliably predicting direction",
                            "Review feature importance - trend indicators may be weak",
                            "Check if recent period has high volatility/noise",
                            "Consider adding momentum/trend features",
                        ],
                    )
                )

        logger.info(
            f"Degradation check for {model_name} ({horizon}): "
            f"{len(alerts)} alerts generated"
        )

        return alerts

    def check_retraining_status(
        self,
        model_name: str,
        horizon: str,
        training_result: Dict[str, Any],
    ) -> List[ModelAlert]:
        """
        Check re-training completion status.

        Args:
            model_name: Model identifier.
            horizon: Forecast horizon.
            training_result: Dict with keys:
                - success: bool
                - metrics: Dict (if successful)
                - error: str (if failed)
                - hyperparameters: Dict (if successful)
                - training_time: float (seconds)

        Returns:
            List of alerts (1 success or 1 failure alert).

        Example:
            >>> result = {
            ...     "success": True,
            ...     "metrics": {"rmse": 10.2, "mae": 7.8, "mape": 0.9},
            ...     "hyperparameters": {"learning_rate": 0.1},
            ...     "training_time": 245.3
            ... }
            >>> alerts = monitor.check_retraining_status("xgboost_7d", "7d", result)
        """
        alerts = []

        if training_result.get("success"):
            # Success - check if metrics improved
            metrics = training_result.get("metrics", {})
            baseline = self.load_baseline(model_name, horizon)

            improvement_msg = ""
            if baseline and "rmse" in metrics:
                old_rmse = baseline.rmse
                new_rmse = metrics["rmse"]
                improvement = (old_rmse - new_rmse) / old_rmse * 100

                if improvement > 0:
                    improvement_msg = f" (RMSE improved by {improvement:.1f}%)"
                else:
                    improvement_msg = f" (RMSE degraded by {abs(improvement):.1f}%)"

            alerts.append(
                ModelAlert(
                    alert_type=AlertType.RETRAINING_SUCCESS,
                    severity=AlertSeverity.INFO,
                    model_name=model_name,
                    horizon=horizon,
                    message=f"Re-training completed successfully for {model_name} ({horizon})"
                            f"{improvement_msg}",
                    current_metrics=metrics,
                    baseline_metrics=baseline.to_dict() if baseline else None,
                    details={
                        "hyperparameters": training_result.get("hyperparameters", {}),
                        "training_time_seconds": training_result.get("training_time", 0),
                        "timestamp": datetime.now().isoformat(),
                    },
                    recommendations=[
                        "Update baseline metrics with new performance",
                        "Monitor first 3-5 forecasts with new model",
                        "Compare predictions with previous model version",
                    ],
                )
            )

        else:
            # Failure - critical alert
            error_msg = training_result.get("error", "Unknown error")

            alerts.append(
                ModelAlert(
                    alert_type=AlertType.RETRAINING_FAILURE,
                    severity=AlertSeverity.CRITICAL,
                    model_name=model_name,
                    horizon=horizon,
                    message=f"Re-training FAILED for {model_name} ({horizon}): {error_msg}",
                    details={
                        "error": error_msg,
                        "timestamp": datetime.now().isoformat(),
                    },
                    recommendations=[
                        "CRITICAL: Continue using previous model version",
                        "Investigate failure cause (logs, data quality, convergence)",
                        "Retry re-training with different hyperparameters",
                        "Check for data issues (NaN, outliers, insufficient samples)",
                        "Notify ML team for manual review",
                    ],
                )
            )

        return alerts

    def check_failures(
        self,
        model_name: str,
        horizon: str,
        failure_info: Dict[str, Any],
    ) -> List[ModelAlert]:
        """
        Check for model failures (training, prediction, data quality).

        Args:
            model_name: Model identifier.
            horizon: Forecast horizon.
            failure_info: Dict with keys:
                - failure_type: "training" | "prediction" | "data_quality"
                - details: str or dict
                - affected_dates: List[str] (for prediction failures)
                - missing_pct: float (for data quality)

        Returns:
            List of alerts.

        Example:
            >>> failure = {
            ...     "failure_type": "prediction",
            ...     "details": "NaN values in forecast output",
            ...     "affected_dates": ["2025-01-15", "2025-01-16"]
            ... }
            >>> alerts = monitor.check_failures("xgboost_7d", "7d", failure)
        """
        alerts = []
        failure_type = failure_info.get("failure_type", "unknown")

        if failure_type == "training":
            # Training convergence failure
            alerts.append(
                ModelAlert(
                    alert_type=AlertType.TRAINING_FAILURE,
                    severity=AlertSeverity.CRITICAL,
                    model_name=model_name,
                    horizon=horizon,
                    message=f"Training convergence failure: {model_name} ({horizon})",
                    details=failure_info,
                    recommendations=[
                        "Check data for NaN, infinite, or outlier values",
                        "Review hyperparameters (learning rate may be too high)",
                        "Verify sufficient training samples (need 180+ days)",
                        "Check feature engineering for invalid values",
                        "Review logs for numerical stability issues",
                    ],
                )
            )

        elif failure_type == "prediction":
            # NaN or infinite predictions
            affected = failure_info.get("affected_dates", [])
            alerts.append(
                ModelAlert(
                    alert_type=AlertType.PREDICTION_FAILURE,
                    severity=AlertSeverity.CRITICAL,
                    model_name=model_name,
                    horizon=horizon,
                    message=f"Prediction failure: NaN/infinite values detected "
                            f"({len(affected)} dates affected)",
                    details=failure_info,
                    recommendations=[
                        "DO NOT use affected predictions for reporting/decisions",
                        "Fallback to ensemble or previous model version",
                        "Investigate input data for the affected dates",
                        "Check model loading (corrupted model file?)",
                        "Re-train model if issue persists",
                    ],
                )
            )

        elif failure_type == "data_quality":
            # Missing values exceed threshold
            missing_pct = failure_info.get("missing_pct", 0)
            alerts.append(
                ModelAlert(
                    alert_type=AlertType.DATA_QUALITY_ISSUE,
                    severity=AlertSeverity.WARNING if missing_pct < 0.10 else AlertSeverity.CRITICAL,
                    model_name=model_name,
                    horizon=horizon,
                    message=f"Data quality issue: {missing_pct:.1%} missing values "
                            f"(threshold: {self.data_quality_threshold:.1%})",
                    details=failure_info,
                    recommendations=[
                        "Review data collection process for gaps",
                        "Check data provider APIs for outages",
                        "Implement data imputation strategy if possible",
                        "Consider using backup data sources",
                        f"Missing values acceptable up to {self.data_quality_threshold:.1%}",
                    ],
                )
            )

        return alerts

    def log_optimization_results(
        self,
        model_name: str,
        horizon: str,
        optimization_result: Dict[str, Any],
    ) -> List[ModelAlert]:
        """
        Log hyperparameter optimization results.

        Args:
            model_name: Model identifier.
            horizon: Forecast horizon.
            optimization_result: Dict with keys:
                - n_trials: int
                - best_params: Dict
                - best_rmse: float
                - improvement_vs_default: float (%)
                - optimization_time: float (seconds)

        Returns:
            List of alerts (INFO level).

        Example:
            >>> result = {
            ...     "n_trials": 50,
            ...     "best_params": {"learning_rate": 0.12, "max_depth": 6},
            ...     "best_rmse": 9.8,
            ...     "improvement_vs_default": 12.5,
            ...     "optimization_time": 1834.2
            ... }
            >>> alerts = monitor.log_optimization_results("xgboost_7d", "7d", result)
        """
        alerts = []

        n_trials = optimization_result.get("n_trials", 0)
        improvement = optimization_result.get("improvement_vs_default", 0)
        best_params = optimization_result.get("best_params", {})

        alerts.append(
            ModelAlert(
                alert_type=AlertType.OPTIMIZATION_COMPLETE,
                severity=AlertSeverity.INFO,
                model_name=model_name,
                horizon=horizon,
                message=f"Hyperparameter optimization completed: {n_trials} trials, "
                        f"{improvement:+.1f}% improvement vs defaults",
                details=optimization_result,
                recommendations=[
                    f"Best hyperparameters found: {best_params}",
                    "Model will use optimized hyperparameters for re-training",
                    "Monitor performance with new hyperparameters over next week",
                    "Compare forecast quality before/after optimization",
                ],
            )
        )

        return alerts

    def get_alert_summary(self, alerts: List[ModelAlert]) -> Dict[str, Any]:
        """
        Generate alert summary for email formatting.

        Args:
            alerts: List of alerts to summarize.

        Returns:
            Dict with summary statistics and grouped alerts.

        Example:
            >>> summary = monitor.get_alert_summary(all_alerts)
            >>> print(f"Critical: {summary['counts']['critical']}")
            >>> for alert in summary['critical_alerts']:
            ...     print(alert.message)
        """
        if not alerts:
            return {
                "total": 0,
                "counts": {"critical": 0, "warning": 0, "info": 0},
                "critical_alerts": [],
                "warning_alerts": [],
                "info_alerts": [],
                "requires_action": False,
                "summary_text": "No alerts generated - all models healthy",
            }

        # Group by severity
        critical = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        warning = [a for a in alerts if a.severity == AlertSeverity.WARNING]
        info = [a for a in alerts if a.severity == AlertSeverity.INFO]

        # Generate summary text
        summary_parts = []
        if critical:
            summary_parts.append(f"{len(critical)} CRITICAL")
        if warning:
            summary_parts.append(f"{len(warning)} WARNING")
        if info:
            summary_parts.append(f"{len(info)} INFO")

        summary_text = ", ".join(summary_parts) if summary_parts else "No alerts"

        return {
            "total": len(alerts),
            "counts": {
                "critical": len(critical),
                "warning": len(warning),
                "info": len(info),
            },
            "critical_alerts": critical,
            "warning_alerts": warning,
            "info_alerts": info,
            "requires_action": len(critical) > 0 or len(warning) > 0,
            "summary_text": summary_text,
            "timestamp": datetime.now().isoformat(),
        }

    def save_baseline(
        self,
        model_name: str,
        horizon: str,
        metrics: Dict[str, Any],
        n_samples: int = 0,
    ) -> None:
        """
        Save baseline metrics for future comparison.

        Args:
            model_name: Model identifier.
            horizon: Forecast horizon.
            metrics: Dict with rmse, mae, mape, directional_accuracy.
            n_samples: Number of samples in baseline.

        Example:
            >>> metrics = {"rmse": 10.2, "mae": 7.8, "mape": 0.95,
            ...            "directional_accuracy": 0.62}
            >>> monitor.save_baseline("xgboost_7d", "7d", metrics, n_samples=180)
        """
        baseline = BaselineMetrics(
            rmse=metrics.get("rmse", 0),
            mae=metrics.get("mae", 0),
            mape=metrics.get("mape", 0),
            directional_accuracy=metrics.get("directional_accuracy", 0),
            n_samples=n_samples,
            established_date=datetime.now().isoformat(),
        )

        # Save to file
        baseline_file = self._get_baseline_path(model_name, horizon)
        baseline_file.parent.mkdir(parents=True, exist_ok=True)

        with open(baseline_file, "w") as f:
            json.dump(baseline.to_dict(), f, indent=2)

        # Update cache
        cache_key = f"{model_name}_{horizon}"
        self._baseline_cache[cache_key] = baseline

        logger.info(f"Baseline saved for {model_name} ({horizon}): RMSE={baseline.rmse:.2f}")

    def load_baseline(
        self,
        model_name: str,
        horizon: str,
    ) -> Optional[BaselineMetrics]:
        """
        Load baseline metrics from file.

        Args:
            model_name: Model identifier.
            horizon: Forecast horizon.

        Returns:
            BaselineMetrics object or None if not found.

        Example:
            >>> baseline = monitor.load_baseline("xgboost_7d", "7d")
            >>> if baseline:
            ...     print(f"Baseline RMSE: {baseline.rmse:.2f}")
        """
        cache_key = f"{model_name}_{horizon}"

        # Check cache first
        if cache_key in self._baseline_cache:
            return self._baseline_cache[cache_key]

        # Load from file
        baseline_file = self._get_baseline_path(model_name, horizon)

        if not baseline_file.exists():
            logger.debug(f"No baseline found for {model_name} ({horizon})")
            return None

        try:
            with open(baseline_file, "r") as f:
                data = json.load(f)

            baseline = BaselineMetrics.from_dict(data)

            # Cache it
            self._baseline_cache[cache_key] = baseline

            logger.debug(f"Baseline loaded for {model_name} ({horizon}): RMSE={baseline.rmse:.2f}")
            return baseline

        except Exception as e:
            logger.error(f"Failed to load baseline for {model_name} ({horizon}): {e}")
            return None

    def update_baseline(
        self,
        model_name: str,
        horizon: str,
        new_metrics: Dict[str, Any],
        update_strategy: str = "replace",
    ) -> None:
        """
        Update existing baseline with new metrics.

        Args:
            model_name: Model identifier.
            horizon: Forecast horizon.
            new_metrics: New metrics to incorporate.
            update_strategy: "replace" or "average" (exponential moving average).

        Example:
            >>> # After successful re-training with improvement
            >>> new_metrics = {"rmse": 9.5, "mae": 7.1, "mape": 0.88,
            ...                "directional_accuracy": 0.65}
            >>> monitor.update_baseline("xgboost_7d", "7d", new_metrics,
            ...                         update_strategy="replace")
        """
        if update_strategy == "replace":
            # Simply replace with new metrics
            self.save_baseline(model_name, horizon, new_metrics)

        elif update_strategy == "average":
            # Exponential moving average (alpha=0.3 for new values)
            old_baseline = self.load_baseline(model_name, horizon)

            if old_baseline is None:
                # No baseline exists, save as new
                self.save_baseline(model_name, horizon, new_metrics)
            else:
                # Calculate EMA
                alpha = 0.3
                averaged = {
                    "rmse": alpha * new_metrics.get("rmse", 0) + (1 - alpha) * old_baseline.rmse,
                    "mae": alpha * new_metrics.get("mae", 0) + (1 - alpha) * old_baseline.mae,
                    "mape": alpha * new_metrics.get("mape", 0) + (1 - alpha) * old_baseline.mape,
                    "directional_accuracy": (
                        alpha * new_metrics.get("directional_accuracy", 0)
                        + (1 - alpha) * old_baseline.directional_accuracy
                    ),
                }

                self.save_baseline(model_name, horizon, averaged)
                logger.info(f"Baseline updated (EMA) for {model_name} ({horizon})")

        else:
            raise ValueError(f"Unknown update_strategy: {update_strategy}")

    def _get_baseline_path(self, model_name: str, horizon: str) -> Path:
        """Get path to baseline file for model and horizon."""
        return self.baseline_dir / f"{model_name}_{horizon}_baseline.json"


__all__ = [
    "ModelPerformanceMonitor",
    "ModelAlert",
    "AlertType",
    "AlertSeverity",
    "BaselineMetrics",
]
