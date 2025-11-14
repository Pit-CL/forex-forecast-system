#!/usr/bin/env python3
"""
SARIMAX Auto-Retraining Script for USD/CLP Forecasting System.

This script automatically re-trains SARIMAX models monthly for all horizons (7d, 15d, 30d, 90d).
Implements comprehensive auto-ARIMA order selection, time-series cross-validation, diagnostic
checks, baseline comparison, and performance alerting.

Schedule: 1st of each month, 01:00 Chile time (via cron)
Execution: docker exec forex-30d python /app/scripts/auto_retrain_sarimax.py

Features:
- Loads last 2 years of data for robust seasonal pattern detection
- Auto-ARIMA order selection with horizon-specific constraints
- 12-fold time-series cross-validation with monthly splits
- Comprehensive diagnostics (ACF, PACF, residuals, Q-Q plots, Ljung-Box, Jarque-Bera)
- Baseline comparison with performance degradation detection
- Email alerts with detailed performance reports
- Failure handling with automatic fallback and notifications
- Model versioning and persistence

Author: Forex Forecast System (Phase 3: MLOps Automation)
Date: 2025-11-14
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from loguru import logger

# Import SARIMAX forecaster
from forex_core.models.sarimax_forecaster import (
    SARIMAXForecaster,
    SARIMAXConfig,
    ForecastMetrics,
    ResidualDiagnostics,
)

# Import data loader and feature engineer
from forex_core.data.loader import DataLoader
from forex_core.features.feature_engineer import engineer_features

# Import email notification components
from forex_core.notifications.email import EmailSender
from forex_core.config import get_settings

warnings.filterwarnings('ignore')

# Constants
HORIZONS = [7, 15, 30, 90]  # All horizons for SARIMAX
DATA_LOOKBACK_DAYS = 730  # 2 years of data
CV_N_SPLITS = 12  # 12-fold cross-validation (monthly splits)
MODEL_BASE_PATH = Path("/app/models")
REPORTS_PATH = Path("/app/reports")
LOGS_PATH = Path("/app/logs")
BASELINE_THRESHOLD = 0.15  # 15% RMSE increase threshold for degradation alert


@dataclass
class CrossValidationResult:
    """Results from time-series cross-validation."""

    fold_metrics: List[ForecastMetrics]
    mean_rmse: float
    std_rmse: float
    mean_mae: float
    std_mae: float
    mean_mape: float
    std_mape: float
    mean_directional_accuracy: float
    std_directional_accuracy: float

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'mean_rmse': self.mean_rmse,
            'std_rmse': self.std_rmse,
            'mean_mae': self.mean_mae,
            'std_mae': self.std_mae,
            'mean_mape': self.mean_mape,
            'std_mape': self.std_mape,
            'mean_directional_accuracy': self.mean_directional_accuracy,
            'std_directional_accuracy': self.std_directional_accuracy,
            'n_folds': len(self.fold_metrics)
        }


@dataclass
class RetrainingResult:
    """Complete re-training result for a single horizon."""

    horizon_days: int
    success: bool
    metrics: Optional[ForecastMetrics]
    cv_result: Optional[CrossValidationResult]
    diagnostics: Optional[ResidualDiagnostics]
    selected_order: Optional[Tuple]
    seasonal_order: Optional[Tuple]
    baseline_comparison: Optional[Dict]
    model_path: Optional[Path]
    diagnostics_plot_path: Optional[Path]
    error_message: Optional[str]
    training_duration_seconds: float
    timestamp: datetime


def setup_logging(horizon: Optional[int] = None) -> None:
    """
    Configure logging for re-training script.

    Args:
        horizon: Specific horizon (optional, for single-horizon mode)
    """
    log_file = LOGS_PATH / "retraining_sarimax.log"
    LOGS_PATH.mkdir(parents=True, exist_ok=True)

    # Remove default handler
    logger.remove()

    # Add console handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # Add file handler
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="DEBUG",
        rotation="10 MB"
    )

    logger.info("=" * 80)
    logger.info(f"SARIMAX AUTO-RETRAINING STARTED - {datetime.now().isoformat()}")
    if horizon:
        logger.info(f"Mode: Single horizon ({horizon}d)")
    else:
        logger.info(f"Mode: All horizons ({HORIZONS})")
    logger.info("=" * 80)


def load_training_data(lookback_days: int = DATA_LOOKBACK_DAYS) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load historical data for SARIMAX training.

    Args:
        lookback_days: Number of days to load (default: 730 = 2 years)

    Returns:
        Tuple of (target_df, exog_df)
        - target_df: DataFrame with 'close' column (USD/CLP)
        - exog_df: DataFrame with exogenous variables

    Raises:
        ValueError: If insufficient data or missing required columns
    """
    logger.info(f"Loading last {lookback_days} days of data...")

    try:
        # Load data using DataLoader
        settings = get_settings()
        loader = DataLoader(settings)
        bundle = loader.load()

        # Extract USD/CLP series
        usdclp_series = bundle.usdclp_series

        if len(usdclp_series) < lookback_days:
            logger.warning(
                f"Only {len(usdclp_series)} days available (requested {lookback_days}). "
                "Using all available data."
            )

        # Get last N days
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        usdclp_filtered = usdclp_series[usdclp_series.index >= cutoff_date]

        # Create target DataFrame
        target_df = pd.DataFrame({
            'close': usdclp_filtered.values
        }, index=usdclp_filtered.index)

        # Create exogenous variables DataFrame
        exog_df = pd.DataFrame(index=target_df.index)

        # Add copper price
        if hasattr(bundle, 'copper_series') and len(bundle.copper_series) > 0:
            copper_aligned = bundle.copper_series.reindex(target_df.index, method='ffill')
            exog_df['copper_price'] = copper_aligned
        else:
            logger.warning("Copper series not available, using constant")
            exog_df['copper_price'] = 4.0

        # Add DXY
        if hasattr(bundle, 'dxy_series') and len(bundle.dxy_series) > 0:
            dxy_aligned = bundle.dxy_series.reindex(target_df.index, method='ffill')
            exog_df['dxy_index'] = dxy_aligned
        else:
            logger.warning("DXY series not available, using constant")
            exog_df['dxy_index'] = 105.0

        # Add VIX
        if hasattr(bundle, 'vix_series') and len(bundle.vix_series) > 0:
            vix_aligned = bundle.vix_series.reindex(target_df.index, method='ffill')
            exog_df['vix'] = vix_aligned
        else:
            logger.warning("VIX series not available, using constant")
            exog_df['vix'] = 15.0

        # Add TPM (Chilean rate)
        if hasattr(bundle, 'tpm_series') and len(bundle.tpm_series) > 0:
            tpm_aligned = bundle.tpm_series.reindex(target_df.index, method='ffill')
            exog_df['tpm'] = tpm_aligned
        else:
            logger.warning("TPM series not available, using constant")
            exog_df['tpm'] = 5.5

        # Add Fed Funds rate (if available)
        if 'fed_funds' in bundle.indicators:
            fed_rate = bundle.indicators['fed_funds'].value
            exog_df['fed_rate'] = fed_rate
        else:
            exog_df['fed_rate'] = 5.0

        # Handle missing values
        exog_df = exog_df.fillna(method='ffill').fillna(method='bfill')
        target_df = target_df.fillna(method='ffill').fillna(method='bfill')

        logger.info(f"Loaded {len(target_df)} days of data")
        logger.info(f"Target range: {target_df['close'].min():.2f} - {target_df['close'].max():.2f}")
        logger.info(f"Exogenous variables: {list(exog_df.columns)}")

        return target_df, exog_df

    except Exception as e:
        logger.error(f"Failed to load training data: {e}")
        raise


