"""
Configuration Validator for Model Optimization.

Validates new model configurations against current baseline to ensure
that optimization actually improves performance before deployment.

Example:
    >>> validator = ConfigValidator(data_dir=Path("data"))
    >>> report = validator.validate(new_config, current_config, "7d", series)
    >>> if report.approved:
    ...     print("Config approved for deployment!")
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

from ..forecasting.chronos_model import forecast_chronos
from ..forecasting.metrics import calculate_rmse, calculate_mape, calculate_mae
from .chronos_optimizer import OptimizedConfig


@dataclass
class ValidationMetrics:
    """
    Metrics comparing new config vs current config.

    Attributes:
        rmse_improvement: % improvement in RMSE (negative = worse).
        mape_improvement: % improvement in MAPE.
        mae_improvement: % improvement in MAE.
        ci95_coverage_new: CI95 coverage for new config (should be ~0.95).
        ci95_coverage_current: CI95 coverage for current config.
        bias_new: Mean bias (error) for new config.
        bias_current: Mean bias for current config.
        inference_time_new: Inference time in seconds.
        inference_time_current: Inference time in seconds.
        stability_score: Ratio of std devs (new/current).
    """

    rmse_improvement: float
    mape_improvement: float
    mae_improvement: float
    ci95_coverage_new: float
    ci95_coverage_current: float
    bias_new: float
    bias_current: float
    inference_time_new: float
    inference_time_current: float
    stability_score: float


@dataclass
class ValidationReport:
    """
    Complete validation report with approval decision.

    Attributes:
        horizon: Forecast horizon being validated.
        approved: Whether new config is approved for deployment.
        metrics: Detailed comparison metrics.
        new_config: The new configuration being validated.
        current_config: The current baseline configuration.
        approval_reasons: List of reasons for approval/rejection.
        timestamp: When validation was performed.
    """

    horizon: str
    approved: bool
    metrics: ValidationMetrics
    new_config: OptimizedConfig
    current_config: Optional[OptimizedConfig]
    approval_reasons: list[str]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ConfigValidator:
    """
    Validates new model configurations against current baseline.

    Uses walk-forward validation to compare performance of new vs
    current config on recent historical data.

    Approval criteria:
    1. RMSE improves >= 5% OR MAPE improves >= 3%
    2. Std dev doesn't increase > 10%
    3. Inference time doesn't increase > 50%
    4. CI95 coverage >= 0.90
    5. Absolute bias < threshold

    Args:
        data_dir: Directory containing historical data.
        validation_window: Days of data for validation (default: 30).
        rmse_improvement_threshold: Min % RMSE improvement (default: 5.0).
        mape_improvement_threshold: Min % MAPE improvement (default: 3.0).
        max_stability_increase: Max % increase in std dev (default: 10.0).
        max_inference_time_increase: Max % increase in time (default: 50.0).

    Example:
        >>> validator = ConfigValidator(data_dir=Path("data"))
        >>> report = validator.validate(new_config, current_config, "7d", series)
        >>>
        >>> if report.approved:
        ...     print("Approved:", report.approval_reasons)
        ... else:
        ...     print("Rejected:", report.approval_reasons)
    """

    def __init__(
        self,
        data_dir: Path,
        validation_window: int = 30,
        rmse_improvement_threshold: float = 5.0,
        mape_improvement_threshold: float = 3.0,
        max_stability_increase: float = 10.0,
        max_inference_time_increase: float = 50.0,
        min_ci95_coverage: float = 0.90,
        max_bias: float = 5.0,
    ):
        self.data_dir = data_dir
        self.validation_window = validation_window
        self.rmse_improvement_threshold = rmse_improvement_threshold
        self.mape_improvement_threshold = mape_improvement_threshold
        self.max_stability_increase = max_stability_increase
        self.max_inference_time_increase = max_inference_time_increase
        self.min_ci95_coverage = min_ci95_coverage
        self.max_bias = max_bias

        logger.info(
            f"ConfigValidator initialized: "
            f"validation_window={validation_window}d, "
            f"RMSE threshold={rmse_improvement_threshold}%, "
            f"MAPE threshold={mape_improvement_threshold}%"
        )

    def validate(
        self,
        new_config: OptimizedConfig,
        current_config: Optional[OptimizedConfig],
        horizon: str,
        series: pd.Series,
    ) -> ValidationReport:
        """
        Validate new config against current config.

        Args:
            new_config: New optimized configuration to validate.
            current_config: Current configuration (baseline). If None,
                           auto-approve (initial deployment).
            horizon: Forecast horizon.
            series: Historical USD/CLP series.

        Returns:
            ValidationReport with approval decision and detailed metrics.

        Example:
            >>> report = validator.validate(new_config, current_config, "7d", series)
            >>> print(f"Approved: {report.approved}")
            >>> print(f"RMSE improvement: {report.metrics.rmse_improvement:.1f}%")
        """
        logger.info(f"Validating new config for {horizon}")

        # If no current config, auto-approve (initial deployment)
        if current_config is None:
            logger.info("No current config - auto-approving initial deployment")
            return self._create_auto_approve_report(new_config, horizon)

        # Run validation comparison
        metrics = self._compare_configs(
            new_config=new_config,
            current_config=current_config,
            horizon=horizon,
            series=series,
        )

        # Decide approval
        approved, reasons = self._decide_approval(metrics)

        report = ValidationReport(
            horizon=horizon,
            approved=approved,
            metrics=metrics,
            new_config=new_config,
            current_config=current_config,
            approval_reasons=reasons,
        )

        if approved:
            logger.info(f"Config APPROVED for {horizon}: {', '.join(reasons)}")
        else:
            logger.warning(f"Config REJECTED for {horizon}: {', '.join(reasons)}")

        return report

    def _compare_configs(
        self,
        new_config: OptimizedConfig,
        current_config: OptimizedConfig,
        horizon: str,
        series: pd.Series,
    ) -> ValidationMetrics:
        """
        Compare performance of new vs current config.

        Uses backtesting on recent validation window.
        """
        horizon_days = self._parse_horizon(horizon)

        # Split data
        split_point = len(series) - self.validation_window
        train_series = series.iloc[:split_point]
        actual_values = series.iloc[
            split_point : split_point + horizon_days
        ].values

        logger.debug(
            f"Validation split: train={len(train_series)}, "
            f"test={len(actual_values)} days"
        )

        # Forecast with NEW config
        logger.debug("Generating forecast with NEW config...")
        start_new = datetime.now()
        forecast_new = forecast_chronos(
            series=train_series,
            steps=horizon_days,
            context_length=new_config.context_length,
            num_samples=new_config.num_samples,
            temperature=new_config.temperature,
            validate=False,
        )
        inference_time_new = (datetime.now() - start_new).total_seconds()

        # Forecast with CURRENT config
        logger.debug("Generating forecast with CURRENT config...")
        start_current = datetime.now()
        forecast_current = forecast_chronos(
            series=train_series,
            steps=horizon_days,
            context_length=current_config.context_length,
            num_samples=current_config.num_samples,
            temperature=current_config.temperature,
            validate=False,
        )
        inference_time_current = (datetime.now() - start_current).total_seconds()

        # Extract predictions and CI
        pred_new = np.array([p.mean for p in forecast_new.series])
        ci95_low_new = np.array([p.ci95_low for p in forecast_new.series])
        ci95_high_new = np.array([p.ci95_high for p in forecast_new.series])

        pred_current = np.array([p.mean for p in forecast_current.series])
        ci95_low_current = np.array([p.ci95_low for p in forecast_current.series])
        ci95_high_current = np.array([p.ci95_high for p in forecast_current.series])

        # Align lengths
        min_len = min(len(pred_new), len(pred_current), len(actual_values))
        pred_new = pred_new[:min_len]
        pred_current = pred_current[:min_len]
        actual_values = actual_values[:min_len]
        ci95_low_new = ci95_low_new[:min_len]
        ci95_high_new = ci95_high_new[:min_len]
        ci95_low_current = ci95_low_current[:min_len]
        ci95_high_current = ci95_high_current[:min_len]

        # Calculate metrics for NEW
        rmse_new = calculate_rmse(actual_values, pred_new)
        mape_new = calculate_mape(actual_values, pred_new)
        mae_new = calculate_mae(actual_values, pred_new)
        errors_new = actual_values - pred_new
        bias_new = np.mean(errors_new)
        std_new = np.std(errors_new)
        ci95_coverage_new = np.mean(
            (actual_values >= ci95_low_new) & (actual_values <= ci95_high_new)
        )

        # Calculate metrics for CURRENT
        rmse_current = calculate_rmse(actual_values, pred_current)
        mape_current = calculate_mape(actual_values, pred_current)
        mae_current = calculate_mae(actual_values, pred_current)
        errors_current = actual_values - pred_current
        bias_current = np.mean(errors_current)
        std_current = np.std(errors_current)
        ci95_coverage_current = np.mean(
            (actual_values >= ci95_low_current) & (actual_values <= ci95_high_current)
        )

        # Calculate improvements (negative = worse)
        rmse_improvement = (
            ((rmse_current - rmse_new) / rmse_current) * 100
            if rmse_current > 0
            else 0
        )
        mape_improvement = (
            ((mape_current - mape_new) / mape_current) * 100
            if mape_current > 0
            else 0
        )
        mae_improvement = (
            ((mae_current - mae_new) / mae_current) * 100
            if mae_current > 0
            else 0
        )

        # Stability score (ratio of std devs)
        stability_score = std_new / std_current if std_current > 0 else 1.0

        logger.debug(
            f"Validation metrics: RMSE {rmse_current:.2f} -> {rmse_new:.2f} "
            f"({rmse_improvement:+.1f}%), "
            f"MAPE {mape_current:.2f} -> {mape_new:.2f} "
            f"({mape_improvement:+.1f}%)"
        )

        return ValidationMetrics(
            rmse_improvement=rmse_improvement,
            mape_improvement=mape_improvement,
            mae_improvement=mae_improvement,
            ci95_coverage_new=ci95_coverage_new,
            ci95_coverage_current=ci95_coverage_current,
            bias_new=bias_new,
            bias_current=bias_current,
            inference_time_new=inference_time_new,
            inference_time_current=inference_time_current,
            stability_score=stability_score,
        )

    def _decide_approval(
        self, metrics: ValidationMetrics
    ) -> tuple[bool, list[str]]:
        """
        Decide whether to approve new config based on metrics.

        Returns:
            (approved: bool, reasons: list[str])
        """
        reasons = []
        passes = []

        # Criterion 1: Performance improvement
        improved_rmse = metrics.rmse_improvement >= self.rmse_improvement_threshold
        improved_mape = metrics.mape_improvement >= self.mape_improvement_threshold

        if improved_rmse or improved_mape:
            passes.append(True)
            if improved_rmse:
                reasons.append(
                    f"RMSE improved {metrics.rmse_improvement:.1f}% "
                    f"(threshold: {self.rmse_improvement_threshold}%)"
                )
            if improved_mape:
                reasons.append(
                    f"MAPE improved {metrics.mape_improvement:.1f}% "
                    f"(threshold: {self.mape_improvement_threshold}%)"
                )
        else:
            passes.append(False)
            reasons.append(
                f"Insufficient improvement: RMSE {metrics.rmse_improvement:+.1f}%, "
                f"MAPE {metrics.mape_improvement:+.1f}%"
            )

        # Criterion 2: Stability (std dev)
        stability_pct_increase = (metrics.stability_score - 1.0) * 100
        stable = stability_pct_increase <= self.max_stability_increase

        if stable:
            passes.append(True)
            reasons.append(
                f"Stability OK: std dev ratio {metrics.stability_score:.2f}"
            )
        else:
            passes.append(False)
            reasons.append(
                f"Instability detected: std dev increased {stability_pct_increase:.1f}% "
                f"(max: {self.max_stability_increase}%)"
            )

        # Criterion 3: Inference time
        time_increase_pct = (
            (
                (metrics.inference_time_new - metrics.inference_time_current)
                / metrics.inference_time_current
            )
            * 100
            if metrics.inference_time_current > 0
            else 0
        )
        fast_enough = time_increase_pct <= self.max_inference_time_increase

        if fast_enough:
            passes.append(True)
            reasons.append(f"Inference time acceptable: {time_increase_pct:+.1f}%")
        else:
            passes.append(False)
            reasons.append(
                f"Inference too slow: +{time_increase_pct:.1f}% "
                f"(max: {self.max_inference_time_increase}%)"
            )

        # Criterion 4: CI95 coverage
        good_coverage = metrics.ci95_coverage_new >= self.min_ci95_coverage

        if good_coverage:
            passes.append(True)
            reasons.append(
                f"CI95 coverage good: {metrics.ci95_coverage_new:.2%} "
                f"(min: {self.min_ci95_coverage:.2%})"
            )
        else:
            passes.append(False)
            reasons.append(
                f"CI95 coverage low: {metrics.ci95_coverage_new:.2%} "
                f"(min: {self.min_ci95_coverage:.2%})"
            )

        # Criterion 5: Bias
        low_bias = abs(metrics.bias_new) < self.max_bias

        if low_bias:
            passes.append(True)
            reasons.append(f"Bias acceptable: {metrics.bias_new:+.2f} CLP")
        else:
            passes.append(False)
            reasons.append(
                f"Bias too high: {metrics.bias_new:+.2f} CLP "
                f"(max: {self.max_bias} CLP)"
            )

        # Approve if ALL criteria pass
        approved = all(passes)

        return approved, reasons

    def _create_auto_approve_report(
        self, new_config: OptimizedConfig, horizon: str
    ) -> ValidationReport:
        """Create auto-approval report for initial deployment."""
        # Dummy metrics (no comparison available)
        metrics = ValidationMetrics(
            rmse_improvement=0.0,
            mape_improvement=0.0,
            mae_improvement=0.0,
            ci95_coverage_new=0.0,
            ci95_coverage_current=0.0,
            bias_new=0.0,
            bias_current=0.0,
            inference_time_new=0.0,
            inference_time_current=0.0,
            stability_score=1.0,
        )

        return ValidationReport(
            horizon=horizon,
            approved=True,
            metrics=metrics,
            new_config=new_config,
            current_config=None,
            approval_reasons=["Initial deployment - no baseline for comparison"],
        )

    def _parse_horizon(self, horizon: str) -> int:
        """Parse horizon string to days."""
        horizon_map = {"7d": 7, "15d": 15, "30d": 30, "90d": 90}
        return horizon_map.get(horizon, 7)


__all__ = ["ConfigValidator", "ValidationReport", "ValidationMetrics"]
