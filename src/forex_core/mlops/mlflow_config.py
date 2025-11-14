"""
MLflow configuration and initialization.

Provides centralized MLflow setup for all forecasting services with:
- Consistent experiment naming
- Automatic directory creation
- Backend store (SQLite) configuration
- Artifact store (filesystem) configuration
- Lightweight VPS-optimized setup (no separate tracking server needed)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Any

from loguru import logger

# MLflow is optional dependency - gracefully degrade if not installed
try:
    import mlflow
    import mlflow.pytorch
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    logger.warning(
        "MLflow not installed. Install with: pip install mlflow>=2.16\n"
        "MLflow tracking will be disabled."
    )


class MLflowConfig:
    """
    MLflow configuration manager for VPS deployment.

    Handles initialization of MLflow tracking with local SQLite backend
    and filesystem artifact storage. Optimized for single-VPS deployment
    with minimal dependencies.

    Architecture:
        - Backend Store: SQLite database (./data/mlflow/mlflow.db)
        - Artifact Store: Local filesystem (./data/mlflow/mlruns/)
        - No separate tracking server needed
        - Optional MLflow UI via Docker Compose

    Example:
        >>> config = MLflowConfig()
        >>> config.setup(experiment_name="forecaster_7d")
        >>> with config.start_run(run_name="forecast_20251113"):
        ...     mlflow.log_param("horizon", "7d")
        ...     mlflow.log_metric("rmse", 12.34)
    """

    def __init__(
        self,
        tracking_uri: Optional[str] = None,
        artifact_location: Optional[str] = None,
    ):
        """
        Initialize MLflow configuration.

        Args:
            tracking_uri: MLflow tracking URI. If None, uses:
                          sqlite:///data/mlflow/mlflow.db
            artifact_location: Artifact storage path. If None, uses:
                              ./data/mlflow/mlruns

        Raises:
            RuntimeError: If MLflow is not installed.

        Example:
            >>> # Use default SQLite + filesystem
            >>> config = MLflowConfig()
            >>>
            >>> # Custom paths
            >>> config = MLflowConfig(
            ...     tracking_uri="sqlite:////app/data/mlflow.db",
            ...     artifact_location="/app/data/artifacts"
            ... )
        """
        if not MLFLOW_AVAILABLE:
            raise RuntimeError(
                "MLflow is not installed. Install with: pip install mlflow>=2.16"
            )

        # Default paths for VPS deployment
        self.base_dir = Path("./data/mlflow")
        self.base_dir.mkdir(parents=True, exist_ok=True)

        if tracking_uri is None:
            db_path = self.base_dir / "mlflow.db"
            self.tracking_uri = f"sqlite:///{db_path.absolute()}"
        else:
            self.tracking_uri = tracking_uri

        if artifact_location is None:
            self.artifact_location = str((self.base_dir / "mlruns").absolute())
        else:
            self.artifact_location = artifact_location

        # Create artifact directory
        Path(self.artifact_location).mkdir(parents=True, exist_ok=True)

        logger.debug(f"MLflow tracking URI: {self.tracking_uri}")
        logger.debug(f"MLflow artifact location: {self.artifact_location}")

    def setup(
        self,
        experiment_name: str,
        *,
        tags: Optional[dict] = None,
    ) -> str:
        """
        Setup MLflow tracking for a forecast service.

        Creates or gets experiment, sets tracking URI, and applies tags.

        Args:
            experiment_name: Name of MLflow experiment (e.g., "forecaster_7d").
            tags: Optional experiment-level tags.

        Returns:
            Experiment ID (str).

        Raises:
            RuntimeError: If experiment setup fails.

        Example:
            >>> config = MLflowConfig()
            >>> exp_id = config.setup(
            ...     experiment_name="forecaster_7d",
            ...     tags={"model_family": "chronos", "horizon": "7d"}
            ... )
            >>> print(f"Experiment ID: {exp_id}")
        """
        # Set tracking URI
        mlflow.set_tracking_uri(self.tracking_uri)
        logger.info(f"MLflow tracking URI: {self.tracking_uri}")

        # Create or get experiment
        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(
                    name=experiment_name,
                    artifact_location=self.artifact_location,
                    tags=tags or {},
                )
                logger.info(f"Created MLflow experiment: {experiment_name} (ID: {experiment_id})")
            else:
                experiment_id = experiment.experiment_id
                logger.info(f"Using existing MLflow experiment: {experiment_name} (ID: {experiment_id})")

            mlflow.set_experiment(experiment_name)
            return experiment_id

        except Exception as e:
            logger.error(f"Failed to setup MLflow experiment {experiment_name}: {e}")
            raise RuntimeError(f"MLflow experiment setup failed: {e}")

    def start_run(
        self,
        run_name: Optional[str] = None,
        tags: Optional[dict] = None,
        description: Optional[str] = None,
    ) -> Any:
        """
        Start a new MLflow run.

        Args:
            run_name: Name for this run (e.g., "forecast_2025-11-13").
            tags: Run-level tags.
            description: Run description.

        Returns:
            mlflow.ActiveRun context manager.

        Example:
            >>> config = MLflowConfig()
            >>> config.setup("forecaster_7d")
            >>> with config.start_run(run_name="forecast_2025-11-13") as run:
            ...     mlflow.log_param("model", "chronos-t5-small")
            ...     mlflow.log_metric("rmse", 12.34)
        """
        return mlflow.start_run(
            run_name=run_name,
            tags=tags,
            description=description,
        )

    def log_forecast_metrics(
        self,
        horizon: str,
        rmse: float,
        mae: float,
        mape: float,
        *,
        directional_accuracy: Optional[float] = None,
        step: Optional[int] = None,
    ) -> None:
        """
        Log standard forecast evaluation metrics.

        Args:
            horizon: Forecast horizon (e.g., "7d", "30d").
            rmse: Root Mean Squared Error.
            mae: Mean Absolute Error.
            mape: Mean Absolute Percentage Error.
            directional_accuracy: Optional directional accuracy (% correct direction).
            step: Optional step number (for backtesting).

        Example:
            >>> config = MLflowConfig()
            >>> config.setup("forecaster_7d")
            >>> with config.start_run():
            ...     config.log_forecast_metrics(
            ...         horizon="7d",
            ...         rmse=12.34,
            ...         mae=10.15,
            ...         mape=1.25,
            ...         directional_accuracy=0.68
            ...     )
        """
        mlflow.log_metric(f"{horizon}_rmse", rmse, step=step)
        mlflow.log_metric(f"{horizon}_mae", mae, step=step)
        mlflow.log_metric(f"{horizon}_mape", mape, step=step)

        if directional_accuracy is not None:
            mlflow.log_metric(f"{horizon}_directional_accuracy", directional_accuracy, step=step)

        logger.debug(
            f"Logged metrics for {horizon}: "
            f"RMSE={rmse:.4f}, MAE={mae:.4f}, MAPE={mape:.2f}%"
        )

    def log_model_artifact(
        self,
        model: Any,
        artifact_path: str,
        *,
        registered_model_name: Optional[str] = None,
    ) -> None:
        """
        Log a model as MLflow artifact.

        Args:
            model: Model object (PyTorch, sklearn, etc.).
            artifact_path: Path within run's artifact directory.
            registered_model_name: Optional name for model registry.

        Raises:
            RuntimeError: If model logging fails.

        Example:
            >>> # Log PyTorch model
            >>> config.log_model_artifact(
            ...     model=chronos_model,
            ...     artifact_path="chronos_model",
            ...     registered_model_name="usdclp_chronos_7d"
            ... )
        """
        try:
            mlflow.pytorch.log_model(
                pytorch_model=model,
                artifact_path=artifact_path,
                registered_model_name=registered_model_name,
            )
            logger.info(f"Logged model artifact: {artifact_path}")

            if registered_model_name:
                logger.info(f"Registered model: {registered_model_name}")

        except Exception as e:
            logger.error(f"Failed to log model artifact: {e}")
            raise RuntimeError(f"Model logging failed: {e}")

    @staticmethod
    def get_best_run(
        experiment_name: str,
        metric: str = "7d_rmse",
        ascending: bool = True,
    ) -> Optional[Any]:
        """
        Get best run from an experiment based on a metric.

        Args:
            experiment_name: Name of experiment to search.
            metric: Metric to optimize (e.g., "7d_rmse").
            ascending: True for minimization (RMSE, MAE), False for maximization.

        Returns:
            Best run or None if no runs found.

        Example:
            >>> best_run = MLflowConfig.get_best_run(
            ...     experiment_name="forecaster_7d",
            ...     metric="7d_rmse",
            ...     ascending=True  # Minimize RMSE
            ... )
            >>> if best_run:
            ...     print(f"Best RMSE: {best_run.data.metrics['7d_rmse']:.4f}")
        """
        if not MLFLOW_AVAILABLE:
            logger.warning("MLflow not available, cannot get best run")
            return None

        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                logger.warning(f"Experiment '{experiment_name}' not found")
                return None

            runs = mlflow.search_runs(
                experiment_ids=[experiment.experiment_id],
                filter_string="",
                order_by=[f"metrics.{metric} {'ASC' if ascending else 'DESC'}"],
                max_results=1,
            )

            if runs.empty:
                logger.warning(f"No runs found in experiment '{experiment_name}'")
                return None

            run_id = runs.iloc[0]["run_id"]
            return mlflow.get_run(run_id)

        except Exception as e:
            logger.error(f"Failed to get best run: {e}")
            return None


def is_mlflow_available() -> bool:
    """
    Check if MLflow is installed and available.

    Returns:
        True if MLflow can be imported, False otherwise.

    Example:
        >>> if is_mlflow_available():
        ...     config = MLflowConfig()
        ...     # ... use MLflow
        >>> else:
        ...     print("MLflow not installed, skipping tracking")
    """
    return MLFLOW_AVAILABLE


__all__ = ["MLflowConfig", "is_mlflow_available"]
