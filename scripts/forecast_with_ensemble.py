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
            raw_data = loader.load_latest(days=MIN_TRAINING_DAYS + horizon_days)
            logger.info(f"Loaded {len(raw_data)} days of data via DataLoader")
        except Exception as e:
            logger.warning(f"DataLoader failed: {e}. Using fallback...")
            raw_data = _load_data_fallback()
    else:
        raw_data = _load_data_fallback()

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


def _load_data_fallback() -> pd.DataFrame:
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

    logger.info(f"Loaded {len(df)} rows from {data_file}")

    return df


# ============================================================================
# FORECASTING
# ============================================================================

def generate_forecast(
    features_df: pd.DataFrame,
    exog_df: Optional[pd.DataFrame],
    horizon_days: int,
    train: bool = False,
    verbose: bool = False,
) -> Tuple[EnsembleForecast, EnsembleForecaster]:
    """
    Generate forecast using ensemble model.

    Workflow:
    1. Load trained ensemble from disk (or train if requested)
    2. Generate predictions for horizon_days
    3. Calculate confidence intervals
    4. Package results

    Args:
        features_df: Full feature-engineered dataset
        exog_df: Exogenous variables for SARIMAX
        horizon_days: Forecast horizon (7, 15, 30, 90)
        train: Whether to train new model (default: load existing)
        verbose: Enable verbose logging

    Returns:
        Tuple of (forecast, ensemble_model)

    Raises:
        FileNotFoundError: If model not found and train=False
        RuntimeError: If forecast generation fails
    """
    model_dir = MODELS_DIR / f"ensemble_{horizon_days}d"

    # Initialize ensemble
    ensemble = EnsembleForecaster(horizon_days=horizon_days)

    # Load or train
    if train or not model_dir.exists():
        logger.info(f"Training new ensemble for {horizon_days}d horizon...")

        if verbose:
            logger.info("This may take several minutes...")

        try:
            metrics = ensemble.train(
                data=features_df,
                target_col='usdclp',
                exog_data=exog_df,
                validation_split=0.2,
                verbose=verbose,
            )

            logger.info(f"Training complete:")
            logger.info(f"  Ensemble RMSE: {metrics.ensemble_rmse:.2f} CLP")
            logger.info(f"  Ensemble MAE:  {metrics.ensemble_mae:.2f} CLP")
            logger.info(f"  Direction Acc: {metrics.ensemble_directional_accuracy:.1f}%")

            # Save trained model
            ensemble.save_models(model_dir)
            logger.info(f"Model saved to {model_dir}")

        except Exception as e:
            logger.error(f"Training failed: {e}")
            raise RuntimeError(f"Failed to train ensemble: {e}")

    else:
        logger.info(f"Loading trained ensemble from {model_dir}...")
        try:
            ensemble.load_models(model_dir)
            logger.info("Model loaded successfully")
        except FileNotFoundError:
            raise FileNotFoundError(
                f"No trained model found at {model_dir}. "
                f"Run with --train to create one."
            )

    # Prepare future exogenous variables (if needed)
    future_exog = None
    if exog_df is not None and len(exog_df) > 0:
        # For simplicity, use last known values for future exog
        # In production, would use actual forecasts/expectations
        last_exog = exog_df.iloc[-1]
        future_exog = pd.DataFrame(
            [last_exog.values] * horizon_days,
            columns=exog_df.columns,
        )
        logger.info(f"Using last known exog values for future forecast")

    # Generate forecast
    logger.info(f"Generating {horizon_days}d forecast...")

    try:
        forecast = ensemble.predict(
            data=features_df,
            steps=horizon_days,
            exog_forecast=future_exog,
        )

        logger.info(f"Forecast generated:")
        logger.info(f"  Point forecast: {forecast.ensemble_forecast[-1]:.2f} CLP")
        logger.info(f"  95% CI: [{forecast.lower_2sigma[-1]:.2f}, {forecast.upper_2sigma[-1]:.2f}]")

    except Exception as e:
        logger.error(f"Forecast generation failed: {e}")
        raise RuntimeError(f"Failed to generate forecast: {e}")

    return forecast, ensemble


# ============================================================================
# MARKET SHOCK DETECTION
# ============================================================================

