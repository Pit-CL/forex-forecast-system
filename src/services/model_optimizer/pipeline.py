"""
Model Optimization Pipeline.

End-to-end pipeline that:
1. Checks triggers
2. Optimizes hyperparameters
3. Validates new config
4. Deploys if approved
5. Monitors post-deployment

Example:
    >>> pipeline = ModelOptimizationPipeline(horizon="7d")
    >>> result = pipeline.run()
    >>> if result.success:
    ...     print(f"Optimization successful: {result.summary}")
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger

from forex_core.data.loader import load_usdclp_series
from forex_core.optimization.chronos_optimizer import ChronosHyperparameterOptimizer
from forex_core.optimization.deployment import ConfigDeploymentManager
from forex_core.optimization.triggers import OptimizationTriggerManager
from forex_core.optimization.validator import ConfigValidator


@dataclass
class OptimizationResult:
    """
    Result of optimization pipeline execution.

    Attributes:
        horizon: Forecast horizon optimized.
        success: Whether optimization completed successfully.
        triggered: Whether optimization was triggered (may skip if no trigger).
        optimized: Whether optimization was performed.
        validated: Whether validation passed.
        deployed: Whether config was deployed.
        summary: Human-readable summary.
        trigger_report: Report from trigger check.
        optimized_config: Optimized config (if generated).
        validation_report: Validation report (if validated).
        deployment_report: Deployment report (if deployed).
        error_message: Error message if failed.
        timestamp: When pipeline executed.
    """

    horizon: str
    success: bool
    triggered: bool
    optimized: bool
    validated: bool
    deployed: bool
    summary: str
    trigger_report: Optional[object] = None
    optimized_config: Optional[object] = None
    validation_report: Optional[object] = None
    deployment_report: Optional[object] = None
    error_message: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ModelOptimizationPipeline:
    """
    End-to-end model optimization pipeline.

    Orchestrates the complete optimization workflow:
    - Trigger detection
    - Hyperparameter optimization
    - Configuration validation
    - Safe deployment
    - Post-deployment monitoring

    Args:
        horizon: Forecast horizon to optimize (e.g., "7d").
        data_dir: Directory containing data and configs.
        config_dir: Directory for configuration files.
        dry_run: If True, skip deployment (validation only).

    Example:
        >>> # Optimize single horizon
        >>> pipeline = ModelOptimizationPipeline(horizon="7d")
        >>> result = pipeline.run()
        >>>
        >>> print(f"Success: {result.success}")
        >>> print(f"Summary: {result.summary}")
    """

    def __init__(
        self,
        horizon: str,
        data_dir: Path = Path("data"),
        config_dir: Path = Path("configs"),
        dry_run: bool = False,
    ):
        self.horizon = horizon
        self.data_dir = Path(data_dir)
        self.config_dir = Path(config_dir)
        self.dry_run = dry_run

        # Initialize components
        self.trigger_manager = OptimizationTriggerManager(data_dir=data_dir)
        self.optimizer = ChronosHyperparameterOptimizer(
            horizon=horizon,
            validation_window=30,
            search_method="grid",
        )
        self.validator = ConfigValidator(
            data_dir=data_dir,
            validation_window=30,
        )
        self.deployment_manager = ConfigDeploymentManager(
            config_dir=config_dir,
            enable_git_versioning=True,
            enable_notifications=True,
        )

        logger.info(
            f"ModelOptimizationPipeline initialized: "
            f"horizon={horizon}, dry_run={dry_run}"
        )

    def run(self) -> OptimizationResult:
        """
        Run complete optimization pipeline.

        Returns:
            OptimizationResult with complete execution details.

        Example:
            >>> result = pipeline.run()
            >>> if result.deployed:
            ...     print("New config deployed successfully!")
        """
        logger.info(f"=" * 80)
        logger.info(f"Starting optimization pipeline for {self.horizon}")
        logger.info(f"=" * 80)

        try:
            # Step 1: Load data
            logger.info("Step 1: Loading historical data...")
            series = self._load_data()

            # Step 2: Check triggers
            logger.info("Step 2: Checking optimization triggers...")
            trigger_report = self.trigger_manager.should_optimize(
                self.horizon, series
            )

            if not trigger_report.should_optimize:
                logger.info(
                    f"No optimization needed for {self.horizon} - "
                    f"all triggers negative"
                )
                return OptimizationResult(
                    horizon=self.horizon,
                    success=True,
                    triggered=False,
                    optimized=False,
                    validated=False,
                    deployed=False,
                    summary="No optimization needed - all triggers negative",
                    trigger_report=trigger_report,
                )

            logger.warning(
                f"Optimization TRIGGERED: {', '.join(trigger_report.reasons)}"
            )

            # Step 3: Optimize hyperparameters
            logger.info("Step 3: Optimizing hyperparameters...")
            optimized_config = self.optimizer.optimize(series)

            logger.info(
                f"Optimization complete: "
                f"RMSE={optimized_config.validation_rmse:.2f}, "
                f"context={optimized_config.context_length}d, "
                f"samples={optimized_config.num_samples}"
            )

            # Step 4: Validate new config
            logger.info("Step 4: Validating new configuration...")
            current_config = self.deployment_manager.get_current_config(
                self.horizon
            )
            validation_report = self.validator.validate(
                new_config=optimized_config,
                current_config=current_config,
                horizon=self.horizon,
                series=series,
            )

            if not validation_report.approved:
                logger.warning(
                    f"Validation FAILED for {self.horizon}: "
                    f"{', '.join(validation_report.approval_reasons)}"
                )

                # Record failed optimization
                self.trigger_manager.record_optimization(
                    self.horizon, trigger_report, success=False
                )

                return OptimizationResult(
                    horizon=self.horizon,
                    success=True,  # Pipeline succeeded, validation just rejected
                    triggered=True,
                    optimized=True,
                    validated=False,
                    deployed=False,
                    summary=f"Validation rejected: {', '.join(validation_report.approval_reasons)}",
                    trigger_report=trigger_report,
                    optimized_config=optimized_config,
                    validation_report=validation_report,
                )

            logger.info(
                f"Validation PASSED for {self.horizon}: "
                f"{', '.join(validation_report.approval_reasons)}"
            )

            # Step 5: Deploy (unless dry run)
            if self.dry_run:
                logger.info("DRY RUN mode - skipping deployment")
                return OptimizationResult(
                    horizon=self.horizon,
                    success=True,
                    triggered=True,
                    optimized=True,
                    validated=True,
                    deployed=False,
                    summary="Dry run - validation passed, deployment skipped",
                    trigger_report=trigger_report,
                    optimized_config=optimized_config,
                    validation_report=validation_report,
                )

            logger.info("Step 5: Deploying new configuration...")
            deployment_report = self.deployment_manager.deploy(
                optimized_config, self.horizon
            )

            if not deployment_report.success:
                logger.error(
                    f"Deployment FAILED for {self.horizon}: "
                    f"{deployment_report.error_message}"
                )

                # Record failed deployment
                self.trigger_manager.record_optimization(
                    self.horizon, trigger_report, success=False
                )

                return OptimizationResult(
                    horizon=self.horizon,
                    success=False,
                    triggered=True,
                    optimized=True,
                    validated=True,
                    deployed=False,
                    summary=f"Deployment failed: {deployment_report.error_message}",
                    trigger_report=trigger_report,
                    optimized_config=optimized_config,
                    validation_report=validation_report,
                    deployment_report=deployment_report,
                    error_message=deployment_report.error_message,
                )

            logger.info(
                f"Deployment SUCCESSFUL for {self.horizon}: "
                f"backup={deployment_report.backup_path}"
            )

            # Record successful optimization
            self.trigger_manager.record_optimization(
                self.horizon, trigger_report, success=True
            )

            # Success!
            summary = (
                f"Optimization complete: "
                f"RMSE improved {validation_report.metrics.rmse_improvement:.1f}%, "
                f"config deployed successfully"
            )

            logger.info(f"=" * 80)
            logger.info(f"Pipeline COMPLETED successfully for {self.horizon}")
            logger.info(f"Summary: {summary}")
            logger.info(f"=" * 80)

            return OptimizationResult(
                horizon=self.horizon,
                success=True,
                triggered=True,
                optimized=True,
                validated=True,
                deployed=True,
                summary=summary,
                trigger_report=trigger_report,
                optimized_config=optimized_config,
                validation_report=validation_report,
                deployment_report=deployment_report,
            )

        except Exception as e:
            logger.exception(f"Pipeline failed for {self.horizon}: {e}")

            return OptimizationResult(
                horizon=self.horizon,
                success=False,
                triggered=False,
                optimized=False,
                validated=False,
                deployed=False,
                summary=f"Pipeline error: {str(e)}",
                error_message=str(e),
            )

    def _load_data(self) -> pd.Series:
        """
        Load USD/CLP historical series.

        Returns:
            Series indexed by date with USD/CLP prices.
        """
        # Use existing data loader
        series = load_usdclp_series(self.data_dir / "warehouse")

        if len(series) < 365:
            logger.warning(
                f"Short series: {len(series)} days (recommended: >=365)"
            )

        return series


def run_optimization_for_all_horizons(
    data_dir: Path = Path("data"),
    config_dir: Path = Path("configs"),
    dry_run: bool = False,
) -> dict[str, OptimizationResult]:
    """
    Run optimization pipeline for all horizons.

    Args:
        data_dir: Directory containing data.
        config_dir: Directory for configs.
        dry_run: If True, skip deployment.

    Returns:
        Dictionary mapping horizon to OptimizationResult.

    Example:
        >>> results = run_optimization_for_all_horizons()
        >>> for horizon, result in results.items():
        ...     print(f"{horizon}: {result.summary}")
    """
    horizons = ["7d", "15d", "30d", "90d"]
    results = {}

    logger.info(f"Running optimization for {len(horizons)} horizons")

    for horizon in horizons:
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing horizon: {horizon}")
        logger.info(f"{'='*80}\n")

        try:
            pipeline = ModelOptimizationPipeline(
                horizon=horizon,
                data_dir=data_dir,
                config_dir=config_dir,
                dry_run=dry_run,
            )

            result = pipeline.run()
            results[horizon] = result

        except Exception as e:
            logger.exception(f"Failed to process {horizon}: {e}")
            results[horizon] = OptimizationResult(
                horizon=horizon,
                success=False,
                triggered=False,
                optimized=False,
                validated=False,
                deployed=False,
                summary=f"Pipeline error: {str(e)}",
                error_message=str(e),
            )

    # Summary report
    logger.info(f"\n{'='*80}")
    logger.info("OPTIMIZATION SUMMARY")
    logger.info(f"{'='*80}")

    for horizon, result in results.items():
        status = "✅ SUCCESS" if result.success else "❌ FAILED"
        logger.info(f"{horizon}: {status} - {result.summary}")

    deployed_count = sum(1 for r in results.values() if r.deployed)
    logger.info(f"\nDeployed: {deployed_count}/{len(horizons)} horizons")

    return results


__all__ = [
    "ModelOptimizationPipeline",
    "OptimizationResult",
    "run_optimization_for_all_horizons",
]