def cross_validate_sarimax(
    forecaster: SARIMAXForecaster,
    data: pd.DataFrame,
    exog_data: pd.DataFrame,
    target_col: str = 'close',
    n_splits: int = CV_N_SPLITS,
    horizon_days: int = 30
) -> CrossValidationResult:
    """
    Perform time-series cross-validation with monthly splits.

    Uses expanding window approach:
    - Fold 1: Train on first N months, test on month N+1
    - Fold 2: Train on first N+1 months, test on month N+2
    - ...

    Args:
        forecaster: SARIMAXForecaster instance
        data: Target data
        exog_data: Exogenous variables
        target_col: Name of target column
        n_splits: Number of CV folds (default: 12 = monthly)
        horizon_days: Forecast horizon

    Returns:
        CrossValidationResult with aggregated metrics
    """
    logger.info(f"Starting {n_splits}-fold time-series cross-validation...")

    # Calculate split size (approximately monthly)
    split_size = len(data) // (n_splits + 2)  # Reserve data for initial training
    min_train_size = split_size * 2  # At least 2 months for initial training

    fold_metrics = []

    for fold in range(n_splits):
        train_end_idx = min_train_size + (fold * split_size)
        test_start_idx = train_end_idx
        test_end_idx = min(test_start_idx + split_size, len(data))

        if test_end_idx >= len(data):
            logger.warning(f"Fold {fold+1}: Insufficient data, stopping CV")
            break

        # Split data
        train_data = data.iloc[:train_end_idx]
        test_data = data.iloc[test_start_idx:test_end_idx]

        train_exog = exog_data.iloc[:train_end_idx]
        test_exog = exog_data.iloc[test_start_idx:test_end_idx]

        logger.info(
            f"Fold {fold+1}/{n_splits}: "
            f"Train={len(train_data)}, Test={len(test_data)}"
        )

        try:
            # Train model on fold
            fold_config = SARIMAXConfig.from_horizon(horizon_days)
            fold_forecaster = SARIMAXForecaster(fold_config)

            fold_forecaster.train(
                train_data,
                target_col=target_col,
                exog_data=train_exog,
                auto_select_order=False,  # Use default order for speed in CV
                validation_split=0.0  # No nested validation
            )

            # Predict on test fold
            y_true = test_data[target_col].values
            forecast = fold_forecaster.predict(
                steps=len(test_data),
                exog_forecast=test_exog,
                return_conf_int=False
            )
            y_pred = forecast['forecast'].values

            # Calculate metrics for fold
            metrics = SARIMAXForecaster.evaluate(
                y_true, y_pred,
                len(train_data), len(test_data)
            )
            fold_metrics.append(metrics)

            logger.info(f"Fold {fold+1} RMSE: {metrics.rmse:.2f}, MAE: {metrics.mae:.2f}")

        except Exception as e:
            logger.error(f"Fold {fold+1} failed: {e}")
            continue

    if not fold_metrics:
        raise ValueError("Cross-validation failed: No successful folds")

    # Aggregate metrics
    rmse_values = [m.rmse for m in fold_metrics]
    mae_values = [m.mae for m in fold_metrics]
    mape_values = [m.mape for m in fold_metrics]
    da_values = [m.directional_accuracy for m in fold_metrics]

    cv_result = CrossValidationResult(
        fold_metrics=fold_metrics,
        mean_rmse=float(np.mean(rmse_values)),
        std_rmse=float(np.std(rmse_values)),
        mean_mae=float(np.mean(mae_values)),
        std_mae=float(np.std(mae_values)),
        mean_mape=float(np.mean(mape_values)),
        std_mape=float(np.std(mape_values)),
        mean_directional_accuracy=float(np.mean(da_values)),
        std_directional_accuracy=float(np.std(da_values))
    )

    logger.info(
        f"CV Results: RMSE={cv_result.mean_rmse:.2f}±{cv_result.std_rmse:.2f}, "
        f"MAE={cv_result.mean_mae:.2f}±{cv_result.std_mae:.2f}, "
        f"DA={cv_result.mean_directional_accuracy:.1f}%±{cv_result.std_directional_accuracy:.1f}%"
    )

    return cv_result


