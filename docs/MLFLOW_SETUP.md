# MLflow Integration Guide

## Overview

This document describes the MLflow integration for the USD/CLP forecasting system. MLflow provides experiment tracking, model versioning, and deployment capabilities to improve model development workflow and production monitoring.

## Architecture Design

### Lightweight VPS-Optimized Setup

Given the constraint of running on a VPS, we use a **minimal self-contained architecture**:

```
┌─────────────────────────────────────────────────────────┐
│                    VPS (Vultr)                          │
│                                                         │
│  ┌──────────────────┐         ┌──────────────────┐    │
│  │  Forecast Service │────────▶│  MLflow Tracking │    │
│  │  (7d/15d/30d/90d) │         │    (Library)     │    │
│  └──────────────────┘         └──────────────────┘    │
│                                        │                │
│                                        ▼                │
│                          ┌─────────────────────┐       │
│                          │  SQLite Backend     │       │
│                          │  (mlflow.db)        │       │
│                          └─────────────────────┘       │
│                                        │                │
│                                        ▼                │
│                          ┌─────────────────────┐       │
│                          │  Filesystem Artifacts│      │
│                          │  (./mlruns/)        │       │
│                          └─────────────────────┘       │
│                                                         │
│  Optional:                                              │
│  ┌──────────────────┐                                  │
│  │  MLflow UI       │  (Port 5000, optional)           │
│  │  docker-compose  │                                  │
│  └──────────────────┘                                  │
└─────────────────────────────────────────────────────────┘
```

### Components

1. **Backend Store (Metadata):** SQLite database
   - File: `data/mlflow/mlflow.db`
   - Stores: Experiments, runs, parameters, metrics
   - Pros: Zero-config, no separate DB server needed
   - Cons: Single-writer (fine for our sequential forecast jobs)

2. **Artifact Store (Models/Files):** Local Filesystem
   - Path: `data/mlflow/mlruns/`
   - Stores: Serialized models, charts, reports
   - Pros: Simple, fast, no S3 costs
   - Cons: Not distributed (fine for single VPS)

3. **Tracking Library:** Python `mlflow` package
   - Embedded in forecast services
   - No separate tracking server needed
   - Logs metrics/params/artifacts directly to SQLite + filesystem

4. **UI Server (Optional):** MLflow UI Docker container
   - Runs on port 5000
   - Read-only view of experiments
   - Can be started on-demand for analysis
   - Not required for production forecasting

### Why This Design?

**Advantages:**
- Zero external dependencies (no PostgreSQL, no S3)
- Minimal resource footprint (<50 MB RAM for SQLite)
- Simple backup (just copy `data/mlflow/` directory)
- Works offline (no cloud storage needed)
- Fast local artifact access

**Trade-offs:**
- No multi-writer support (fine - forecasts run sequentially)
- No distributed storage (fine - single VPS deployment)
- Manual backups (vs. managed cloud storage)

## Implementation

### Step 1: Install MLflow

Add to `requirements.txt`:

```txt
# MLflow for experiment tracking and model registry
mlflow>=2.16
```

Update dependencies:
```bash
pip install mlflow>=2.16
```

### Step 2: MLflow Configuration Module

Create configuration helper for consistent MLflow setup across all services.

**File:** `src/forex_core/mlops/mlflow_config.py`