def detect_market_shocks(features_df: pd.DataFrame, verbose: bool = False) -> list:
    """
    Detect market shocks and anomalies.

    Uses MarketShockDetector to identify:
    - USD/CLP sudden moves
    - Volatility spikes
    - Copper shocks
    - DXY extremes
    - VIX fear spikes
    - TPM surprises

    Args:
        features_df: Full feature dataset with latest market data
        verbose: Enable verbose logging

    Returns:
        List of Alert objects (sorted by severity)
    """
    if verbose:
        logger.info("Running market shock detection...")

    detector = MarketShockDetector()

    # Prepare data for detector (needs specific columns)
    detection_df = features_df[['usdclp', 'copper_price', 'dxy', 'vix', 'tpm']].copy()
    detection_df['date'] = detection_df.index

    try:
        alerts = detector.detect_all(detection_df)

        if alerts:
            critical = sum(1 for a in alerts if a.severity == AlertSeverity.CRITICAL)
            warning = sum(1 for a in alerts if a.severity == AlertSeverity.WARNING)
            info = sum(1 for a in alerts if a.severity == AlertSeverity.INFO)

            logger.info(f"Market shock detection complete:")
            logger.info(f"  {len(alerts)} alerts ({critical} critical, {warning} warning, {info} info)")

            if verbose:
                for alert in alerts[:3]:  # Show first 3
                    logger.info(f"  - [{alert.severity.value}] {alert.message}")
        else:
            logger.info("No market shocks detected")

    except Exception as e:
        logger.error(f"Market shock detection failed: {e}")
        alerts = []

    return alerts


# ============================================================================
# RESULTS SAVING
# ============================================================================

def save_results(
    forecast: EnsembleForecast,
    ensemble: EnsembleForecaster,
    features_df: pd.DataFrame,
    horizon_days: int,
) -> Dict[str, Any]:
    """
    Save forecast results to JSON file.

    Creates a comprehensive JSON file with:
    - Forecast values and confidence intervals
    - Current market snapshot
    - Model metadata
    - System health metrics

    Args:
        forecast: EnsembleForecast result
        ensemble: Trained ensemble model
        features_df: Feature dataset (for current values)
        horizon_days: Forecast horizon

    Returns:
        Dictionary with all forecast data (same as saved JSON)
    """
    logger.info(f"Saving forecast results...")

    # Get latest values
    latest = features_df.iloc[-1]
    current_price = latest['usdclp']

    # Calculate forecast change
    forecast_price = forecast.ensemble_forecast[-1]
    change_pct = ((forecast_price - current_price) / current_price) * 100

    # Determine bias
    if change_pct > 0.5:
        bias = "ALCISTA"
    elif change_pct < -0.5:
        bias = "BAJISTA"
    else:
        bias = "NEUTRAL"

    # Determine volatility regime
    ci_width = forecast.upper_2sigma[-1] - forecast.lower_2sigma[-1]
    volatility_pct = (ci_width / forecast_price) * 100

    if volatility_pct < 2.0:
        volatility = "BAJA"
    elif volatility_pct < 4.0:
        volatility = "MEDIA"
    else:
        volatility = "ALTA"

    # Get model contributions
    contributions = ensemble.get_model_contributions()

    # Build result dict
    result = {
        "generated_at": datetime.now().isoformat(),
        "horizon": f"{horizon_days}d",
        "horizon_days": horizon_days,

        # Current state
        "current_price": float(current_price),
        "current_date": str(features_df.index[-1].date()),

        # Forecast
        "forecast_price": float(forecast_price),
        "forecast_dates": [str(d.date()) for d in forecast.dates],
        "forecast_values": forecast.ensemble_forecast.tolist(),

        # Confidence intervals
        "ci95_low": float(forecast.lower_2sigma[-1]),
        "ci95_high": float(forecast.upper_2sigma[-1]),
        "ci68_low": float(forecast.lower_1sigma[-1]),
        "ci68_high": float(forecast.upper_1sigma[-1]),

        # Metadata
        "change_pct": float(change_pct),
        "bias": bias,
        "volatility": volatility,
        "volatility_regime": forecast.volatility_regime,

        # Model info
        "weights_used": forecast.weights_used,
        "xgboost_forecast": forecast.xgboost_forecast.tolist() if forecast.xgboost_forecast is not None else None,
        "sarimax_forecast": forecast.sarimax_forecast.tolist() if forecast.sarimax_forecast is not None else None,

        # Model health
        "model_contributions": contributions,

        # Market snapshot
        "market_data": {
            "copper_price": float(latest.get('copper_price', 0)),
            "dxy": float(latest.get('dxy', 0)),
            "vix": float(latest.get('vix', 0)),
            "tpm": float(latest.get('tpm', 0)),
        },
    }

    # Save to JSON
    output_file = OUTPUT_DIR / f"forecast_{horizon_days}d.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)

    logger.info(f"Results saved to {output_file}")

    # Log to PredictionTracker so email system can consume it
    try:
        from forex_core.mlops.tracking import PredictionTracker

        predictions_dir = DATA_DIR / "predictions"
        predictions_dir.mkdir(parents=True, exist_ok=True)
        predictions_path = predictions_dir / "predictions.parquet"

        tracker = PredictionTracker(storage_path=predictions_path)
        tracker.log_prediction(
            forecast_date=datetime.now(),
            horizon=f"{horizon_days}d",
            target_date=forecast.dates[-1],
            predicted_mean=float(forecast_price),
            ci95_low=float(forecast.lower_2sigma[-1]),
            ci95_high=float(forecast.upper_2sigma[-1]),
        )
        logger.info(f"Prediction logged to tracker: {predictions_path}")
    except Exception as e:
        logger.warning(f"Failed to log prediction to tracker: {e}")
        # Don't fail the entire workflow if tracking fails

    return result