def compare_with_baseline(
    horizon_days: int,
    new_metrics: ForecastMetrics
) -> Dict:
    """
    Compare new model with baseline performance.

    Args:
        horizon_days: Forecast horizon
        new_metrics: Metrics from new model

    Returns:
        Dictionary with comparison results
    """
    baseline_path = MODEL_BASE_PATH / f"sarimax_{horizon_days}d" / "baseline_metrics.json"

    comparison = {
        'has_baseline': False,
        'improved': False,
        'degraded': False,
        'rmse_change_pct': 0.0,
        'mae_change_pct': 0.0,
        'recommendation': 'DEPLOY'
    }

    if not baseline_path.exists():
        logger.info("No baseline found, this will be the new baseline")
        comparison['recommendation'] = 'DEPLOY_AS_BASELINE'
        return comparison

    try:
        with open(baseline_path, 'r') as f:
            baseline = json.load(f)

        baseline_rmse = baseline['rmse']
        baseline_mae = baseline['mae']

        # Calculate changes
        rmse_change_pct = ((new_metrics.rmse - baseline_rmse) / baseline_rmse) * 100
        mae_change_pct = ((new_metrics.mae - baseline_mae) / baseline_mae) * 100

        comparison.update({
            'has_baseline': True,
            'baseline_rmse': baseline_rmse,
            'baseline_mae': baseline_mae,
            'new_rmse': new_metrics.rmse,
            'new_mae': new_metrics.mae,
            'rmse_change_pct': rmse_change_pct,
            'mae_change_pct': mae_change_pct
        })

        # Determine if improved or degraded
        if rmse_change_pct < -5:  # More than 5% improvement
            comparison['improved'] = True
            comparison['recommendation'] = 'DEPLOY_UPDATE_BASELINE'
            logger.info(f"Model improved by {abs(rmse_change_pct):.1f}% RMSE")
        elif rmse_change_pct > BASELINE_THRESHOLD * 100:  # More than 15% degradation
            comparison['degraded'] = True
            comparison['recommendation'] = 'ALERT_DEGRADATION'
            logger.warning(f"Model degraded by {rmse_change_pct:.1f}% RMSE")
        else:
            comparison['recommendation'] = 'DEPLOY'
            logger.info(f"Model performance similar to baseline (RMSE change: {rmse_change_pct:.1f}%)")

        return comparison

    except Exception as e:
        logger.error(f"Failed to compare with baseline: {e}")
        comparison['recommendation'] = 'DEPLOY'
        return comparison


