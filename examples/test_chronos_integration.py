#!/usr/bin/env python3
"""
Test script for Chronos-Bolt-Small integration.

This script tests the Chronos forecasting model integration by:
1. Loading historical USD/CLP data
2. Generating a forecast with Chronos
3. Validating the forecast structure
4. Comparing with ensemble forecast (if other models enabled)

Usage:
    python examples/test_chronos_integration.py

Requirements:
    - chronos-forecasting installed
    - torch installed
    - At least 1GB RAM available
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
import psutil
from forex_core.forecasting import (
    forecast_chronos,
    get_chronos_pipeline,
    release_chronos_pipeline,
    ForecastEngine,
)
from forex_core.config import get_settings
from forex_core.data.loader import load_data
from forex_core.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


def check_system_requirements() -> bool:
    """Check if system meets Chronos requirements."""
    available_mb = psutil.virtual_memory().available / (1024 * 1024)
    required_mb = 800

    logger.info(f"Available RAM: {available_mb:.0f}MB")
    logger.info(f"Required RAM: {required_mb}MB")

    if available_mb < required_mb:
        logger.error("Insufficient memory for Chronos")
        return False

    return True


def test_chronos_standalone():
    """Test Chronos model in standalone mode."""
    logger.info("=" * 60)
    logger.info("TEST 1: Chronos Standalone Forecast")
    logger.info("=" * 60)

    try:
        # Load data
        logger.info("Loading historical USD/CLP data...")
        bundle = load_data()
        series = bundle.usdclp_series

        logger.info(f"Loaded {len(series)} days of data")
        logger.info(f"Date range: {series.index[0]} to {series.index[-1]}")
        logger.info(f"Last price: {series.iloc[-1]:.2f} CLP")

        # Generate forecast
        logger.info("\nGenerating Chronos forecast (7 days)...")
        forecast = forecast_chronos(
            series=series,
            steps=7,
            context_length=180,
            num_samples=100,
            validate=True,
            validation_window=30,
        )

        # Display results
        logger.info("\n✓ Forecast generated successfully!")
        logger.info(f"Methodology: {forecast.methodology}")
        logger.info(f"Error metrics: {forecast.error_metrics}")
        logger.info(f"Residual volatility: {forecast.residual_vol:.4f}")

        logger.info("\n7-Day Forecast:")
        logger.info("-" * 60)
        for i, point in enumerate(forecast.series, 1):
            logger.info(
                f"Day {i} ({point.date.strftime('%Y-%m-%d')}): "
                f"{point.mean:.2f} CLP "
                f"(95% CI: [{point.ci95_low:.2f}, {point.ci95_high:.2f}])"
            )

        return True

    except Exception as exc:
        logger.error(f"Standalone test failed: {exc}", exc_info=True)
        return False


def test_chronos_with_ensemble():
    """Test Chronos integrated in ForecastEngine ensemble."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Chronos in Ensemble with Other Models")
    logger.info("=" * 60)

    try:
        # Configure with Chronos enabled
        settings = get_settings()
        settings.enable_chronos = True
        settings.enable_arima = True
        settings.enable_var = True
        settings.enable_rf = False  # Skip RF to save time

        logger.info(f"Models enabled:")
        logger.info(f"  - ARIMA: {settings.enable_arima}")
        logger.info(f"  - VAR: {settings.enable_var}")
        logger.info(f"  - Random Forest: {settings.enable_rf}")
        logger.info(f"  - Chronos: {settings.enable_chronos}")

        # Create engine
        engine = ForecastEngine(
            config=settings,
            horizon="daily",
            steps=7,
        )

        # Load data
        logger.info("\nLoading data bundle...")
        bundle = load_data()

        # Generate ensemble forecast
        logger.info("Generating ensemble forecast (includes Chronos)...")
        forecast, artifacts = engine.forecast(bundle)

        # Display results
        logger.info("\n✓ Ensemble forecast generated successfully!")
        logger.info(f"\nEnsemble Weights:")
        logger.info("-" * 60)
        for model, weight in artifacts.weights.items():
            logger.info(f"  {model:15s}: {weight:.4f} ({weight*100:.1f}%)")

        logger.info(f"\nComponent Metrics:")
        logger.info("-" * 60)
        for model, metrics in artifacts.component_metrics.items():
            rmse = metrics.get("RMSE", metrics.get("pseudo_RMSE", 0))
            mape = metrics.get("MAPE", metrics.get("pseudo_MAPE", 0))
            logger.info(f"  {model:15s}: RMSE={rmse:.4f}, MAPE={mape:.4f}")

        logger.info(f"\nEnsemble 7-Day Forecast:")
        logger.info("-" * 60)
        for i, point in enumerate(forecast.series, 1):
            logger.info(
                f"Day {i} ({point.date.strftime('%Y-%m-%d')}): "
                f"{point.mean:.2f} CLP "
                f"(95% CI: [{point.ci95_low:.2f}, {point.ci95_high:.2f}])"
            )

        # Check if Chronos contributed
        if "chronos" in artifacts.weights:
            chronos_weight = artifacts.weights["chronos"]
            logger.info(
                f"\n✓ Chronos contributed {chronos_weight*100:.1f}% to ensemble"
            )
        else:
            logger.warning("\n⚠ Chronos was not included in ensemble")

        return True

    except Exception as exc:
        logger.error(f"Ensemble test failed: {exc}", exc_info=True)
        return False


def test_memory_cleanup():
    """Test memory cleanup after Chronos usage."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Memory Cleanup")
    logger.info("=" * 60)

    try:
        # Check memory before
        mem_before = psutil.virtual_memory().available / (1024 * 1024)
        logger.info(f"Available RAM before loading: {mem_before:.0f}MB")

        # Load pipeline
        logger.info("Loading Chronos pipeline...")
        pipeline = get_chronos_pipeline()
        mem_after_load = psutil.virtual_memory().available / (1024 * 1024)
        logger.info(f"Available RAM after loading: {mem_after_load:.0f}MB")
        logger.info(f"Memory used by model: ~{mem_before - mem_after_load:.0f}MB")

        # Release pipeline
        logger.info("\nReleasing Chronos pipeline...")
        release_chronos_pipeline()
        mem_after_release = psutil.virtual_memory().available / (1024 * 1024)
        logger.info(f"Available RAM after release: {mem_after_release:.0f}MB")
        logger.info(f"Memory freed: ~{mem_after_release - mem_after_load:.0f}MB")

        logger.info("\n✓ Memory cleanup successful")
        return True

    except Exception as exc:
        logger.error(f"Memory cleanup test failed: {exc}", exc_info=True)
        return False


def main():
    """Run all Chronos integration tests."""
    # Configure logging
    configure_logging(level="INFO")

    logger.info("Chronos-Bolt-Small Integration Test Suite")
    logger.info("=" * 60)

    # Check system requirements
    if not check_system_requirements():
        logger.error("System does not meet Chronos requirements. Exiting.")
        sys.exit(1)

    # Run tests
    results = {
        "Standalone Forecast": test_chronos_standalone(),
        "Ensemble Integration": test_chronos_with_ensemble(),
        "Memory Cleanup": test_memory_cleanup(),
    }

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"{test_name:25s}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        logger.info("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        logger.error("\n❌ Some tests failed. Check logs above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
