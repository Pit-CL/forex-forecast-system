#!/usr/bin/env python3
"""
Main Forecasting Script - USD/CLP Ensemble System.

This script orchestrates the complete forecasting workflow for USD/CLP using
the ensemble system (XGBoost + SARIMAX + GARCH). It integrates all components:
- Data loading and feature engineering
- Ensemble model loading/training
- Forecast generation
- Market shock detection
- Model performance monitoring
- Results saving
- Chart generation
- Email delivery (via test_email_and_pdf.py)

Usage:
    # Generate 7-day forecast
    python scripts/forecast_with_ensemble.py --horizon 7

    # Generate 30-day forecast without email
    python scripts/forecast_with_ensemble.py --horizon 30 --no-email

    # Train new models (first time or re-training)
    python scripts/forecast_with_ensemble.py --horizon 7 --train

    # Verbose logging
    python scripts/forecast_with_ensemble.py --horizon 15 -v

Design Philosophy (KISS):
    - Linear workflow: load → prepare → predict → detect → save → email
    - Clear error messages and logging
    - Fail gracefully with alerts
    - Reuse existing components (no duplication)
    - Simple CLI interface

Author: Code Simplifier Agent
Date: 2025-11-14
Phase: 4 (Integration) - Implementation Plan
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import numpy as np
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loguru import logger

# Import ensemble components
from forex_core.models.ensemble_forecaster import (
    EnsembleForecaster,
    EnsembleForecast,
    EnsembleMetrics,
)
from forex_core.features.feature_engineer import engineer_features, validate_features
from forex_core.alerts.market_shock_detector import MarketShockDetector, AlertSeverity
from forex_core.alerts.alert_email_generator import generate_market_shock_email

# Import data loader (existing)
# Assuming there's a DataLoader class - will create minimal version if needed
try:
    from forex_core.data.loader import DataLoader
except ImportError:
    logger.warning("DataLoader not found - will use fallback data loading")
    DataLoader = None


# ============================================================================
# CONFIGURATION
# ============================================================================

# Docker paths (production)
DOCKER_DATA_DIR = Path("/app/data")
DOCKER_MODELS_DIR = Path("/app/models")
DOCKER_OUTPUT_DIR = Path("/app/output")
DOCKER_REPORTS_DIR = Path("/app/reports")

# Local paths (development)
LOCAL_DATA_DIR = Path(__file__).parent.parent / "data"
LOCAL_MODELS_DIR = Path(__file__).parent.parent / "models"
LOCAL_OUTPUT_DIR = Path(__file__).parent.parent / "output"
LOCAL_REPORTS_DIR = Path(__file__).parent.parent / "reports"

# Detect environment
IS_DOCKER = DOCKER_DATA_DIR.exists() and DOCKER_MODELS_DIR.exists()

# Select paths based on environment
if IS_DOCKER:
    DATA_DIR = DOCKER_DATA_DIR
    MODELS_DIR = DOCKER_MODELS_DIR
    OUTPUT_DIR = DOCKER_OUTPUT_DIR
    REPORTS_DIR = DOCKER_REPORTS_DIR
else:
    DATA_DIR = LOCAL_DATA_DIR
    MODELS_DIR = LOCAL_MODELS_DIR
    OUTPUT_DIR = LOCAL_OUTPUT_DIR
    REPORTS_DIR = LOCAL_REPORTS_DIR

# Create directories if they don't exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / "charts").mkdir(exist_ok=True)

# Minimum data requirements
MIN_TRAINING_DAYS = 180
MIN_PREDICTION_DAYS = 30

# Email script path
EMAIL_SCRIPT = Path(__file__).parent / "test_email_and_pdf.py"


# ============================================================================
# DATA LOADING
# ============================================================================

def load_and_prepare_data(horizon_days: int, verbose: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load latest market data and engineer features.

    This function:
    1. Loads raw USD/CLP, copper, and macro data (last 180+ days)
    2. Engineers 50+ features using feature_engineer
    3. Validates data quality
    4. Prepares exogenous variables for SARIMAX

    Args:
        horizon_days: Forecast horizon in days (7, 15, 30, 90)
        verbose: Enable verbose logging

    Returns:
        Tuple of (features_df, exog_df)
        - features_df: Full dataset with engineered features
        - exog_df: Exogenous variables for SARIMAX (copper, DXY, VIX, TPM)

    Raises:
        ValueError: If data is insufficient or invalid
        FileNotFoundError: If data files are missing
    """
    if verbose:
        logger.info(f"Loading data for {horizon_days}d forecast...")

    # Try to use DataLoader if available
    if DataLoader is not None:
        try:
            loader = DataLoader()
            # DataLoader.load() returns a DataBundle, not a DataFrame
            # We need to convert it to the expected DataFrame format
            raw_data = _convert_databundle_to_dataframe(loader, MIN_TRAINING_DAYS + horizon_days)
            logger.info(f"Loaded {len(raw_data)} days of data via DataLoader")
        except Exception as e:
            logger.warning(f"DataLoader failed: {e}. Using fallback...")
            raw_data = _load_data_fallback(horizon_days)
    else:
        raw_data = _load_data_fallback(horizon_days)

    # Validate minimum data
    if len(raw_data) < MIN_TRAINING_DAYS:
        raise ValueError(
            f"Insufficient data: {len(raw_data)} days "
            f"(need at least {MIN_TRAINING_DAYS} days)"
        )

    logger.info(f"Raw data loaded: {len(raw_data)} rows")

    # Engineer features
    if verbose:
        logger.info("Engineering features (50+ indicators)...")

    features_df = engineer_features(raw_data, horizon=horizon_days)

    # Validate features
    if not validate_features(features_df):
        raise ValueError("Feature validation failed - check data quality")

    logger.info(f"Features engineered: {len(features_df.columns)} columns")

    # Prepare exogenous variables for SARIMAX
    exog_cols = ['copper_price', 'dxy', 'vix', 'tpm']
    available_cols = [col for col in exog_cols if col in features_df.columns]

    if available_cols:
        exog_df = features_df[available_cols].copy()
        logger.info(f"Exogenous variables prepared: {', '.join(available_cols)}")
    else:
        logger.warning("No exogenous variables found - SARIMAX will be univariate")
        exog_df = None

    return features_df, exog_df