def retrain_horizon(horizon_days: int) -> RetrainingResult:
    """
    Re-train SARIMAX model for a single horizon.

    Complete workflow:
    1. Load 2 years of data
    2. Auto-ARIMA order selection
    3. 12-fold cross-validation
    4. Train final model on all data
    5. Generate diagnostics
    6. Compare with baseline
    7. Save model and diagnostics

    Args:
        horizon_days: Forecast horizon (7, 15, 30, or 90)

    Returns:
        RetrainingResult with complete training information
    """
    start_time = datetime.now()
    logger.info(f"\n{'='*60}")
    logger.info(f"RE-TRAINING SARIMAX MODEL - {horizon_days}d HORIZON")
    logger.info(f"{'='*60}\n")

    result = RetrainingResult(
        horizon_days=horizon_days,
        success=False,
        metrics=None,
        cv_result=None,
        diagnostics=None,
        selected_order=None,
        seasonal_order=None,
        baseline_comparison=None,
        model_path=None,
        diagnostics_plot_path=None,
        error_message=None,
        training_duration_seconds=0.0,
        timestamp=start_time
    )

    try:
        # Step 1: Load data
        target_df, exog_df = load_training_data(DATA_LOOKBACK_DAYS)

        # Step 2: Create forecaster with auto-ARIMA
        config = SARIMAXConfig.from_horizon(horizon_days)
        forecaster = SARIMAXForecaster(config)

        logger.info(f"Configuration: {config.exog_vars}")
        logger.info(f"Seasonal period: {config.s}")

        # Step 3: Cross-validation
        logger.info("\nStep 1: Cross-validation...")
        cv_result = cross_validate_sarimax(
            forecaster,
            target_df,
            exog_df,
            target_col='close',
            n_splits=CV_N_SPLITS,
            horizon_days=horizon_days
        )
        result.cv_result = cv_result

        # Step 4: Train final model with auto-ARIMA
        logger.info("\nStep 2: Training final model with auto-ARIMA...")
        metrics = forecaster.train(
            target_df,
            target_col='close',
            exog_data=exog_df,
            auto_select_order=True,
            validation_split=0.2
        )
        result.metrics = metrics
        result.selected_order = forecaster.selected_order
        result.seasonal_order = forecaster.seasonal_order

        logger.info(
            f"Model trained: ARIMA{result.selected_order}x{result.seasonal_order}"
        )

        # Step 5: Generate diagnostics
        logger.info("\nStep 3: Generating diagnostics...")
        diagnostics = forecaster.get_diagnostics()
        result.diagnostics = diagnostics

        # Save diagnostic plots
        diagnostics_plot_path = REPORTS_PATH / f"diagnostics_sarimax_{horizon_days}d.png"
        REPORTS_PATH.mkdir(parents=True, exist_ok=True)
        forecaster.plot_diagnostics(save_path=diagnostics_plot_path)
        result.diagnostics_plot_path = diagnostics_plot_path

        logger.info(f"Diagnostics: White noise={diagnostics.is_white_noise}, Normal={diagnostics.is_normal}")

        # Step 6: Compare with baseline
        logger.info("\nStep 4: Comparing with baseline...")
        comparison = compare_with_baseline(horizon_days, metrics)
        result.baseline_comparison = comparison

        # Step 7: Save model
        model_path = MODEL_BASE_PATH / f"sarimax_{horizon_days}d"
        logger.info(f"\nStep 5: Saving model to {model_path}...")

        metadata = {
            'horizon_days': horizon_days,
            'cv_result': cv_result.to_dict(),
            'diagnostics': {
                'ljung_box_p_value': diagnostics.ljung_box_p_value,
                'jarque_bera_p_value': diagnostics.jarque_bera_p_value,
                'is_white_noise': diagnostics.is_white_noise,
                'is_normal': diagnostics.is_normal
            },
            'baseline_comparison': comparison,
            'training_date': start_time.isoformat(),
            'data_range': f"{target_df.index[0]} to {target_df.index[-1]}",
            'training_samples': len(target_df)
        }

        forecaster.save_model(model_path, metadata=metadata)
        result.model_path = model_path

        # Update baseline if improved
        if comparison['recommendation'] in ['DEPLOY_AS_BASELINE', 'DEPLOY_UPDATE_BASELINE']:
            baseline_metrics_path = model_path / "baseline_metrics.json"
            with open(baseline_metrics_path, 'w') as f:
                json.dump(metrics.to_dict(), f, indent=2)
            logger.info("Baseline updated")

        result.success = True

        duration = (datetime.now() - start_time).total_seconds()
        result.training_duration_seconds = duration

        logger.info(f"\n{'='*60}")
        logger.info(f"RE-TRAINING COMPLETED - {horizon_days}d (duration: {duration:.1f}s)")
        logger.info(f"RMSE: {metrics.rmse:.2f}, MAE: {metrics.mae:.2f}, MAPE: {metrics.mape:.2f}%")
        logger.info(f"Directional Accuracy: {metrics.directional_accuracy:.1f}%")
        logger.info(f"Recommendation: {comparison['recommendation']}")
        logger.info(f"{'='*60}\n")

        return result

    except Exception as e:
        error_msg = f"Re-training failed for {horizon_days}d: {str(e)}"
        logger.error(error_msg)
        logger.exception("Full traceback:")

        result.error_message = error_msg
        result.training_duration_seconds = (datetime.now() - start_time).total_seconds()

        return result