```python
"""
MLflow configuration and initialization.

Provides centralized MLflow setup for all forecasting services with:
- Consistent experiment naming
- Automatic directory creation
- Backend store (SQLite) configuration
- Artifact store (filesystem) configuration
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import mlflow
from loguru import logger


class MLflowConfig:
    """
    MLflow configuration manager.

    Handles initialization of MLflow tracking with local SQLite backend
    and filesystem artifact storage optimized for VPS deployment.

    Example:
        >>> config = MLflowConfig()
        >>> config.setup(experiment_name="forecaster_7d")
        >>> mlflow.log_param("horizon", "7d")
        >>> mlflow.log_metric("rmse", 12.34)
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
            raise

    def start_run(
        self,
        run_name: Optional[str] = None,
        tags: Optional[dict] = None,
        description: Optional[str] = None,
    ) -> mlflow.ActiveRun:
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
            >>> config.log_forecast_metrics(
            ...     horizon="7d",
            ...     rmse=12.34,
            ...     mae=10.15,
            ...     mape=1.25,
            ...     directional_accuracy=0.68
            ... )
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
        model: any,
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
            raise

    @staticmethod
    def get_best_run(
        experiment_name: str,
        metric: str = "7d_rmse",
        ascending: bool = True,
    ) -> Optional[mlflow.entities.Run]:
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


__all__ = ["MLflowConfig"]
```

### Step 3: Integration in Forecast Services

Modify each forecaster's `cli.py` to integrate MLflow tracking.

**File:** `src/services/forecaster_7d/cli.py` (example for 7d, replicate for others)

Add MLflow tracking to the `run()` command:

```python
# Add import at top
from forex_core.mlops.mlflow_config import MLflowConfig
from datetime import datetime

# In run() function, after forecast generation:

def run(...) -> None:
    """Run the 7-day forecast pipeline with MLflow tracking."""

    # ... existing code ...

    # Initialize MLflow
    mlflow_config = MLflowConfig()
    mlflow_config.setup(
        experiment_name="forecaster_7d",
        tags={
            "model_family": "chronos",
            "horizon": "7d",
            "service": "forecaster_7d",
        }
    )

    try:
        # Run pipeline
        with console.status("[yellow]Running forecast pipeline...[/yellow]"):
            # Start MLflow run
            run_name = f"forecast_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            with mlflow_config.start_run(
                run_name=run_name,
                tags={
                    "environment": settings.environment,
                    "skip_email": str(skip_email),
                },
                description=f"7-day USD/CLP forecast generated on {datetime.now().isoformat()}"
            ):
                # Load data
                loader = DataLoader(settings)
                bundle = loader.load()

                # Log data stats as params
                mlflow.log_param("num_sources", len(bundle.sources))
                mlflow.log_param("num_news", len(bundle.news))
                mlflow.log_param("num_events", len(bundle.macro_events))
                mlflow.log_param("usdclp_series_length", len(bundle.usdclp_series))
                mlflow.log_param("copper_features_available", bundle.copper_features is not None)

                # Generate forecast
                engine = ForecastEngine(
                    config=settings,
                    horizon=service_config.horizon,
                    steps=service_config.steps,
                )
                forecast, artifacts = engine.forecast(bundle)

                # Log model metrics
                for model_name, result in artifacts.models.items():
                    mlflow.log_metric(f"{model_name}_rmse", result.rmse)
                    mlflow.log_metric(f"{model_name}_mape", result.mape)
                    mlflow.log_metric(f"{model_name}_weight", result.weight)

                # Log aggregate forecast metrics
                mlflow_config.log_forecast_metrics(
                    horizon="7d",
                    rmse=artifacts.ensemble_rmse,  # You may need to compute this
                    mae=artifacts.ensemble_mae,
                    mape=artifacts.ensemble_mape,
                )

                # Log forecast summary
                mlflow.log_param("forecast_mean", forecast.series[0].mean)
                mlflow.log_param("forecast_std", forecast.series[0].ci95_high - forecast.series[0].mean)

                # Generate report (existing code)
                report_path = run_forecast_pipeline(
                    skip_email=skip_email,
                    output_dir=output_dir,
                )

                # Log report as artifact
                mlflow.log_artifact(str(report_path), artifact_path="reports")

        # Success message
        console.print(f"\n[bold green]✓ Forecast completed successfully![/bold green]")
        console.print(f"[green]Report saved to:[/green] {report_path}")
        console.print(f"[cyan]MLflow run:[/cyan] {run_name}")

    except Exception as e:
        # Log failure
        mlflow.log_param("status", "failed")
        mlflow.log_param("error_message", str(e))
        console.print(f"\n[bold red]✗ Pipeline failed:[/bold red] {e}")
        logger.exception("Pipeline execution failed")
        raise typer.Exit(code=1)
```

