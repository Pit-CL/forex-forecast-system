#!/usr/bin/env python3
"""
Test script for copper price integration.

This script validates that the copper data provider works correctly
and integrates properly with the DataLoader pipeline.

Usage:
    python scripts/test_copper_integration.py
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forex_core.config import get_settings
from forex_core.data import DataLoader
from forex_core.data.providers import CopperPricesClient
from loguru import logger


def test_copper_client_standalone():
    """Test CopperPricesClient in isolation."""
    logger.info("=" * 60)
    logger.info("TEST 1: CopperPricesClient Standalone")
    logger.info("=" * 60)

    settings = get_settings()
    client = CopperPricesClient(settings)

    try:
        # Test fetching series
        logger.info("Fetching 5 years of copper data...")
        series = client.fetch_series(years=5)

        logger.info(f"✓ Successfully fetched {len(series)} copper price points")
        logger.info(f"  Date range: {series.index[0]} to {series.index[-1]}")
        logger.info(f"  Price range: ${series.min():.2f} - ${series.max():.2f} USD/lb")
        logger.info(f"  Latest price: ${series.iloc[-1]:.2f} USD/lb")

        # Test computing features
        logger.info("\nComputing technical features...")
        features = client.compute_features(series)

        logger.info(f"✓ Computed {len(features)} features:")
        for name, feature_series in features.items():
            latest_value = feature_series.dropna().iloc[-1] if len(feature_series.dropna()) > 0 else float('nan')
            logger.info(f"  - {name}: {latest_value:.4f}")

        # Validate key features exist
        expected_features = [
            "copper_returns_1d",
            "copper_returns_5d",
            "copper_returns_20d",
            "copper_volatility_20d",
            "copper_volatility_60d",
            "copper_sma_20",
            "copper_sma_50",
            "copper_trend_signal",
            "copper_rsi_14",
            "copper_price_normalized",
        ]

        missing = set(expected_features) - set(features.keys())
        if missing:
            logger.error(f"✗ Missing expected features: {missing}")
            return False

        logger.info("✓ All expected features present")

        # Validate data quality
        logger.info("\nValidating data quality...")

        # Check volatility is reasonable (typically 0.1 - 0.5 for copper)
        vol_20d = features["copper_volatility_20d"].dropna()
        if len(vol_20d) > 0:
            avg_vol = vol_20d.mean()
            if 0.05 < avg_vol < 1.0:
                logger.info(f"✓ Volatility in reasonable range: {avg_vol:.3f}")
            else:
                logger.warning(f"⚠ Volatility seems unusual: {avg_vol:.3f}")

        # Check RSI is in valid range (0-100)
        rsi = features["copper_rsi_14"].dropna()
        if len(rsi) > 0:
            if rsi.min() >= 0 and rsi.max() <= 100:
                logger.info(f"✓ RSI in valid range: {rsi.min():.1f} - {rsi.max():.1f}")
            else:
                logger.error(f"✗ RSI out of range: {rsi.min():.1f} - {rsi.max():.1f}")
                return False

        logger.info("\n✓ TEST 1 PASSED\n")
        return True

    except Exception as e:
        logger.error(f"✗ TEST 1 FAILED: {e}")
        logger.exception("Detailed error:")
        return False


def test_dataloader_integration():
    """Test copper integration in full DataLoader pipeline."""
    logger.info("=" * 60)
    logger.info("TEST 2: DataLoader Integration")
    logger.info("=" * 60)

    settings = get_settings()
    loader = DataLoader(settings)

    try:
        logger.info("Loading full data bundle...")
        bundle = loader.load()

        logger.info(f"✓ Data bundle loaded with {len(bundle.sources)} sources")

        # Check copper series exists
        if bundle.copper_series is None or len(bundle.copper_series) == 0:
            logger.error("✗ Copper series is empty or None")
            return False

        logger.info(f"✓ Copper series loaded: {len(bundle.copper_series)} points")

        # Check copper indicator
        if "copper" not in bundle.indicators:
            logger.error("✗ Copper indicator not in bundle.indicators")
            return False

        copper_indicator = bundle.indicators["copper"]
        logger.info(f"✓ Copper indicator: ${copper_indicator.value:.2f} {copper_indicator.unit}")

        # Check copper features
        if bundle.copper_features is None:
            logger.warning("⚠ Copper features are None (may be expected if computation failed)")
        else:
            logger.info(f"✓ Copper features loaded: {len(bundle.copper_features)} features")

            # Print sample features
            logger.info("\nSample copper features:")
            sample_features = [
                "copper_volatility_20d",
                "copper_rsi_14",
                "copper_trend_signal",
            ]

            for feat_name in sample_features:
                if feat_name in bundle.copper_features:
                    feat_series = bundle.copper_features[feat_name]
                    latest = feat_series.dropna().iloc[-1] if len(feat_series.dropna()) > 0 else float('nan')
                    logger.info(f"  {feat_name}: {latest:.4f}")

            # Check correlation with USD/CLP
            if "copper_usdclp_correlation_90d" in bundle.copper_features:
                corr_series = bundle.copper_features["copper_usdclp_correlation_90d"]
                latest_corr = corr_series.dropna().iloc[-1] if len(corr_series.dropna()) > 0 else float('nan')
                logger.info(f"\n✓ Copper-USDCLP 90d correlation: {latest_corr:.3f}")

                # Negative correlation is expected (higher copper -> stronger CLP -> lower USD/CLP)
                if latest_corr < 0:
                    logger.info("  (Negative correlation expected: higher copper → stronger CLP)")
                else:
                    logger.warning(f"  ⚠ Positive correlation unusual for copper-CLP relationship")

        logger.info("\n✓ TEST 2 PASSED\n")
        return True

    except Exception as e:
        logger.error(f"✗ TEST 2 FAILED: {e}")
        logger.exception("Detailed error:")
        return False


def test_fallback_mechanism():
    """Test that FRED fallback works if configured."""
    logger.info("=" * 60)
    logger.info("TEST 3: FRED Fallback (optional)")
    logger.info("=" * 60)

    settings = get_settings()

    if not settings.fred_api_key:
        logger.warning("⚠ FRED_API_KEY not configured, skipping fallback test")
        logger.info("  Set FRED_API_KEY in .env to test fallback capability")
        return True  # Not a failure, just skipped

    client = CopperPricesClient(settings)

    try:
        logger.info("Testing FRED backup source (force_backup=True)...")
        series = client.fetch_series(years=2, force_backup=True)

        logger.info(f"✓ FRED fallback works: {len(series)} data points")
        logger.info(f"  Latest FRED copper price: ${series.iloc[-1]:.2f} USD/lb")

        logger.info("\n✓ TEST 3 PASSED\n")
        return True

    except Exception as e:
        logger.error(f"✗ TEST 3 FAILED: {e}")
        logger.exception("Detailed error:")
        return False


def main():
    """Run all tests."""
    logger.info("\n" + "=" * 60)
    logger.info("COPPER INTEGRATION TEST SUITE")
    logger.info("=" * 60 + "\n")

    results = []

    # Test 1: Standalone client
    results.append(("CopperPricesClient Standalone", test_copper_client_standalone()))

    # Test 2: DataLoader integration
    results.append(("DataLoader Integration", test_dataloader_integration()))

    # Test 3: FRED fallback
    results.append(("FRED Fallback", test_fallback_mechanism()))

    # Summary
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {test_name}")

    logger.info("=" * 60)
    logger.info(f"TOTAL: {passed}/{total} tests passed")

    if passed == total:
        logger.info("✓ ALL TESTS PASSED")
        return 0
    else:
        logger.error("✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