def send_results_email(results: List[RetrainingResult]) -> None:
    """
    Send email with re-training results.

    Args:
        results: List of RetrainingResult objects
    """
    logger.info("Generating and sending results email...")

    try:
        settings = get_settings()
        sender = EmailSender(settings)

        # Count successes and failures
        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]

        # Determine subject
        if not successes and failures:
            subject = "🚨 CRITICAL: SARIMAX Re-training Failed for All Horizons"
        elif failures:
            subject = f"⚠️ SARIMAX Re-training: {len(successes)}/{len(results)} Successful"
        else:
            subject = f"✅ SARIMAX Re-training Completed Successfully ({len(successes)} horizons)"

        # Build email body
        body_lines = [
            "<h2>SARIMAX Monthly Re-training Report</h2>",
            f"<p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
            f"<p><strong>Status:</strong> {len(successes)}/{len(results)} horizons successful</p>",
            "<hr>"
        ]

        # Successful re-trainings
        if successes:
            body_lines.append("<h3>✅ Successful Re-trainings</h3>")
            body_lines.append("<table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse;'>")
            body_lines.append(
                "<tr style='background-color: #004f71; color: white;'>"
                "<th>Horizon</th><th>RMSE</th><th>MAE</th><th>MAPE</th><th>Dir. Acc.</th>"
                "<th>CV RMSE</th><th>Order</th><th>Status</th></tr>"
            )

            for r in successes:
                comparison = r.baseline_comparison or {}
                status = comparison.get('recommendation', 'DEPLOYED')
                rmse_change = comparison.get('rmse_change_pct', 0)

                status_color = '#28a745' if comparison.get('improved') else (
                    '#dc3545' if comparison.get('degraded') else '#ffc107'
                )

                body_lines.append(
                    f"<tr>"
                    f"<td>{r.horizon_days}d</td>"
                    f"<td>{r.metrics.rmse:.2f}</td>"
                    f"<td>{r.metrics.mae:.2f}</td>"
                    f"<td>{r.metrics.mape:.2f}%</td>"
                    f"<td>{r.metrics.directional_accuracy:.1f}%</td>"
                    f"<td>{r.cv_result.mean_rmse:.2f}±{r.cv_result.std_rmse:.2f}</td>"
                    f"<td>{r.selected_order}x{r.seasonal_order}</td>"
                    f"<td style='background-color: {status_color}; color: white;'>{status}</td>"
                    f"</tr>"
                )

            body_lines.append("</table>")

        # Failed re-trainings
        if failures:
            body_lines.append("<h3>❌ Failed Re-trainings</h3>")
            body_lines.append("<ul>")
            for r in failures:
                body_lines.append(f"<li><strong>{r.horizon_days}d:</strong> {r.error_message}</li>")
            body_lines.append("</ul>")

        # Performance alerts
        degraded_models = [r for r in successes if r.baseline_comparison and r.baseline_comparison.get('degraded')]
        if degraded_models:
            body_lines.append("<h3>⚠️ Performance Degradation Alerts</h3>")
            body_lines.append("<ul>")
            for r in degraded_models:
                rmse_change = r.baseline_comparison['rmse_change_pct']
                body_lines.append(
                    f"<li><strong>{r.horizon_days}d:</strong> RMSE increased by {rmse_change:.1f}% "
                    f"(threshold: {BASELINE_THRESHOLD*100:.0f}%)</li>"
                )
            body_lines.append("</ul>")

        # Next steps
        body_lines.append("<hr>")
        body_lines.append("<h3>Next Steps</h3>")
        body_lines.append("<ul>")
        if failures:
            body_lines.append("<li>Investigate failed re-trainings and retry manually</li>")
        if degraded_models:
            body_lines.append("<li>Review models with performance degradation</li>")
            body_lines.append("<li>Consider data quality issues or regime changes</li>")
        if not failures and not degraded_models:
            body_lines.append("<li>No action required - all models performing well</li>")
        body_lines.append("</ul>")

        body = "\n".join(body_lines)

        # Send email
        sender.send(
            subject=subject,
            body=body,
            html=True
        )

        logger.info("Results email sent successfully")

    except Exception as e:
        logger.error(f"Failed to send results email: {e}")