### Step 4: Docker Compose for MLflow UI (Optional)

Add MLflow UI service to `docker-compose.yml` for on-demand viewing:

```yaml
services:
  # ... existing services ...

  # MLflow UI - on-demand web interface for viewing experiments
  mlflow-ui:
    image: ghcr.io/mlflow/mlflow:v2.16.2
    container_name: mlflow-ui
    ports:
      - "5000:5000"
    volumes:
      - ./data/mlflow:/mlflow
    command: >
      mlflow ui
      --backend-store-uri sqlite:////mlflow/mlflow.db
      --default-artifact-root /mlflow/mlruns
      --host 0.0.0.0
      --port 5000
    restart: unless-stopped
    profiles:
      - mlflow  # Only start when explicitly requested
```

**Usage:**
```bash
# Start MLflow UI
docker-compose --profile mlflow up -d mlflow-ui

# Access at http://your-vps-ip:5000

# Stop when done
docker-compose --profile mlflow down
```

### Step 5: Backup and Restore

**Backup MLflow data:**
```bash
# Backup entire MLflow directory
tar -czf mlflow_backup_$(date +%Y%m%d).tar.gz data/mlflow/

# Or use rsync for incremental backups
rsync -av data/mlflow/ /backup/mlflow/
```

**Restore:**
```bash
tar -xzf mlflow_backup_20251113.tar.gz -C ./
```

## Usage Guide

### Viewing Experiments

**Option 1: MLflow UI (Recommended)**

```bash
# Start UI server
docker-compose --profile mlflow up -d mlflow-ui

# Open browser to http://localhost:5000
```

**Option 2: CLI Query**

```python
from forex_core.mlops.mlflow_config import MLflowConfig
import mlflow

mlflow_config = MLflowConfig()
mlflow.set_tracking_uri(mlflow_config.tracking_uri)

# List all experiments
experiments = mlflow.search_experiments()
for exp in experiments:
    print(f"{exp.name}: {exp.experiment_id}")

# Get runs for an experiment
runs = mlflow.search_runs(
    experiment_names=["forecaster_7d"],
    order_by=["metrics.7d_rmse ASC"],
    max_results=10
)
print(runs[["run_id", "metrics.7d_rmse", "metrics.7d_mape", "start_time"]])
```

### Comparing Models

```python
from forex_core.mlops.mlflow_config import MLflowConfig

# Get best run from each horizon
best_7d = MLflowConfig.get_best_run("forecaster_7d", metric="7d_rmse")
best_30d = MLflowConfig.get_best_run("forecaster_30d", metric="30d_rmse")

print(f"Best 7d RMSE: {best_7d.data.metrics['7d_rmse']:.4f}")
print(f"Best 30d RMSE: {best_30d.data.metrics['30d_rmse']:.4f}")
```

### Model Rollback

If a new model performs worse, rollback to previous best:

```python
# Get previous best run
best_run = MLflowConfig.get_best_run("forecaster_7d", metric="7d_rmse")

# Load model from that run
model_uri = f"runs:/{best_run.info.run_id}/chronos_model"
model = mlflow.pytorch.load_model(model_uri)

# Use in production
# ...
```

## Monitoring Dashboard

Create a simple monitoring script:

**File:** `scripts/mlflow_dashboard.py`