def _convert_databundle_to_dataframe(loader: DataLoader, days: int) -> pd.DataFrame:
    """
    Convert DataBundle from DataLoader to DataFrame format expected by feature engineering.

    Args:
        loader: DataLoader instance
        days: Number of days of data to load

    Returns:
        DataFrame with columns: usdclp, copper_price, dxy, vix, tpm, fed_funds,
                                and Chilean indicators if available
    """
    # Load the DataBundle
    bundle = loader.load()

    # Start with USDCLP as the base
    df = pd.DataFrame(index=bundle.usdclp_series.index)
    df['usdclp'] = bundle.usdclp_series
    # NOTE: 'value' column will be loaded by ensemble_forecaster from parquet
    # This ensures we use truly raw values for adaptive window calculation

    # Add copper data
    if hasattr(bundle, 'copper_series') and bundle.copper_series is not None:
        # Align copper data with USDCLP index
        df['copper_price'] = bundle.copper_series.reindex(df.index, method='ffill')

    # Add DXY
    if hasattr(bundle, 'dxy_series') and bundle.dxy_series is not None:
        df['dxy'] = bundle.dxy_series.reindex(df.index, method='ffill')

    # Add VIX
    if hasattr(bundle, 'vix_series') and bundle.vix_series is not None:
        df['vix'] = bundle.vix_series.reindex(df.index, method='ffill')

    # Add TPM (Chilean policy rate)
    if hasattr(bundle, 'tpm_series') and bundle.tpm_series is not None:
        df['tpm'] = bundle.tpm_series.reindex(df.index, method='ffill')

    # Add Fed Funds rate (if available)
    if 'fed_target' in bundle.indicators:
        df['fed_funds'] = bundle.indicators['fed_target'].value
    else:
        # Default Fed Funds rate
        df['fed_funds'] = 5.0

    # Add Chilean economic indicators
    if hasattr(bundle, 'chilean_indicators') and bundle.chilean_indicators:
        for name, series in bundle.chilean_indicators.items():
            if series is not None:
                # Resample monthly to daily and forward-fill
                daily_series = series.resample('D').ffill() if not series.empty else series
                df[name] = daily_series.reindex(df.index, method='ffill')
                logger.info(f"Added Chilean indicator: {name}")

    # Add China PMI
    if hasattr(bundle, 'china_pmi') and bundle.china_pmi is not None:
        # Resample monthly to daily
        daily_pmi = bundle.china_pmi.resample('D').ffill() if not bundle.china_pmi.empty else bundle.china_pmi
        df['china_pmi'] = daily_pmi.reindex(df.index, method='ffill')
        logger.info("Added China PMI data")

    # Add AFP flows
    if hasattr(bundle, 'afp_flows') and bundle.afp_flows is not None:
        # Resample monthly to daily
        daily_afp = bundle.afp_flows.resample('D').ffill() if not bundle.afp_flows.empty else bundle.afp_flows
        df['afp_flows'] = daily_afp.reindex(df.index, method='ffill')
        logger.info("Added AFP flows data")

    # Add LME inventory
    if hasattr(bundle, 'lme_inventory') and bundle.lme_inventory is not None:
        df['lme_inventory'] = bundle.lme_inventory.reindex(df.index, method='ffill')
        logger.info("Added LME inventory data")

    # Take only the requested number of days
    if len(df) > days:
        df = df.iloc[-days:]

    # Drop rows with NaN in core columns
    core_cols = ['usdclp', 'copper_price', 'dxy', 'vix', 'tpm', 'fed_funds']
    existing_core = [col for col in core_cols if col in df.columns]
    df = df.dropna(subset=existing_core)

    logger.info(f"Converted DataBundle to DataFrame: {len(df)} rows, {len(df.columns)} columns")
    logger.info(f"Columns: {df.columns.tolist()}")

    return df