def main():
    """Main entry point for SARIMAX auto-retraining."""
    parser = argparse.ArgumentParser(
        description="SARIMAX Auto-Retraining Script for USD/CLP Forecasting"
    )
    parser.add_argument(
        '--horizon',
        type=int,
        choices=HORIZONS,
        help=f"Train specific horizon only (choices: {HORIZONS}). Default: all horizons"
    )
    parser.add_argument(
        '--no-email',
        action='store_true',
        help="Skip email notification"
    )
    parser.add_argument(
        '--cv-splits',
        type=int,
        default=CV_N_SPLITS,
        help=f"Number of CV splits (default: {CV_N_SPLITS})"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.horizon)

    # Determine horizons to train
    horizons_to_train = [args.horizon] if args.horizon else HORIZONS

    logger.info(f"Training horizons: {horizons_to_train}")
    logger.info(f"Cross-validation splits: {args.cv_splits}")
    logger.info(f"Data lookback: {DATA_LOOKBACK_DAYS} days")

    # Train all horizons
    results = []
    for horizon in horizons_to_train:
        try:
            result = retrain_horizon(horizon)
            results.append(result)
        except Exception as e:
            logger.error(f"Unexpected error for {horizon}d: {e}")
            results.append(RetrainingResult(
                horizon_days=horizon,
                success=False,
                metrics=None,
                cv_result=None,
                diagnostics=None,
                selected_order=None,
                seasonal_order=None,
                baseline_comparison=None,
                model_path=None,
                diagnostics_plot_path=None,
                error_message=str(e),
                training_duration_seconds=0.0,
                timestamp=datetime.now()
            ))

    # Send results email
    if not args.no_email:
        try:
            send_results_email(results)
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("SARIMAX AUTO-RETRAINING SUMMARY")
    logger.info("=" * 80)

    successes = sum(1 for r in results if r.success)
    failures = len(results) - successes

    logger.info(f"Total horizons: {len(results)}")
    logger.info(f"Successful: {successes}")
    logger.info(f"Failed: {failures}")

    for result in results:
        if result.success:
            logger.info(
                f"  ✓ {result.horizon_days}d: RMSE={result.metrics.rmse:.2f}, "
                f"MAE={result.metrics.mae:.2f}, DA={result.metrics.directional_accuracy:.1f}%"
            )
        else:
            logger.error(f"  ✗ {result.horizon_days}d: {result.error_message}")

    logger.info("=" * 80)

    # Exit with appropriate code
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