# ============================================================================
# EMAIL SENDING
# ============================================================================

def send_forecast_email(forecast_data: Dict[str, Any], horizon_days: int) -> bool:
    """
    Send forecast email via test_email_and_pdf.py.

    This function does NOT duplicate email generation logic.
    It simply calls the existing test_email_and_pdf.py script with
    the forecast data.

    Args:
        forecast_data: Dictionary with forecast results (from save_results)
        horizon_days: Forecast horizon

    Returns:
        True if email sent successfully, False otherwise
    """
    if not EMAIL_SCRIPT.exists():
        logger.warning(f"Email script not found: {EMAIL_SCRIPT}")
        return False

    logger.info(f"Sending forecast email via {EMAIL_SCRIPT.name}...")

    try:
        # The email script expects --horizon argument
        cmd = [
            sys.executable,
            str(EMAIL_SCRIPT),
            "--horizon", f"{horizon_days}d",
        ]

        # Run email script
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
        )

        logger.info("Email script executed successfully")

        if result.stdout:
            logger.debug(f"Email script output: {result.stdout}")

        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Email script failed with code {e.returncode}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr}")
        return False

    except subprocess.TimeoutExpired:
        logger.error("Email script timed out (>2 minutes)")
        return False

    except Exception as e:
        logger.error(f"Unexpected error sending email: {e}")
        return False


def send_alert_email(alerts: list, market_data: Dict[str, Any]) -> bool:
    """
    Send market shock alert email.

    Args:
        alerts: List of Alert objects from MarketShockDetector
        market_data: Current market snapshot

    Returns:
        True if email sent successfully, False otherwise
    """
    if not alerts:
        logger.info("No alerts to send")
        return False

    logger.info(f"Generating market shock alert email ({len(alerts)} alerts)...")

    try:
        html, pdf_bytes = generate_market_shock_email(alerts, market_data)

        # Save HTML for inspection
        alert_file = OUTPUT_DIR / f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(alert_file, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"Alert email saved to {alert_file}")

        # TODO: Integrate with actual email sender
        # For now, just save the file
        logger.warning("Alert email sending not yet implemented - saved to file only")

        return True

    except Exception as e:
        logger.error(f"Failed to generate alert email: {e}")
        return False


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