def _load_data_fallback(horizon: int) -> pd.DataFrame:
    """
    Fallback data loading if DataLoader is unavailable.

    Looks for CSV files in DATA_DIR:
    - usdclp_data.csv
    - copper_data.csv
    - macro_data.csv

    Returns:
        Merged DataFrame with all market data
    """
    logger.info("Using fallback data loading...")

    # Try different file patterns
    possible_files = [
        DATA_DIR / "usdclp_latest.csv",
        DATA_DIR / "usdclp_data.csv",
        DATA_DIR / "market_data.csv",
    ]

    data_file = None
    for f in possible_files:
        if f.exists():
            data_file = f
            break

    if data_file is None:
        raise FileNotFoundError(
            f"No data file found in {DATA_DIR}. "
            f"Expected one of: {[f.name for f in possible_files]}"
        )

    logger.info(f"Loading data from {data_file}")

    # Load CSV
    df = pd.read_csv(data_file)

    # Try to parse date column
    date_cols = ['date', 'Date', 'fecha', 'Fecha', 'timestamp']
    date_col = None
    for col in date_cols:
        if col in df.columns:
            date_col = col
            break

    if date_col:
        df[date_col] = pd.to_datetime(df[date_col])
        df.set_index(date_col, inplace=True)
    else:
        logger.warning("No date column found - assuming index is dates")

    # Rename columns to standard names if needed
    column_mapping = {
        'Close': 'usdclp',
        'close': 'usdclp',
        'USD_CLP': 'usdclp',
        'Copper': 'copper_price',
        'copper': 'copper_price',
        'DXY': 'dxy',
        'VIX': 'vix',
        'TPM': 'tpm',
        'tpm_rate': 'tpm',
        'fed_funds': 'fed_funds',
        'FedFunds': 'fed_funds',
    }

    df.rename(columns=column_mapping, inplace=True)

    # NOTE: 'value' column will be loaded by ensemble_forecaster from parquet
    # This ensures we use truly raw values for adaptive window calculation

    # Fill missing columns with defaults (for testing)
    if 'copper_price' not in df.columns:
        logger.warning("Copper price not found - using default value")
        df['copper_price'] = 4.0

    if 'dxy' not in df.columns:
        logger.warning("DXY not found - using default value")
        df['dxy'] = 104.0

    if 'vix' not in df.columns:
        logger.warning("VIX not found - using default value")
        df['vix'] = 15.0

    if 'tpm' not in df.columns:
        logger.warning("TPM not found - using default value")
        df['tpm'] = 5.5

    if 'fed_funds' not in df.columns:
        logger.warning("Fed Funds not found - using default value")
        df['fed_funds'] = 5.0

    # NEW: Add Chilean indicators with reasonable defaults to prevent pipeline failure
    # These will be used if Chilean data is not available in the CSV
    chilean_defaults = {
        'trade_balance': 0,      # Neutral trade balance
        'imacec_yoy': 2.5,       # Average Chilean growth rate
        'china_pmi': 50.0,       # Neutral PMI (50 = expansion/contraction line)
        'afp_flows': 0,          # No net flows
        # lme_inventory can remain missing - it's truly optional
    }

    # Try to load Chilean indicators from a separate CSV if available
    chilean_csv = DATA_DIR / "chilean_indicators.csv"
    if chilean_csv.exists():
        try:
            chilean_df = pd.read_csv(chilean_csv, index_col=0, parse_dates=True)
            # Merge Chilean data with main DataFrame
            df = df.join(chilean_df, how='left')
            logger.info(f"Loaded Chilean indicators from {chilean_csv}")
        except Exception as e:
            logger.warning(f"Failed to load Chilean indicators: {e}")

    # Apply defaults for any missing Chilean indicators
    for indicator, default_value in chilean_defaults.items():
        if indicator not in df.columns:
            logger.info(f"Adding default {indicator} = {default_value}")
            df[indicator] = default_value
        else:
            # Fill NaN values in existing columns
            if df[indicator].isna().all():
                logger.info(f"Filling empty {indicator} with default = {default_value}")
                df[indicator] = default_value
            elif df[indicator].isna().any():
                logger.info(f"Forward-filling {indicator} NaN values")
                df[indicator] = df[indicator].fillna(method='ffill').fillna(default_value)

    logger.info(f"Loaded {len(df)} rows from {data_file}")
    logger.info(f"Available columns: {df.columns.tolist()}")

    return df


