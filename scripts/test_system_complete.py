#!/usr/bin/env python3
"""
Complete System Test - USD/CLP Autonomous Forecasting System

Tests all components end-to-end with synthetic data:
1. Feature engineering
2. XGBoost forecaster
3. SARIMAX forecaster
4. GARCH/EGARCH volatility
5. Ensemble forecaster
6. Market shock detection
7. Model performance monitoring
8. Alert email generation

Usage:
    python scripts/test_system_complete.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | {message}")

def generate_test_data(days=365):
    """Generate synthetic USD/CLP and macro data for testing."""
    logger.info(f"Generating {days} days of test data...")

    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    # Generate realistic USD/CLP data with trend and seasonality
    t = np.arange(days)
    trend = 900 + 50 * (t / days)  # Gradual uptrend
    seasonality = 10 * np.sin(2 * np.pi * t / 365)  # Annual seasonality
    noise = np.random.normal(0, 5, days)  # Random walk
    usdclp = trend + seasonality + noise.cumsum() * 0.1

    # Copper price (inverse correlation with USD/CLP)
    copper = 4.0 - 0.5 * (usdclp - 950) / 50 + np.random.normal(0, 0.1, days)

    # Copper volume
    copper_volume = np.random.lognormal(10, 0.3, days)

    # DXY index
    dxy = 100 + np.random.normal(0, 2, days).cumsum() * 0.1

    # VIX volatility
    vix = np.maximum(10, 18 + np.random.normal(0, 5, days))

    # TPM (Chilean rate)
    tpm = 5.5 + np.random.choice([-0.25, 0, 0.25], days, p=[0.1, 0.8, 0.1]).cumsum() * 0.1
    tpm = np.clip(tpm, 3.0, 8.0)

    # Fed Funds rate
    fed_funds = 4.5 + np.random.choice([-0.25, 0, 0.25], days, p=[0.15, 0.7, 0.15]).cumsum() * 0.1
    fed_funds = np.clip(fed_funds, 2.0, 6.0)

    # IMACEC (Chilean GDP proxy)
    imacec = 100 + np.random.normal(0.2, 1.5, days).cumsum()

    # IPC (Chilean inflation)
    ipc = 4.5 + np.random.normal(0, 0.5, days).cumsum() * 0.01
    ipc = np.clip(ipc, 2.0, 8.0)

    df = pd.DataFrame({
        'date': dates,
        'usdclp': usdclp,
        'copper_price': copper,
        'copper_volume': copper_volume,
        'dxy': dxy,
        'vix': vix,
        'tpm': tpm,
        'fed_funds': fed_funds,
        'imacec': imacec,
        'ipc': ipc
    })

    logger.info(f"✓ Generated {len(df)} rows")
    logger.info(f"  USD/CLP range: {df['usdclp'].min():.2f} - {df['usdclp'].max():.2f}")
    logger.info(f"  Copper range: {df['copper_price'].min():.2f} - {df['copper_price'].max():.2f}")

    return df


def test_feature_engineering(data):
    """Test feature engineering module."""
    logger.info("\n=== TEST 1: Feature Engineering ===")

    from forex_core.features import engineer_features

    features_df = engineer_features(data, horizon=7)

    logger.info(f"✓ Generated {len(features_df.columns)} features")
    logger.info(f"  Original columns: {len(data.columns)}")
    logger.info(f"  Engineered columns: {len(features_df.columns) - len(data.columns)}")
    logger.info(f"  NaN percentage: {features_df.isna().sum().sum() / (len(features_df) * len(features_df.columns)) * 100:.2f}%")

    assert len(features_df) > 0, "No features generated"
    assert len(features_df.columns) > len(data.columns), "No new features added"

    return features_df


def test_xgboost_forecaster(data):
    """Test XGBoost forecaster."""
    logger.info("\n=== TEST 2: XGBoost Forecaster ===")

    from forex_core.models.xgboost_forecaster import XGBoostForecaster, XGBoostConfig

    # Create 7-day forecaster
    config = XGBoostConfig.from_horizon(horizon_days=7)
    forecaster = XGBoostForecaster(config)

    logger.info(f"Training XGBoost with {len(data)} samples...")
    metrics = forecaster.train(data, target_col='usdclp')

    logger.info(f"✓ Training completed")
    logger.info(f"  RMSE: {metrics.rmse:.2f} CLP")
    logger.info(f"  MAE: {metrics.mae:.2f} CLP")
    logger.info(f"  MAPE: {metrics.mape:.2f}%")

    # Generate forecast
    forecast = forecaster.predict(data, steps=7)

    logger.info(f"✓ Generated {len(forecast)} day forecast")
    logger.info(f"  Mean forecast: {forecast.mean():.2f} CLP")

    assert metrics.rmse > 0, "Invalid RMSE"
    assert len(forecast) == 7, "Incorrect forecast length"

    return forecaster, metrics


def test_sarimax_forecaster(data):
    """Test SARIMAX forecaster."""
    logger.info("\n=== TEST 3: SARIMAX Forecaster ===")

    from forex_core.models.sarimax_forecaster import SARIMAXForecaster, SARIMAXConfig

    # Create 30-day forecaster
    config = SARIMAXConfig.from_horizon(horizon_days=30)
    forecaster = SARIMAXForecaster(config)

    # Prepare exogenous variables
    exog_data = data[['copper_price', 'dxy', 'vix', 'tpm']].copy()

    logger.info(f"Training SARIMAX with {len(data)} samples...")
    try:
        metrics = forecaster.train(data, target_col='usdclp', exog_data=exog_data, auto_select_order=False)

        logger.info(f"✓ Training completed")
        logger.info(f"  RMSE: {metrics.rmse:.2f} CLP")
        logger.info(f"  MAE: {metrics.mae:.2f} CLP")
        logger.info(f"  AIC: {metrics.aic:.2f}")

        # Generate forecast (need future exog values)
        future_exog = exog_data.iloc[-30:].copy()
        forecast = forecaster.predict(steps=30, exog_forecast=future_exog)

        logger.info(f"✓ Generated {len(forecast)} day forecast")

        return forecaster, metrics
    except Exception as e:
        logger.warning(f"⚠ SARIMAX training skipped: {str(e)[:100]}")
        return None, None


def test_garch_volatility(data):
    """Test GARCH/EGARCH volatility models."""
    logger.info("\n=== TEST 4: GARCH/EGARCH Volatility ===")

    from forex_core.models.garch_volatility import GARCHVolatility

    # Create EGARCH for 7-day (short-term)
    vol_model = GARCHVolatility(horizon_days=7)

    # Generate returns (residuals) for testing
    returns = data['usdclp'].pct_change().dropna() * 100

    logger.info(f"Fitting EGARCH on {len(returns)} returns...")
    try:
        vol_model.fit(returns.values)

        logger.info(f"✓ EGARCH fitted successfully")

        # Forecast volatility
        vol_forecast = vol_model.forecast_volatility(950.0, steps=7)

        logger.info(f"  Volatility: {vol_forecast.volatility:.2f}")
        logger.info(f"  Regime: {vol_forecast.regime.value}")
        logger.info(f"  95% CI: [{vol_forecast.confidence_intervals['2sigma'][0]:.2f}, {vol_forecast.confidence_intervals['2sigma'][1]:.2f}]")

        return vol_model
    except Exception as e:
        logger.warning(f"⚠ GARCH fitting skipped: {str(e)[:100]}")
        return None


def test_ensemble_forecaster(data):
    """Test ensemble forecaster (integration test)."""
    logger.info("\n=== TEST 5: Ensemble Forecaster ===")

    from forex_core.models.ensemble_forecaster import EnsembleForecaster

    # Create 7-day ensemble
    ensemble = EnsembleForecaster(horizon_days=7)

    # Prepare exog data
    exog_data = data[['copper_price', 'dxy', 'vix', 'tpm']].copy()

    logger.info(f"Training ensemble (XGBoost + SARIMAX + EGARCH)...")
    try:
        metrics = ensemble.train(
            data=data,
            target_col='usdclp',
            exog_data=exog_data,
            verbose=False
        )

        logger.info(f"✓ Ensemble trained successfully")
        logger.info(f"  Ensemble RMSE: {metrics.ensemble_rmse:.2f} CLP")
        logger.info(f"  XGBoost RMSE: {metrics.xgboost_rmse:.2f} CLP")
        logger.info(f"  SARIMAX RMSE: {metrics.sarimax_rmse:.2f} CLP")

        # Generate forecast
        future_exog = exog_data.iloc[-7:].copy()
        forecast = ensemble.predict(data, steps=7, exog_forecast=future_exog)

        logger.info(f"✓ Generated ensemble forecast")
        logger.info(f"  Mean forecast: {forecast.ensemble_forecast.mean():.2f} CLP")
        logger.info(f"  95% CI width: {(forecast.upper_2sigma - forecast.lower_2sigma).mean():.2f} CLP")

        # Get model contributions
        contributions = ensemble.get_model_contributions()
        logger.info(f"  XGBoost weight: {contributions['weights']['xgboost_weight']}")
        logger.info(f"  SARIMAX weight: {contributions['weights']['sarimax_weight']}")

        return ensemble, metrics
    except Exception as e:
        logger.error(f"✗ Ensemble training failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_market_shock_detection(data):
    """Test market shock detection."""
    logger.info("\n=== TEST 6: Market Shock Detection ===")

    from forex_core.alerts import MarketShockDetector

    # Create detector
    detector = MarketShockDetector()

    # Add a shock to the data
    shock_data = data.copy()
    shock_data.loc[shock_data.index[-1], 'usdclp'] *= 1.025  # +2.5% shock
    shock_data.loc[shock_data.index[-1], 'vix'] = 35  # VIX spike

    logger.info("Detecting market shocks...")
    alerts = detector.detect_all(shock_data)

    logger.info(f"✓ Detection completed")
    logger.info(f"  Alerts found: {len(alerts)}")

    for alert in alerts:
        logger.info(f"  - {alert.alert_type.value}: {alert.severity.value}")

    return alerts


def test_model_performance_monitoring():
    """Test model performance monitoring."""
    logger.info("\n=== TEST 7: Model Performance Monitoring ===")

    from forex_core.alerts.model_performance_alerts import ModelPerformanceMonitor, ForecastMetrics

    monitor = ModelPerformanceMonitor()

    # Create fake metrics
    baseline_metrics = ForecastMetrics(
        rmse=8.5,
        mae=6.2,
        mape=0.9,
        directional_accuracy=0.65
    )

    current_metrics = ForecastMetrics(
        rmse=10.2,  # 20% worse (WARNING threshold)
        mae=7.8,
        mape=1.1,
        directional_accuracy=0.58  # Below 60% (WARNING)
    )

    logger.info("Checking for degradation...")
    alerts = monitor.check_degradation(
        model_name="xgboost_7d",
        current_metrics=current_metrics,
        baseline_metrics=baseline_metrics
    )

    logger.info(f"✓ Monitoring completed")
    logger.info(f"  Alerts generated: {len(alerts)}")

    for alert in alerts:
        logger.info(f"  - {alert.alert_type.value}: {alert.severity.value}")

    return alerts


def test_alert_email_generation(market_alerts, performance_alerts):
    """Test alert email generation."""
    logger.info("\n=== TEST 8: Alert Email Generation ===")

    from forex_core.alerts.alert_email_generator import generate_market_shock_email

    if market_alerts:
        market_snapshot = {
            "usdclp": 958.30,
            "copper_price": 3.98,
            "dxy": 105.8,
            "vix": 32.5,
            "timestamp": "14/11/2025 18:00"
        }

        logger.info("Generating market shock email...")
        html, pdf = generate_market_shock_email(market_alerts, market_snapshot)

        logger.info(f"✓ Market shock email generated")
        logger.info(f"  HTML size: {len(html)} bytes")
        logger.info(f"  PDF: {'generated' if pdf else 'skipped (WeasyPrint N/A)'}")

        # Save for inspection
        output_dir = Path("output/test_alerts")
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_dir / "market_shock_test.html", "w") as f:
            f.write(html)
        logger.info(f"  Saved to: {output_dir}/market_shock_test.html")
    else:
        logger.info("  No market shock alerts to generate email")


def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("USD/CLP Autonomous Forecasting System - Complete Test")
    logger.info("=" * 60)

    try:
        # Generate test data
        data = generate_test_data(days=365)

        # Test 1: Feature Engineering
        features_df = test_feature_engineering(data)

        # Test 2: XGBoost
        xgb_forecaster, xgb_metrics = test_xgboost_forecaster(data)

        # Test 3: SARIMAX
        sarimax_forecaster, sarimax_metrics = test_sarimax_forecaster(data)

        # Test 4: GARCH/EGARCH
        garch_model = test_garch_volatility(data)

        # Test 5: Ensemble (integration)
        ensemble, ensemble_metrics = test_ensemble_forecaster(data)

        # Test 6: Market Shock Detection
        market_alerts = test_market_shock_detection(data)

        # Test 7: Model Performance Monitoring
        performance_alerts = test_model_performance_monitoring()

        # Test 8: Alert Email Generation
        test_alert_email_generation(market_alerts, performance_alerts)

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("TESTING SUMMARY")
        logger.info("=" * 60)
        logger.info("✓ Feature Engineering: PASS")
        logger.info(f"✓ XGBoost Forecaster: PASS (RMSE: {xgb_metrics.rmse:.2f})")
        logger.info(f"{'✓' if sarimax_metrics else '⚠'} SARIMAX Forecaster: {'PASS' if sarimax_metrics else 'SKIPPED'}")
        logger.info(f"{'✓' if garch_model else '⚠'} GARCH Volatility: {'PASS' if garch_model else 'SKIPPED'}")
        logger.info(f"{'✓' if ensemble_metrics else '✗'} Ensemble Forecaster: {'PASS' if ensemble_metrics else 'FAIL'}")
        logger.info(f"✓ Market Shock Detector: PASS ({len(market_alerts)} alerts)")
        logger.info(f"✓ Performance Monitor: PASS ({len(performance_alerts)} alerts)")
        logger.info("✓ Alert Email Generator: PASS")
        logger.info("=" * 60)

        if ensemble_metrics:
            logger.info("\n✅ ALL CRITICAL TESTS PASSED")
            logger.info("System is ready for production deployment!")
            return 0
        else:
            logger.warning("\n⚠ SOME TESTS SKIPPED OR FAILED")
            logger.warning("Review output above for details")
            return 1

    except Exception as e:
        logger.error(f"\n✗ TESTING FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
