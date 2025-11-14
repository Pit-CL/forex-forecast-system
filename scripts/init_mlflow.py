#!/usr/bin/env python3
"""
Initialize MLflow for forex forecasting system.

This script sets up MLflow experiments for all forecast horizons
and validates the installation.

Usage:
    python scripts/init_mlflow.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forex_core.mlops.mlflow_config import is_mlflow_available, MLflowConfig
from loguru import logger


def main() -> int:
    """Initialize MLflow experiments."""
    logger.info("=" * 60)
    logger.info("MLFLOW INITIALIZATION")
    logger.info("=" * 60)

    # Check MLflow availability
    if not is_mlflow_available():
        logger.error("MLflow is not installed!")
        logger.error("Install with: pip install mlflow>=2.16")
        return 1

    logger.info("✓ MLflow is installed")

    # Initialize config
    try:
        config = MLflowConfig()
        logger.info(f"✓ MLflow config created")
        logger.info(f"  Tracking URI: {config.tracking_uri}")
        logger.info(f"  Artifact location: {config.artifact_location}")
    except Exception as e:
        logger.error(f"✗ Failed to create MLflow config: {e}")
        return 1

    # Create experiments for all horizons
    horizons = [
        ("forecaster_7d", "7d", "7-day USD/CLP forecast"),
        ("forecaster_15d", "15d", "15-day USD/CLP forecast"),
        ("forecaster_30d", "30d", "30-day USD/CLP forecast"),
        ("forecaster_90d", "90d", "90-day USD/CLP forecast"),
    ]

    logger.info("\nCreating experiments...")

    for exp_name, horizon, description in horizons:
        try:
            exp_id = config.setup(
                experiment_name=exp_name,
                tags={
                    "horizon": horizon,
                    "model_family": "chronos",
                    "currency_pair": "USD/CLP",
                    "description": description,
                },
            )
            logger.info(f"✓ {exp_name}: ID={exp_id}")
        except Exception as e:
            logger.error(f"✗ Failed to create {exp_name}: {e}")
            return 1

    # Verify setup
    logger.info("\nVerifying setup...")

    import mlflow

    mlflow.set_tracking_uri(config.tracking_uri)

    experiments = mlflow.search_experiments()
    logger.info(f"✓ Found {len(experiments)} experiments:")

    for exp in experiments:
        logger.info(f"  - {exp.name} (ID: {exp.experiment_id})")

    # Check directories
    logger.info("\nVerifying directories...")

    if Path(config.base_dir).exists():
        logger.info(f"✓ Base directory exists: {config.base_dir}")
    else:
        logger.error(f"✗ Base directory missing: {config.base_dir}")
        return 1

    if Path(config.artifact_location).exists():
        logger.info(f"✓ Artifact location exists: {config.artifact_location}")
    else:
        logger.error(f"✗ Artifact location missing: {config.artifact_location}")
        return 1

    # Final success message
    logger.info("\n" + "=" * 60)
    logger.info("✓ MLFLOW INITIALIZATION COMPLETE")
    logger.info("=" * 60)
    logger.info("\nNext steps:")
    logger.info("1. Run a forecast: python -m services.forecaster_7d.cli run --skip-email")
    logger.info("2. View dashboard: python scripts/mlflow_dashboard.py")
    logger.info("3. Start UI: docker-compose --profile mlflow up -d mlflow-ui")
    logger.info("   Then visit: http://localhost:5000")
    logger.info("")

    return 0


if __name__ == "__main__":
    sys.exit(main())