# ============================================================================
# FORECASTING
# ============================================================================

def generate_forecast(
    features_df: pd.DataFrame,
    exog_df: Optional[pd.DataFrame],
    horizon_days: int,
    train_models: bool = False,
    verbose: bool = False,
) -> Tuple[EnsembleForecast, EnsembleMetrics]:
    """
    Generate ensemble forecast using XGBoost, SARIMAX, and GARCH.

    Args:
        features_df: DataFrame with engineered features
        exog_df: Exogenous variables for SARIMAX (optional)
        horizon_days: Forecast horizon (7, 15, 30, 90)
        train_models: Whether to train new models
        verbose: Enable verbose logging

    Returns:
        Tuple of (forecast, metrics)
        - forecast: EnsembleForecast object with predictions
        - metrics: Performance metrics for each model

    Raises:
        FileNotFoundError: If models not found and train_models=False
        ValueError: If training fails
    """
    if verbose:
        logger.info(f"Initializing ensemble forecaster (horizon={horizon_days}d)...")

    # Initialize ensemble with univariate SARIMAX (no exogenous variables)
    # Create custom SARIMAX config with empty exog_vars to force univariate
    from forex_core.models.sarimax_forecaster import SARIMAXConfig
    sarimax_config = SARIMAXConfig.from_horizon(horizon_days)
    sarimax_config.exog_vars = []  # Force univariate - no exogenous variables

    forecaster = EnsembleForecaster(
        horizon_days=horizon_days,
        sarimax_config=sarimax_config,
    )

    # Determine model path
    model_path = MODELS_DIR / f"ensemble_{horizon_days}d"

    # Train or load models
    # Note: SARIMAX is trained WITHOUT exogenous variables (univariate)
    # This is because we cannot forecast future values of copper, DXY, VIX, TPM
    # SARIMAX is excellent at capturing trend/seasonality from USD/CLP itself
    metrics = None
    if train_models:
        logger.info("Training new ensemble models...")
        logger.info("SARIMAX will be univariate (no exogenous variables)")
        metrics = forecaster.train(
            data=features_df,
            target_col='usdclp',
            exog_data=None,  # No exogenous variables for SARIMAX
        )
        logger.info(f"Training complete. Metrics: {metrics}")
    else:
        # Try to load existing models
        try:
            forecaster.load_models(model_path)
            logger.info("Loaded existing models")
        except FileNotFoundError:
            logger.warning("Models not found - training new models...")
            logger.info("SARIMAX will be univariate (no exogenous variables)")
            metrics = forecaster.train(
                data=features_df,
                target_col='usdclp',
                exog_data=None,  # No exogenous variables for SARIMAX
            )

    # Generate forecast
    if verbose:
        logger.info("Generating ensemble forecast...")

    forecast = forecaster.predict(
        data=features_df,
        exog_forecast=None,  # No exogenous forecast needed
    )

    logger.info(
        f"Forecast generated: {horizon_days} days, "
        f"Point estimate: {forecast.ensemble_forecast[-1]:.2f} CLP"
    )

    return forecast, metrics