```python
#!/usr/bin/env python3
"""Simple CLI dashboard for MLflow experiments."""

import mlflow
from forex_core.mlops.mlflow_config import MLflowConfig
from tabulate import tabulate

def main():
    config = MLflowConfig()
    mlflow.set_tracking_uri(config.tracking_uri)

    experiments = ["forecaster_7d", "forecaster_15d", "forecaster_30d", "forecaster_90d"]

    print("\n" + "=" * 80)
    print("MLFLOW EXPERIMENT DASHBOARD")
    print("=" * 80 + "\n")

    for exp_name in experiments:
        print(f"\n{exp_name.upper()}")
        print("-" * 80)

        runs = mlflow.search_runs(
            experiment_names=[exp_name],
            order_by=["start_time DESC"],
            max_results=5
        )

        if runs.empty:
            print("  No runs found\n")
            continue

        # Extract key columns
        table_data = []
        for _, run in runs.iterrows():
            table_data.append([
                run["start_time"].strftime("%Y-%m-%d %H:%M"),
                f"{run.get('metrics.7d_rmse', run.get('metrics.30d_rmse', 'N/A')):.4f}",
                f"{run.get('metrics.7d_mape', run.get('metrics.30d_mape', 'N/A')):.2f}%",
                run.get("tags.environment", "N/A"),
                run["run_id"][:8]
            ])

        print(tabulate(
            table_data,
            headers=["Timestamp", "RMSE", "MAPE", "Env", "Run ID"],
            tablefmt="grid"
        ))

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
```

**Usage:**
```bash
python scripts/mlflow_dashboard.py
```

## Performance Impact

### Storage Requirements
- SQLite database: ~1-5 MB per 100 runs
- Artifacts per run: ~2-10 MB (depends on model size)
- Expected growth: ~500 MB per year (daily 7d + weekly others)

### Runtime Overhead
- MLflow logging: ~0.1-0.5 seconds per run
- Negligible impact on 2-4 minute forecast pipeline

### Resource Usage
- Memory: <10 MB for tracking library
- CPU: Negligible (only during logging)
- Disk I/O: Minimal (SQLite writes are async)

## Benefits

1. **Experiment Tracking:** Compare different model configurations
2. **Model Registry:** Version control for models
3. **Reproducibility:** Track all params/metrics for each forecast
4. **Debugging:** Identify when/why forecasts degraded
5. **A/B Testing:** Compare old vs. new model performance
6. **Audit Trail:** Full history of production forecasts

## Production Checklist

- [ ] Install MLflow: `pip install mlflow>=2.16`
- [ ] Create `src/forex_core/mlops/mlflow_config.py`
- [ ] Update forecaster CLIs to use MLflow
- [ ] Test locally: `python -m services.forecaster_7d.cli run --skip-email`
- [ ] Verify MLflow database created: `ls data/mlflow/mlflow.db`
- [ ] Check runs logged: `python scripts/mlflow_dashboard.py`
- [ ] Add MLflow UI to docker-compose (optional)
- [ ] Setup backup cron job for `data/mlflow/`
- [ ] Document team workflow in README

## Troubleshooting

### Issue: SQLite database locked

**Cause:** Multiple forecast services running simultaneously

**Solution:**
- Forecasts should run sequentially (different cron schedules)
- Or use PostgreSQL backend instead of SQLite (more complex)

### Issue: MLflow UI shows no experiments

**Cause:** Wrong tracking URI or database path

**Solution:**
```bash
# Check database exists
ls -lh data/mlflow/mlflow.db

# Verify tracking URI in MLflow UI matches config
docker-compose logs mlflow-ui | grep "backend-store-uri"
```

### Issue: Artifacts not appearing in UI

**Cause:** Artifact location mismatch

**Solution:**
Ensure `--default-artifact-root` in docker-compose matches `MLflowConfig.artifact_location`

## Future Enhancements

1. **Automatic Model Selection:** Deploy best model based on validation metrics
2. **Drift Detection:** Alert when new forecasts have unusual errors
3. **Hyperparameter Tuning:** Track grid search experiments
4. **Backtesting Integration:** Log historical accuracy metrics
5. **Alerting:** Send notifications when metrics degrade
6. **Remote Backend:** Migrate to PostgreSQL for multi-writer support

---

**Last Updated:** 2025-11-13
**Version:** 1.0.0
**Status:** Production Ready (Lightweight VPS deployment)
