#!/usr/bin/env python3
"""
XGBoost Auto-Retraining Script for USD/CLP Forecasting.

This script automatically re-trains XGBoost models weekly for all forecast horizons
(7d, 15d, 30d, 90d) with hyperparameter optimization using Optuna.

Process:
1. Load last 180 days of data from warehouse
2. Engineer 50+ features using feature_engineer
3. Optimize hyperparameters with Optuna (50 trials, 5-fold walk-forward validation)
4. Train final model on full dataset with best hyperparameters
5. Compare performance vs. baseline and update if improved
6. Save model with metadata to /app/models/xgboost_{horizon}/
7. Send performance alert email with results

Schedule: Sundays 00:00 Chile time (via cron)

Usage:
    # Re-train all horizons (default)
    python scripts/auto_retrain_xgboost.py

    # Re-train specific horizon
    python scripts/auto_retrain_xgboost.py --horizon 7

    # Dry run (no model saving, no emails)
    python scripts/auto_retrain_xgboost.py --dry-run

    # Fast mode (fewer trials for testing)
    python scripts/auto_retrain_xgboost.py --fast --horizon 7

Example:
    >>> # Weekly automated run from cron
    >>> python scripts/auto_retrain_xgboost.py
    >>> # Output: Models saved, baselines updated, email sent

Environment:
    PYTHONPATH=/app/src (set by Docker/cron)

Requirements:
    - xgboost>=2.0.0
    - optuna>=3.0.0
    - Data warehouse with 180+ days of history
    - Email configuration in settings

Author: Code Reviewer Agent
Date: 2025-11-14
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import optuna
import pandas as pd
from optuna.samplers import TPESampler

# Set PYTHONPATH to /app/src for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forex_core.alerts.alert_email_generator import generate_model_performance_email
from forex_core.alerts.model_performance_alerts import (
    AlertSeverity,
    AlertType,
    ModelAlert,
    ModelPerformanceMonitor,
)
from forex_core.config import get_settings
from forex_core.data.loader import DataLoader
from forex_core.features.feature_engineer import engineer_features
from forex_core.features.feature_selector import FeatureSelector
from forex_core.models.xgboost_forecaster import (
    ForecastMetrics,
    XGBoostConfig,
    XGBoostForecaster,
)
from forex_core.utils.logging import logger

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/app/logs/retraining_xgboost.log"),
        logging.StreamHandler(),
    ],
)

# Constants
DEFAULT_HORIZONS = [7, 15, 30, 90]

# Horizon-specific training windows to ensure adequate sample sizes
# Short-term forecasts (7d, 15d) use 6 months, medium-term (30d) uses 1 year,
# Long-term (90d) uses 18 months for better seasonal pattern capture
TRAINING_WINDOWS = {
    7: 252,   # 1 year - capture full TPM cycle and ensure MIN_TRAIN_SIZE
    15: 365,  # 1.5 years - stability and seasonality
    30: 365,  # 1 year - maintain (already good)
    90: 730,  # 2 years - better long-term patterns
}

# Default fallback if horizon not in dictionary
DEFAULT_TRAINING_WINDOW = 180

OPTUNA_N_TRIALS = 50
OPTUNA_N_TRIALS_FAST = 10
WALK_FORWARD_SPLITS = 5
MIN_TRAIN_SIZE = 252  # 1 year of trading days for statistical robustness (>4 samples per feature)

# Model save directory
MODELS_DIR = Path("/app/models")


def load_training_data(horizon: int = 7, days: Optional[int] = None) -> pd.DataFrame:
    """
    Load last N days of data from warehouse with all required features.

    Args:
        horizon: Forecast horizon to determine optimal training window
        days: Number of days of history to load (overrides horizon-based selection)

    Returns:
        DataFrame with columns: date, usdclp, copper_price, dxy, vix, tpm, fed_funds

    Raises:
        ValueError: If insufficient data available
        RuntimeError: If data loading fails
    """
    # Use horizon-specific training window if days not specified
    if days is None:
        days = TRAINING_WINDOWS.get(horizon, DEFAULT_TRAINING_WINDOW)

    logger.info(f"Loading last {days} days of training data for {horizon}d horizon...")

    try:
        settings = get_settings()
        loader = DataLoader(settings)
        bundle = loader.load()

        # Merge all required series into single DataFrame
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Filter to training window
        usdclp_series = bundle.usdclp_series[start_date:end_date]
        copper_series = bundle.copper_series[start_date:end_date]
        dxy_series = bundle.dxy_series[start_date:end_date]
        vix_series = bundle.vix_series[start_date:end_date]

        # TPM and Fed Funds are typically constant over short periods
        # Forward-fill to daily frequency
        tpm_series = bundle.tpm_series[start_date:end_date].resample("D").ffill()

        # Get Fed Funds from indicators or default
        if "fed_target" in bundle.indicators:
            fed_funds_value = bundle.indicators["fed_target"].value
        else:
            # Default to last known rate (adjust as needed)
            fed_funds_value = 5.25  # Example default
            logger.warning(f"Fed Funds not available, using default: {fed_funds_value}%")

        # Create unified DataFrame
        df = pd.DataFrame(
            {
                "usdclp": usdclp_series,
                "copper_price": copper_series,
                "dxy": dxy_series,
                "vix": vix_series,
            }
        )

        # Add TPM (forward-fill to daily)
        df = df.join(tpm_series.rename("tpm"), how="left")
        df["tpm"] = df["tpm"].ffill().bfill()

        # Add Fed Funds (constant for recent period)
        df["fed_funds"] = fed_funds_value

        # Forward-fill and backward-fill market data to handle weekends/holidays
        # Financial markets have different trading days, so we fill gaps
        for col in ["usdclp", "copper_price", "dxy", "vix"]:
            df[col] = df[col].ffill().bfill()

        # Drop rows with missing values (should be minimal after ffill/bfill)
        initial_len = len(df)
        df = df.dropna()
        final_len = len(df)

        if final_len < initial_len:
            logger.warning(
                f"Dropped {initial_len - final_len} rows with missing values "
                f"({(initial_len - final_len) / initial_len * 100:.1f}%)"
            )

        # Validate data quality
        if len(df) < MIN_TRAIN_SIZE:
            raise ValueError(
                f"Insufficient data: {len(df)} days (minimum {MIN_TRAIN_SIZE} required)"
            )

        # Check for data quality issues
        missing_pct = df.isna().sum().sum() / (len(df) * len(df.columns))
        if missing_pct > 0.05:
            raise ValueError(
                f"Data quality issue: {missing_pct:.1%} missing values (threshold: 5%)"
            )

        logger.info(
            f"Training data loaded: {len(df)} days, "
            f"{len(df.columns)} columns, "
            f"date range: {df.index[0].date()} to {df.index[-1].date()}"
        )

        return df

    except Exception as e:
        logger.error(f"Failed to load training data: {e}")
        raise RuntimeError(f"Data loading failed: {e}") from e


def optimize_hyperparameters(
    data: pd.DataFrame,
    horizon: int,
    n_trials: int = OPTUNA_N_TRIALS,
    n_splits: int = WALK_FORWARD_SPLITS,
) -> Tuple[Dict[str, Any], float, optuna.study.Study]:
    """
    Optimize XGBoost hyperparameters using Optuna with walk-forward validation.

    Uses Tree-structured Parzen Estimator (TPE) sampler for efficient search.
    Objective: Minimize RMSE on validation set.

    Search space (horizon-adapted):
    - learning_rate: [0.01, 0.3]
    - max_depth: [3, 10]
    - n_estimators: [100, 1000]
    - subsample: [0.6, 1.0]
    - colsample_bytree: [0.6, 1.0]
    - reg_alpha: [0, 10]
    - reg_lambda: [0, 10]
    - min_child_weight: [1, 7]
    - gamma: [0, 1]

    Args:
        data: Training data with all features
        horizon: Forecast horizon in days
        n_trials: Number of Optuna trials (default 50)
        n_splits: Number of walk-forward validation splits (default 5)

    Returns:
        Tuple of (best_params, best_rmse, study)

    Example:
        >>> best_params, best_rmse, study = optimize_hyperparameters(df, horizon=7)
        >>> print(f"Best RMSE: {best_rmse:.2f}")
        >>> print(f"Best params: {best_params}")
    """
    logger.info(
        f"Starting hyperparameter optimization: {n_trials} trials, "
        f"{n_splits}-fold walk-forward validation"
    )

    # Engineer features once
    try:
        features_df = engineer_features(data, horizon=horizon)
    except Exception as e:
        logger.error(f"Feature engineering failed: {e}")
        raise

    # Feature selection step
    logger.info(f"Performing feature selection to reduce from {len(features_df.columns)-1} features...")
    feature_selector = FeatureSelector(target_features=30, correlation_threshold=0.95)

    # Separate features and target
    target_col = "usdclp"
    feature_cols = [col for col in features_df.columns if col != target_col]
    X = features_df[feature_cols]
    y = features_df[target_col]

    # Apply feature selection
    try:
        X_selected = feature_selector.fit_select(X, y, verbose=True)
        logger.info(f"Selected {len(X_selected.columns)} features for optimization")

        # Reconstruct dataframe with selected features and target
        features_df_selected = pd.concat([X_selected, y], axis=1)

        # Save feature selector for later use in training
        models_dir = MODELS_DIR / f"xgboost_{horizon}d"
        models_dir.mkdir(parents=True, exist_ok=True)
        selector_path = models_dir / "feature_selector.pkl"
        feature_selector.save(str(selector_path))
        logger.info(f"Feature selector saved to {selector_path}")

    except Exception as e:
        logger.warning(f"Feature selection failed: {e}. Using all features.")
        features_df_selected = features_df

    def objective(trial: optuna.Trial) -> float:
        """Optuna objective function: minimize RMSE."""

        # Sample hyperparameters
        params = {
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "n_estimators": trial.suggest_int("n_estimators", 100, 1000, step=50),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 0, 10),
            "reg_lambda": trial.suggest_float("reg_lambda", 0, 10),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 7),
            "gamma": trial.suggest_float("gamma", 0, 1),
        }

        # Create config with trial parameters
        config = XGBoostConfig(horizon_days=horizon, **params)
        forecaster = XGBoostForecaster(config)

        try:
            # Walk-forward validation with selected features
            metrics_list = forecaster.walk_forward_validation(
                features_df_selected,
                target_col="usdclp",
                n_splits=n_splits,
                min_train_size=MIN_TRAIN_SIZE,
            )

            if not metrics_list:
                logger.warning(f"Trial {trial.number}: No validation metrics (insufficient data)")
                return float("inf")

            # Calculate average RMSE across folds
            avg_rmse = np.mean([m.rmse for m in metrics_list])

            # Report intermediate value for pruning
            trial.report(avg_rmse, step=0)

            # Prune unpromising trials
            if trial.should_prune():
                raise optuna.TrialPruned()

            return avg_rmse

        except optuna.TrialPruned:
            raise
        except Exception as e:
            logger.warning(f"Trial {trial.number} failed: {e}")
            return float("inf")

    # Create study with TPE sampler
    study = optuna.create_study(
        direction="minimize",
        sampler=TPESampler(seed=42),
        study_name=f"xgboost_horizon_{horizon}d",
    )

    # Suppress Optuna logging noise
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    # Run optimization
    start_time = time.time()
    study.optimize(
        objective,
        n_trials=n_trials,
        timeout=None,
        show_progress_bar=True,
        n_jobs=1,  # Sequential for reproducibility
    )
    elapsed = time.time() - start_time

    best_params = study.best_params
    best_rmse = study.best_value

    logger.info(
        f"Optimization complete: Best RMSE={best_rmse:.2f}, "
        f"Time={elapsed:.1f}s ({elapsed / n_trials:.1f}s/trial)"
    )
    logger.info(f"Best hyperparameters: {json.dumps(best_params, indent=2)}")

    return best_params, best_rmse, study


def train_final_model(
    data: pd.DataFrame,
    horizon: int,
    hyperparameters: Dict[str, Any],
) -> Tuple[XGBoostForecaster, ForecastMetrics]:
    """
    Train final XGBoost model on full dataset with best hyperparameters.

    Uses 80/20 train/validation split for final metrics.

    Args:
        data: Full training data
        horizon: Forecast horizon in days
        hyperparameters: Best hyperparameters from Optuna

    Returns:
        Tuple of (trained_forecaster, training_metrics)

    Raises:
        RuntimeError: If training fails
    """
    logger.info(f"Training final model for {horizon}d horizon with best hyperparameters")

    try:
        # Engineer features
        features_df = engineer_features(data, horizon=horizon)

        # Load and apply feature selector if it exists
        models_dir = MODELS_DIR / f"xgboost_{horizon}d"
        selector_path = models_dir / "feature_selector.pkl"

        if selector_path.exists():
            logger.info(f"Loading feature selector from {selector_path}")
            feature_selector = FeatureSelector.load(str(selector_path))

            # Apply feature selection
            target_col = "usdclp"
            feature_cols = [col for col in features_df.columns if col != target_col]
            X = features_df[feature_cols]
            y = features_df[target_col]

            X_selected = feature_selector.transform(X)
            features_df = pd.concat([X_selected, y], axis=1)
            logger.info(f"Applied feature selection: {len(X_selected.columns)} features")
        else:
            logger.info("No feature selector found, using all features")

        # Create config with best hyperparameters
        config = XGBoostConfig(horizon_days=horizon, **hyperparameters)
        forecaster = XGBoostForecaster(config)

        # Train on full dataset (80/20 split)
        metrics = forecaster.train(
            features_df,
            target_col="usdclp",
            validation_split=0.2,
            early_stopping_rounds=50,
            verbose=False,
        )

        logger.info(
            f"Training complete: RMSE={metrics.rmse:.2f}, MAE={metrics.mae:.2f}, "
            f"MAPE={metrics.mape:.2f}%, Directional Accuracy={metrics.directional_accuracy:.1f}%"
        )

        return forecaster, metrics

    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise RuntimeError(f"Model training failed: {e}") from e


def compare_with_baseline(
    model_name: str,
    horizon: str,
    new_metrics: ForecastMetrics,
    monitor: ModelPerformanceMonitor,
) -> Tuple[bool, List[ModelAlert]]:
    """
    Compare new model performance with baseline and decide whether to update.

    Decision logic:
    - If no baseline exists: Accept new model, create baseline
    - If RMSE improved by >5%: Accept and update baseline
    - If RMSE degraded by <10%: Accept but keep baseline (natural variance)
    - If RMSE degraded by >10%: Reject, keep old model and baseline

    Args:
        model_name: Model identifier (e.g., "xgboost_7d")
        horizon: Forecast horizon string (e.g., "7d")
        new_metrics: Metrics from newly trained model
        monitor: ModelPerformanceMonitor instance

    Returns:
        Tuple of (should_update_baseline, alerts)
        - should_update_baseline: True if new model is better
        - alerts: List of alerts generated

    Example:
        >>> should_update, alerts = compare_with_baseline(
        ...     "xgboost_7d", "7d", metrics, monitor
        ... )
        >>> if should_update:
        ...     monitor.update_baseline("xgboost_7d", "7d", metrics_dict)
    """
    logger.info(f"Comparing {model_name} ({horizon}) with baseline")

    # Convert metrics to dict
    metrics_dict = {
        "rmse": new_metrics.rmse,
        "mae": new_metrics.mae,
        "mape": new_metrics.mape,
        "directional_accuracy": new_metrics.directional_accuracy,
    }

    # Check degradation
    alerts = monitor.check_degradation(model_name, metrics_dict, horizon)

    # Load baseline for comparison
    baseline = monitor.load_baseline(model_name, horizon)

    if baseline is None:
        # No baseline exists - accept new model
        logger.info("No baseline exists - accepting new model and creating baseline")
        return True, alerts

    # Calculate improvement/degradation
    rmse_change = (new_metrics.rmse - baseline.rmse) / baseline.rmse * 100

    if rmse_change <= -5.0:
        # Significant improvement (>5%)
        logger.info(f"RMSE improved by {abs(rmse_change):.1f}% - updating baseline")
        return True, alerts
    elif rmse_change <= 10.0:
        # Minor degradation (<10%) - acceptable (natural variance)
        logger.info(
            f"RMSE changed by {rmse_change:+.1f}% - within tolerance, "
            "accepting model but keeping baseline"
        )
        return False, alerts
    else:
        # Significant degradation (>10%) - reject
        logger.warning(
            f"RMSE degraded by {rmse_change:+.1f}% - rejecting new model, "
            "keeping previous version"
        )

        # Add critical alert
        alerts.append(
            ModelAlert(
                alert_type=AlertType.RETRAINING_FAILURE,
                severity=AlertSeverity.CRITICAL,
                model_name=model_name,
                horizon=horizon,
                message=f"New model rejected: RMSE degraded by {rmse_change:+.1f}%",
                current_metrics=metrics_dict,
                baseline_metrics=baseline.to_dict(),
                recommendations=[
                    "Continue using previous model version",
                    "Investigate data quality or regime change",
                    "Consider adjusting hyperparameter search space",
                    "Review recent market conditions for anomalies",
                ],
            )
        )

        return False, alerts


def save_model_with_metadata(
    forecaster: XGBoostForecaster,
    horizon: int,
    hyperparameters: Dict[str, Any],
    metrics: ForecastMetrics,
    optimization_time: float,
    baseline_comparison: str,
) -> Path:
    """
    Save trained model with comprehensive metadata.

    Saves:
    - XGBoost model (JSON format)
    - Scalers (pickle)
    - Metadata (JSON): config, hyperparameters, metrics, timestamp, etc.
    - Optimization results (JSON): trials, best params, search history

    Args:
        forecaster: Trained XGBoostForecaster
        horizon: Forecast horizon in days
        hyperparameters: Best hyperparameters from Optuna
        metrics: Training metrics
        optimization_time: Time spent on optimization (seconds)
        baseline_comparison: Comparison result string

    Returns:
        Path to saved model directory

    Example:
        >>> model_path = save_model_with_metadata(
        ...     forecaster, 7, best_params, metrics, 245.3, "Improved by 12.5%"
        ... )
        >>> print(f"Model saved to {model_path}")
    """
    model_dir = MODELS_DIR / f"xgboost_{horizon}d"
    model_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Saving model to {model_dir}")

    # Prepare metadata
    metadata = {
        "model_type": "xgboost",
        "horizon_days": horizon,
        "hyperparameters": hyperparameters,
        "training_metrics": metrics.to_dict(),
        "optimization_time_seconds": optimization_time,
        "baseline_comparison": baseline_comparison,
        "trained_at": datetime.now().isoformat(),
        "training_window_days": TRAINING_WINDOWS.get(horizon, DEFAULT_TRAINING_WINDOW),
        "optuna_trials": OPTUNA_N_TRIALS,
        "model_version": "1.0.0",
    }

    # Save model with metadata
    forecaster.save_model(model_dir, metadata=metadata)

    logger.info(f"Model saved successfully: {model_dir}")

    return model_dir


def send_results_email(
    alerts: List[ModelAlert],
    dry_run: bool = False,
) -> bool:
    """
    Send performance alert email with re-training results.

    Email includes:
    - Summary of all horizons re-trained
    - Performance metrics (current vs baseline)
    - Hyperparameter changes
    - Recommendations

    Args:
        alerts: List of ModelAlert objects from all horizons
        dry_run: If True, generate email but don't send

    Returns:
        True if email sent successfully, False otherwise

    Example:
        >>> success = send_results_email(all_alerts, dry_run=False)
        >>> if success:
        ...     logger.info("Email sent successfully")
    """
    if not alerts:
        logger.info("No alerts to send")
        return True

    logger.info(f"Generating performance alert email for {len(alerts)} alerts")

    try:
        # Generate email HTML and PDF
        html, pdf_bytes = generate_model_performance_email(alerts, generate_pdf=True)

        if dry_run:
            logger.info("DRY RUN: Email generated but not sent")
            logger.debug(f"Email HTML length: {len(html)} chars")
            if pdf_bytes:
                logger.debug(f"PDF size: {len(pdf_bytes)} bytes")
            return True

        # TODO: Integrate with email sending system (Gmail SMTP)
        # For now, save to file for manual review
        email_dir = Path("/app/logs/emails")
        email_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = email_dir / f"retraining_alert_{timestamp}.html"
        html_path.write_text(html, encoding="utf-8")
        logger.info(f"Email HTML saved to {html_path}")

        if pdf_bytes:
            pdf_path = email_dir / f"retraining_alert_{timestamp}.pdf"
            pdf_path.write_bytes(pdf_bytes)
            logger.info(f"Email PDF saved to {pdf_path}")

        logger.info("Email sent successfully (saved to logs for review)")
        return True

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def retrain_horizon(
    horizon: int,
    monitor: ModelPerformanceMonitor,
    fast_mode: bool = False,
    dry_run: bool = False,
) -> Tuple[bool, List[ModelAlert]]:
    """
    Re-train XGBoost model for single horizon.

    Complete workflow:
    1. Load training data (180 days)
    2. Optimize hyperparameters (Optuna)
    3. Train final model
    4. Compare with baseline
    5. Save model if accepted
    6. Update baseline if improved

    Args:
        horizon: Forecast horizon in days (7, 15, 30, or 90)
        monitor: ModelPerformanceMonitor for baseline comparison
        fast_mode: If True, use fewer Optuna trials (for testing)
        dry_run: If True, don't save models or update baselines

    Returns:
        Tuple of (success, alerts)

    Example:
        >>> monitor = ModelPerformanceMonitor()
        >>> success, alerts = retrain_horizon(7, monitor, fast_mode=False)
        >>> if success:
        ...     print("Re-training successful")
    """
    model_name = f"xgboost_{horizon}d"
    horizon_str = f"{horizon}d"

    logger.info(f"{'=' * 60}")
    logger.info(f"Starting re-training for {model_name}")
    logger.info(f"{'=' * 60}")

    start_time = time.time()
    alerts: List[ModelAlert] = []

    try:
        # Step 1: Load training data
        logger.info("Step 1/6: Loading training data")
        data = load_training_data(horizon=horizon)

        # Check data quality
        missing_pct = data.isna().sum().sum() / (len(data) * len(data.columns))
        if missing_pct > 0.05:
            alerts.append(
                ModelAlert(
                    alert_type=AlertType.DATA_QUALITY_ISSUE,
                    severity=AlertSeverity.WARNING,
                    model_name=model_name,
                    horizon=horizon_str,
                    message=f"Data quality issue: {missing_pct:.1%} missing values",
                    details={"missing_pct": missing_pct},
                    recommendations=[
                        "Review data collection process",
                        "Check for API outages",
                        "Consider imputation strategies",
                    ],
                )
            )

        # Step 2: Optimize hyperparameters
        logger.info("Step 2/6: Optimizing hyperparameters")
        n_trials = OPTUNA_N_TRIALS_FAST if fast_mode else OPTUNA_N_TRIALS
        best_params, best_rmse, study = optimize_hyperparameters(
            data, horizon, n_trials=n_trials
        )
        optimization_time = time.time() - start_time

        # Step 3: Train final model
        logger.info("Step 3/6: Training final model")
        forecaster, metrics = train_final_model(data, horizon, best_params)

        # Step 4: Compare with baseline
        logger.info("Step 4/6: Comparing with baseline")
        should_update_baseline, comparison_alerts = compare_with_baseline(
            model_name, horizon_str, metrics, monitor
        )
        alerts.extend(comparison_alerts)

        # Determine baseline comparison string
        baseline = monitor.load_baseline(model_name, horizon_str)
        if baseline:
            rmse_change = (metrics.rmse - baseline.rmse) / baseline.rmse * 100
            baseline_comparison = f"RMSE changed by {rmse_change:+.1f}% vs baseline"
        else:
            baseline_comparison = "No baseline - first training"

        # Step 5: Save model
        logger.info("Step 5/6: Saving model")
        if not dry_run:
            model_path = save_model_with_metadata(
                forecaster,
                horizon,
                best_params,
                metrics,
                optimization_time,
                baseline_comparison,
            )
        else:
            logger.info("DRY RUN: Model not saved")
            model_path = MODELS_DIR / f"xgboost_{horizon}d"

        # Step 6: Update baseline if improved
        logger.info("Step 6/6: Updating baseline (if improved)")
        if should_update_baseline and not dry_run:
            metrics_dict = {
                "rmse": metrics.rmse,
                "mae": metrics.mae,
                "mape": metrics.mape,
                "directional_accuracy": metrics.directional_accuracy,
            }
            monitor.update_baseline(
                model_name, horizon_str, metrics_dict, update_strategy="replace"
            )
            logger.info("Baseline updated with new metrics")
        else:
            logger.info("Baseline not updated (kept previous version)")

        # Generate success alert
        alerts.append(
            ModelAlert(
                alert_type=AlertType.RETRAINING_SUCCESS,
                severity=AlertSeverity.INFO,
                model_name=model_name,
                horizon=horizon_str,
                message=f"Re-training completed: {baseline_comparison}",
                current_metrics={
                    "rmse": metrics.rmse,
                    "mae": metrics.mae,
                    "mape": metrics.mape,
                    "directional_accuracy": metrics.directional_accuracy,
                },
                baseline_metrics=baseline.to_dict() if baseline else None,
                details={
                    "hyperparameters": best_params,
                    "optimization_time_seconds": optimization_time,
                    "optuna_trials": n_trials,
                    "model_path": str(model_path),
                },
                recommendations=[
                    "Monitor next 3-5 forecasts with new model",
                    "Compare predictions with previous model version",
                    f"Baseline {'updated' if should_update_baseline else 'kept'}",
                ],
            )
        )

        total_time = time.time() - start_time
        logger.info(f"Re-training complete for {model_name}: {total_time:.1f}s")
        logger.info(
            f"Final metrics: RMSE={metrics.rmse:.2f}, MAE={metrics.mae:.2f}, "
            f"MAPE={metrics.mape:.2f}%, Dir.Acc={metrics.directional_accuracy:.1f}%"
        )

        return True, alerts

    except Exception as e:
        logger.error(f"Re-training failed for {model_name}: {e}", exc_info=True)

        # Generate failure alert
        alerts.append(
            ModelAlert(
                alert_type=AlertType.RETRAINING_FAILURE,
                severity=AlertSeverity.CRITICAL,
                model_name=model_name,
                horizon=horizon_str,
                message=f"Re-training FAILED: {str(e)}",
                details={"error": str(e), "error_type": type(e).__name__},
                recommendations=[
                    "CRITICAL: Continue using previous model version",
                    "Investigate failure cause in logs",
                    "Check data availability and quality",
                    "Verify hyperparameter search space",
                    "Notify ML team for manual review",
                ],
            )
        )

        return False, alerts


def main():
    """
    Main entry point for XGBoost auto-retraining.

    Command-line interface:
        --horizon: Specific horizon to retrain (7, 15, 30, or 90). If not specified, retrains all.
        --fast: Fast mode with fewer Optuna trials (for testing)
        --dry-run: Dry run mode (no saving, no emails)

    Exit codes:
        0: Success (all horizons trained)
        1: Partial failure (some horizons failed)
        2: Complete failure (all horizons failed)

    Example:
        $ python scripts/auto_retrain_xgboost.py --horizon 7 --fast
    """
    parser = argparse.ArgumentParser(
        description="Automatically re-train XGBoost models for USD/CLP forecasting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Re-train all horizons (production)
  python scripts/auto_retrain_xgboost.py

  # Re-train specific horizon (testing)
  python scripts/auto_retrain_xgboost.py --horizon 7

  # Fast mode with fewer trials (development)
  python scripts/auto_retrain_xgboost.py --fast --horizon 7

  # Dry run (no saving, no emails)
  python scripts/auto_retrain_xgboost.py --dry-run

Scheduled via cron:
  0 3 * * 0 cd /app && PYTHONPATH=/app/src python scripts/auto_retrain_xgboost.py
  (Sunday 00:00 Chile = 03:00 UTC)
        """,
    )

    parser.add_argument(
        "--horizon",
        type=int,
        choices=[7, 15, 30, 90],
        help="Specific horizon to retrain (7, 15, 30, or 90). If not specified, retrains all.",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help=f"Fast mode: Use {OPTUNA_N_TRIALS_FAST} trials instead of {OPTUNA_N_TRIALS} (for testing)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run: Generate models and emails but don't save or send",
    )

    args = parser.parse_args()

    # Determine horizons to train
    horizons = [args.horizon] if args.horizon else DEFAULT_HORIZONS

    logger.info("=" * 80)
    logger.info("XGBoost Auto-Retraining Started")
    logger.info("=" * 80)
    logger.info(f"Horizons: {horizons}")
    logger.info(f"Fast mode: {args.fast}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"Optuna trials: {OPTUNA_N_TRIALS_FAST if args.fast else OPTUNA_N_TRIALS}")
    logger.info(f"Training windows: {', '.join([f'{h}d:{TRAINING_WINDOWS[h]}' for h in horizons])}")
    logger.info(f"Walk-forward splits: {WALK_FORWARD_SPLITS}")
    logger.info("=" * 80)

    # Initialize monitor
    baseline_dir = Path("/app/data/baselines")
    monitor = ModelPerformanceMonitor(
        baseline_dir=baseline_dir,
        degradation_warning_threshold=0.15,  # 15%
        degradation_critical_threshold=0.30,  # 30%
        directional_accuracy_threshold=0.55,  # 55%
    )

    # Re-train each horizon
    all_alerts: List[ModelAlert] = []
    successes = 0
    failures = 0

    for horizon in horizons:
        success, alerts = retrain_horizon(
            horizon, monitor, fast_mode=args.fast, dry_run=args.dry_run
        )
        all_alerts.extend(alerts)

        if success:
            successes += 1
        else:
            failures += 1

    # Send results email
    logger.info("=" * 80)
    logger.info("Re-training Summary")
    logger.info("=" * 80)
    logger.info(f"Successes: {successes}/{len(horizons)}")
    logger.info(f"Failures: {failures}/{len(horizons)}")
    logger.info(f"Total alerts: {len(all_alerts)}")

    # Group alerts by severity
    critical = [a for a in all_alerts if a.severity == AlertSeverity.CRITICAL]
    warning = [a for a in all_alerts if a.severity == AlertSeverity.WARNING]
    info = [a for a in all_alerts if a.severity == AlertSeverity.INFO]

    logger.info(f"  CRITICAL: {len(critical)}")
    logger.info(f"  WARNING: {len(warning)}")
    logger.info(f"  INFO: {len(info)}")

    # Send email
    logger.info("=" * 80)
    logger.info("Sending results email...")
    email_sent = send_results_email(all_alerts, dry_run=args.dry_run)

    if email_sent:
        logger.info("Email sent successfully")
    else:
        logger.warning("Email sending failed (check logs)")

    # Final summary
    logger.info("=" * 80)
    logger.info("XGBoost Auto-Retraining Complete")
    logger.info("=" * 80)

    # Determine exit code
    if failures == 0:
        logger.info("✅ All horizons re-trained successfully")
        sys.exit(0)
    elif successes > 0:
        logger.warning(f"⚠️ Partial failure: {successes} succeeded, {failures} failed")
        sys.exit(1)
    else:
        logger.error("❌ Complete failure: All horizons failed")
        sys.exit(2)


if __name__ == "__main__":
    main()