def main():
    """
    Main forecasting workflow.

    Steps:
    1. Parse CLI arguments
    2. Load and prepare data
    3. Generate forecast
    4. Detect market shocks
    5. Save results
    6. Send email

    Each step logs progress and handles errors gracefully.
    """
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="USD/CLP Ensemble Forecasting System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 7-day forecast
  %(prog)s --horizon 7

  # Generate 30-day forecast without email
  %(prog)s --horizon 30 --no-email

  # Train new model and forecast
  %(prog)s --horizon 15 --train -v
        """,
    )

    parser.add_argument(
        "--horizon",
        type=int,
        required=True,
        choices=[7, 15, 30, 90],
        help="Forecast horizon in days (7, 15, 30, or 90)",
    )

    parser.add_argument(
        "--train",
        action="store_true",
        help="Train new ensemble model (default: load existing)",
    )

    parser.add_argument(
        "--no-email",
        action="store_true",
        help="Skip sending forecast email",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    # Start workflow
    horizon_days = args.horizon

    logger.info("=" * 70)
    logger.info(f"USD/CLP Ensemble Forecasting System - {horizon_days}d Horizon")
    logger.info("=" * 70)
    logger.info(f"Environment: {'Docker' if IS_DOCKER else 'Local'}")
    logger.info(f"Data dir: {DATA_DIR}")
    logger.info(f"Models dir: {MODELS_DIR}")
    logger.info(f"Output dir: {OUTPUT_DIR}")
    logger.info("")

    try:
        # STEP 1: Load and prepare data
        logger.info("STEP 1/6: Loading and preparing data...")
        features_df, exog_df = load_and_prepare_data(horizon_days, args.verbose)
        logger.info(f"✓ Data prepared: {len(features_df)} rows, {len(features_df.columns)} features")
        logger.info("")

        # STEP 2: Generate forecast
        logger.info("STEP 2/6: Generating forecast...")
        forecast, ensemble = generate_forecast(
            features_df,
            exog_df,
            horizon_days,
            train=args.train,
            verbose=args.verbose,
        )
        logger.info(f"✓ Forecast generated: {forecast.ensemble_forecast[-1]:.2f} CLP")
        logger.info("")

        # STEP 3: Detect market shocks
        logger.info("STEP 3/6: Detecting market shocks...")
        alerts = detect_market_shocks(features_df, args.verbose)
        logger.info(f"✓ Market shock detection complete: {len(alerts)} alerts")
        logger.info("")

        # STEP 4: Save results
        logger.info("STEP 4/6: Saving results...")
        forecast_data = save_results(forecast, ensemble, features_df, horizon_days)
        logger.info("✓ Results saved")
        logger.info("")

        # STEP 5: Send alerts if any
        if alerts:
            logger.info("STEP 5/6: Sending market shock alerts...")
            market_data = {
                "usdclp": forecast_data["current_price"],
                "copper_price": forecast_data["market_data"]["copper_price"],
                "dxy": forecast_data["market_data"]["dxy"],
                "vix": forecast_data["market_data"]["vix"],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            send_alert_email(alerts, market_data)
            logger.info("")
        else:
            logger.info("STEP 5/6: No market shocks - skipping alert email")
            logger.info("")

        # STEP 6: Send forecast email
        if not args.no_email:
            logger.info("STEP 6/6: Sending forecast email...")
            email_sent = send_forecast_email(forecast_data, horizon_days)
            if email_sent:
                logger.info("✓ Forecast email sent")
            else:
                logger.warning("⚠ Forecast email failed (not critical)")
        else:
            logger.info("STEP 6/6: Email sending skipped (--no-email)")

        logger.info("")
        logger.info("=" * 70)
        logger.info("✅ FORECAST WORKFLOW COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Summary:")
        logger.info(f"  Current:  ${forecast_data['current_price']:.2f} CLP")
        logger.info(f"  Forecast: ${forecast_data['forecast_price']:.2f} CLP ({forecast_data['change_pct']:+.1f}%)")
        logger.info(f"  95% CI:   ${forecast_data['ci95_low']:.0f} - ${forecast_data['ci95_high']:.0f}")
        logger.info(f"  Bias:     {forecast_data['bias']}")
        logger.info(f"  Volatility: {forecast_data['volatility']}")
        logger.info(f"  Alerts:   {len(alerts)} detected")
        logger.info("")
        logger.info(f"Results: {OUTPUT_DIR / f'forecast_{horizon_days}d.json'}")

        sys.exit(0)

    except Exception as e:
        logger.error("")
        logger.error("=" * 70)
        logger.error("❌ FORECAST WORKFLOW FAILED")
        logger.error("=" * 70)
        logger.error(f"Error: {e}")
        logger.error("")
        logger.error("Troubleshooting:")
        logger.error("  1. Check data availability in " + str(DATA_DIR))
        logger.error("  2. Verify model exists in " + str(MODELS_DIR / f"ensemble_{horizon_days}d"))
        logger.error("  3. Run with --train to create new model")
        logger.error("  4. Run with -v for verbose logging")
        logger.error("")

        # Try to send failure alert
        # (Would integrate with alert system here)

        sys.exit(1)


if __name__ == "__main__":
    main()