# ============================================================================
# MARKET SHOCK DETECTION
# ============================================================================

def detect_market_shocks(
    forecast: EnsembleForecast,
    features_df: pd.DataFrame,
    horizon_days: int,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Detect potential market shocks and anomalies.

    Args:
        forecast: Ensemble forecast results
        features_df: DataFrame with current market data
        horizon_days: Forecast horizon
        verbose: Enable verbose logging

    Returns:
        Dictionary with:
        - alerts: List of detected alerts
        - severity: Overall severity (LOW, MEDIUM, HIGH, CRITICAL)
        - summary: Text summary of market conditions
        - should_alert: Boolean indicating if email alert needed
    """
    if verbose:
        logger.info("Analyzing market conditions for shocks...")

    detector = MarketShockDetector()

    # Detect shocks using the features DataFrame
    # MarketShockDetector.detect_all() expects a DataFrame with columns:
    # date, usdclp, copper_price, dxy, vix, tpm (optional)
    # Reset index to make 'date' a column if it's currently the index
    detection_df = features_df.copy()
    if 'date' not in detection_df.columns:
        # Index is the date, reset to make it a column
        detection_df = detection_df.reset_index()
        # If reset_index created 'index' column instead of 'date', rename it
        if 'index' in detection_df.columns:
            detection_df = detection_df.rename(columns={'index': 'date'})

    alerts = detector.detect_all(detection_df)

    # Determine overall severity
    if alerts:
        max_severity = max(alert.severity for alert in alerts)
        severity_name = max_severity.name
        should_alert = max_severity >= AlertSeverity.MEDIUM
    else:
        severity_name = "NORMAL"
        should_alert = False

    # Create summary
    if alerts:
        summary_lines = [f"Detected {len(alerts)} market condition(s):"]
        for alert in alerts:
            summary_lines.append(f"  - {alert.severity.name}: {alert.message}")
        summary = "\n".join(summary_lines)
    else:
        summary = "Normal market conditions - no anomalies detected"

    logger.info(f"Market analysis: {severity_name} - {len(alerts)} alerts")

    return {
        'alerts': alerts,
        'severity': severity_name,
        'summary': summary,
        'should_alert': should_alert,
    }


# ============================================================================
# RESULTS SAVING
# ============================================================================

def save_results(
    forecast: EnsembleForecast,
    metrics: Optional[EnsembleMetrics],
    market_analysis: Dict[str, Any],
    horizon_days: int,
) -> Path:
    """
    Save forecast results to JSON and CSV files.

    Creates:
    - output/forecast_YYYYMMDD_Hd.json: Complete results
    - output/forecast_YYYYMMDD_Hd.csv: Time series data
    - output/metrics_YYYYMMDD_Hd.json: Model performance metrics (if available)

    Args:
        forecast: Ensemble forecast results
        metrics: Model performance metrics (None if models were loaded)
        market_analysis: Market shock detection results
        horizon_days: Forecast horizon

    Returns:
        Path to main results JSON file
    """
    timestamp = datetime.now().strftime("%Y%m%d")
    prefix = f"forecast_{timestamp}_{horizon_days}d"

    # Save main results (JSON)
    results = {
        'timestamp': datetime.now().isoformat(),
        'horizon_days': horizon_days,
        'forecast': {
            'point': forecast.ensemble_forecast.tolist(),
            'lower_bound': forecast.lower_2sigma.tolist(),
            'upper_bound': forecast.upper_2sigma.tolist(),
            'dates': [d.isoformat() for d in forecast.dates],
        },
        'weights': forecast.weights_used,
        'market_analysis': {
            'severity': market_analysis['severity'],
            'summary': market_analysis['summary'],
            'alert_count': len(market_analysis['alerts']),
        },
    }

    json_path = OUTPUT_DIR / f"{prefix}.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"Results saved to {json_path}")

    # Save time series (CSV)
    forecast_df = pd.DataFrame({
        'date': forecast.dates,
        'point_forecast': forecast.ensemble_forecast,
        'lower_bound': forecast.lower_2sigma,
        'upper_bound': forecast.upper_2sigma,
    })

    csv_path = OUTPUT_DIR / f"{prefix}.csv"
    forecast_df.to_csv(csv_path, index=False)

    logger.info(f"Time series saved to {csv_path}")

    # Save metrics (JSON) - only if available from training
    if metrics is not None:
        # Use to_dict() method to get all metrics as a dictionary
        metrics_dict = metrics.to_dict()

        metrics_path = OUTPUT_DIR / f"metrics_{timestamp}_{horizon_days}d.json"
        with open(metrics_path, 'w') as f:
            json.dump(metrics_dict, f, indent=2)

        logger.info(f"Metrics saved to {metrics_path}")
    else:
        logger.info("No metrics to save (models were loaded, not trained)")

    return json_path


# ============================================================================
# EMAIL DELIVERY
# ============================================================================

def send_forecast_email(
    forecast: EnsembleForecast,
    market_analysis: Dict[str, Any],
    horizon_days: int,
    test_mode: bool = False,
) -> bool:
    """
    Send forecast email using test_email_and_pdf.py script.

    Args:
        forecast: Ensemble forecast results
        market_analysis: Market shock detection results
        horizon_days: Forecast horizon
        test_mode: If True, sends to test recipients only

    Returns:
        True if email sent successfully, False otherwise
    """
    if not EMAIL_SCRIPT.exists():
        logger.error(f"Email script not found: {EMAIL_SCRIPT}")
        return False

    # Prepare data for email script
    email_data = {
        'horizon_days': horizon_days,
        'current_rate': float(forecast.ensemble_forecast[0]),
        'forecast_rate': float(forecast.ensemble_forecast[-1]),
        'lower_bound': float(forecast.lower_2sigma[-1]),
        'upper_bound': float(forecast.upper_2sigma[-1]),
        'severity': market_analysis['severity'],
        'alert_summary': market_analysis['summary'],
        'timestamp': datetime.now().isoformat(),
    }

    # Save data for email script
    email_data_path = OUTPUT_DIR / "email_data.json"
    with open(email_data_path, 'w') as f:
        json.dump(email_data, f, indent=2)

    # Step 1: Generate email HTML and PDF
    horizon_str = f"{horizon_days}d"
    generate_cmd = [
        sys.executable,
        str(EMAIL_SCRIPT),
        f"--horizon={horizon_str}",
    ]

    try:
        logger.info(f"Generating email HTML and PDF: {' '.join(generate_cmd)}")
        result = subprocess.run(generate_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"Email generation failed: {result.stderr}")
            return False

        logger.info("Email HTML and PDF generated successfully")

        # Step 2: Send email (unless in test mode)
        if not test_mode:
            send_email_script = SCRIPTS_DIR / "send_unified_email.py"
            email_html_path = OUTPUT_DIR / f"email_{horizon_str}.html"
            pdf_path = OUTPUT_DIR / f"report_{horizon_str}.pdf"

            send_cmd = [
                sys.executable,
                str(send_email_script),
                str(email_html_path),
                str(pdf_path),
            ]

            logger.info(f"Sending email: {' '.join(send_cmd)}")
            result = subprocess.run(send_cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("Email sent successfully")
                return True
            else:
                logger.error(f"Email sending failed: {result.stderr}")
                return False
        else:
            logger.info("Test mode - skipping email send")
            return True

    except Exception as e:
        logger.error(f"Failed to run email script: {e}")
        return False


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

def main():
    """
    Main workflow orchestrator.

    Executes complete forecasting pipeline:
    1. Parse arguments
    2. Load and prepare data
    3. Generate ensemble forecast
    4. Detect market shocks
    5. Save results
    6. Send email (optional)
    """
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="USD/CLP Ensemble Forecasting System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--horizon",
        type=int,
        choices=[7, 15, 30, 90],
        default=7,
        help="Forecast horizon in days (default: 7)",
    )

    parser.add_argument(
        "--train",
        action="store_true",
        help="Train new models (default: use existing)",
    )

    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Skip email delivery",
    )

    parser.add_argument(
        "--test-email",
        action="store_true",
        help="Send email to test recipients only",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.add(sys.stderr, level="INFO")

    logger.info(
        f"\n{'='*60}\n"
        f"USD/CLP Ensemble Forecast - {args.horizon} days\n"
        f"{'='*60}"
    )

    try:
        # Step 1: Load and prepare data
        logger.info("\n[1/5] Loading and preparing data...")
        features_df, exog_df = load_and_prepare_data(
            horizon_days=args.horizon,
            verbose=args.verbose,
        )

        # Check if we have sufficient data after feature engineering
        if len(features_df) < MIN_PREDICTION_DAYS:
            raise ValueError(
                f"Insufficient data after feature engineering: {len(features_df)} rows "
                f"(need >= {MIN_PREDICTION_DAYS})"
            )

        # Step 2: Generate forecast
        logger.info("\n[2/5] Generating ensemble forecast...")
        forecast, metrics = generate_forecast(
            features_df=features_df,
            exog_df=exog_df,
            horizon_days=args.horizon,
            train_models=args.train,
            verbose=args.verbose,
        )

        # Step 3: Detect market shocks
        logger.info("\n[3/5] Analyzing market conditions...")
        market_analysis = detect_market_shocks(
            forecast=forecast,
            features_df=features_df,
            horizon_days=args.horizon,
            verbose=args.verbose,
        )

        # Step 4: Save results
        logger.info("\n[4/5] Saving results...")
        results_path = save_results(
            forecast=forecast,
            metrics=metrics,
            market_analysis=market_analysis,
            horizon_days=args.horizon,
        )

        # Step 5: Send email (optional)
        if not args.no_email:
            logger.info("\n[5/5] Sending forecast email...")
            email_sent = send_forecast_email(
                forecast=forecast,
                market_analysis=market_analysis,
                horizon_days=args.horizon,
                test_mode=args.test_email,
            )

            if not email_sent:
                logger.warning("Email delivery failed - check logs")
        else:
            logger.info("\n[5/5] Skipping email delivery (--no-email)")

        # Summary
        logger.info(
            f"\n{'='*60}\n"
            f"FORECAST COMPLETE\n"
            f"{'='*60}\n"
            f"Horizon: {args.horizon} days\n"
            f"Current rate: {features_df['usdclp'].iloc[-1]:.2f} CLP\n"
            f"Forecast: {forecast.ensemble_forecast[-1]:.2f} CLP\n"
            f"Range: [{forecast.lower_2sigma[-1]:.2f}, {forecast.upper_2sigma[-1]:.2f}]\n"
            f"Market condition: {market_analysis['severity']}\n"
            f"Results: {results_path}\n"
            f"{'='*60}"
        )

        # Exit with appropriate code
        if market_analysis['should_alert']:
            sys.exit(2)  # Alert condition
        else:
            sys.exit(0)  # Success

    except Exception as e:
        logger.error(f"\n{'!'*60}")
        logger.error(f"FORECAST FAILED: {e}")
        logger.error(f"{'!'*60}")
        logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()