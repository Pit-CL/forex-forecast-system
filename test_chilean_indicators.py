#!/usr/bin/env python3
"""
Test script for Chilean economic indicators integration.

Tests the new data providers and feature engineering for:
- Banco Central de Chile (BCCh) data
- China PMI (copper demand proxy)
- AFP pension fund flows
- LME copper inventory
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger
import pandas as pd

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")

def test_bcentral_provider():
    """Test Banco Central de Chile provider."""
    logger.info("Testing Banco Central provider...")

    try:
        from src.forex_core.data.providers.bcentral import BancoCentralProvider

        provider = BancoCentralProvider()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        # Test trade balance
        logger.info("Fetching trade balance...")
        trade_balance = provider.get_trade_balance(start_date, end_date)
        if not trade_balance.empty:
            logger.success(f"Trade balance: {len(trade_balance)} observations")
            logger.info(f"Latest: {trade_balance.iloc[-1]:.0f} million CLP")
        else:
            logger.warning("No trade balance data retrieved")

        # Test IMACEC
        logger.info("Fetching IMACEC YoY...")
        imacec = provider.get_imacec_yoy(start_date, end_date)
        if not imacec.empty:
            logger.success(f"IMACEC YoY: {len(imacec)} observations")
            logger.info(f"Latest: {imacec.iloc[-1]:.1f}%")
        else:
            logger.warning("No IMACEC data retrieved")

        return True

    except Exception as e:
        logger.error(f"BCCh provider test failed: {e}")
        return False


def test_china_pmi_provider():
    """Test China PMI provider."""
    logger.info("Testing China PMI provider...")

    try:
        from src.forex_core.data.providers.china_indicators import ChinaPMIProvider
        from src.forex_core.config import get_settings

        settings = get_settings()
        if not settings.fred_api_key or settings.fred_api_key == "your_fred_api_key_here":
            logger.warning("FRED API key not configured - skipping China PMI test")
            return True

        provider = ChinaPMIProvider(settings.fred_api_key)

        # Test manufacturing PMI
        logger.info("Fetching China Manufacturing PMI...")
        pmi = provider.get_manufacturing_pmi()
        if not pmi.empty:
            logger.success(f"China PMI: {len(pmi)} observations")
            logger.info(f"Latest: {pmi.iloc[-1]:.1f} ({'Expansion' if pmi.iloc[-1] > 50 else 'Contraction'})")
        else:
            logger.warning("No China PMI data retrieved")

        return True

    except Exception as e:
        logger.error(f"China PMI provider test failed: {e}")
        return False


def test_afp_flows_provider():
    """Test AFP flows provider."""
    logger.info("Testing AFP flows provider...")

    try:
        from src.forex_core.data.providers.afp_flows import AFPFlowProvider

        provider = AFPFlowProvider()

        # Test net international flows
        logger.info("Fetching AFP net international flows...")
        flows = provider.get_net_international_flows()
        if not flows.empty:
            logger.success(f"AFP flows: {len(flows)} observations")
            logger.info(f"Latest: ${flows.iloc[-1]:.0f}M USD")
        else:
            logger.warning("No AFP flow data retrieved")

        # Test foreign investment percentage
        foreign_pct = provider.get_foreign_investment_percentage()
        if foreign_pct > 0:
            logger.info(f"Foreign investment: {foreign_pct:.1f}%")

        return True

    except Exception as e:
        logger.error(f"AFP provider test failed: {e}")
        return False


def test_lme_inventory():
    """Test LME inventory data."""
    logger.info("Testing LME inventory...")

    try:
        from src.forex_core.data.providers.copper_prices import CopperPricesClient
        from src.forex_core.config import get_settings

        settings = get_settings()
        client = CopperPricesClient(settings)

        if not settings.fred_api_key or settings.fred_api_key == "your_fred_api_key_here":
            logger.warning("FRED API key not configured - skipping LME inventory test")
            return True

        # Test LME inventory
        logger.info("Fetching LME copper inventory...")
        inventory = client.get_lme_inventory()
        if not inventory.empty:
            logger.success(f"LME inventory: {len(inventory)} observations")
            logger.info(f"Latest: {inventory.iloc[-1]:,.0f} metric tons")

            # Test inventory features
            features = client.compute_inventory_features(inventory)
            if features:
                logger.info(f"Computed {len(features)} inventory features")
        else:
            logger.warning("No LME inventory data retrieved")

        return True

    except Exception as e:
        logger.error(f"LME inventory test failed: {e}")
        return False


def test_data_loader_integration():
    """Test integration with DataLoader."""
    logger.info("Testing DataLoader integration...")

    try:
        from src.forex_core.data.loader import DataLoader
        from src.forex_core.config import get_settings

        settings = get_settings()
        loader = DataLoader(settings)

        # Test loading Chilean indicators
        logger.info("Loading Chilean indicators via DataLoader...")
        chilean_indicators = loader.load_chilean_indicators()

        if chilean_indicators:
            logger.success(f"Loaded {len(chilean_indicators)} Chilean indicator series")
            for key, series in chilean_indicators.items():
                if not series.empty:
                    logger.info(f"  - {key}: {len(series)} observations")
        else:
            logger.warning("No Chilean indicators loaded")

        return True

    except Exception as e:
        logger.error(f"DataLoader integration test failed: {e}")
        return False


def test_feature_engineering():
    """Test feature engineering with Chilean indicators."""
    logger.info("Testing feature engineering with Chilean indicators...")

    try:
        from src.forex_core.features.feature_engineer import add_chilean_indicators
        import numpy as np

        # Create sample data
        dates = pd.date_range('2024-01-01', periods=100)
        df = pd.DataFrame({
            'date': dates,
            'usdclp': np.random.uniform(900, 950, 100),
            'trade_balance': [1000 if i % 30 == 0 else np.nan for i in range(100)],  # Monthly
            'imacec_yoy': [3.5 if i % 30 == 0 else np.nan for i in range(100)],  # Monthly
            'china_pmi': [51.2 if i % 30 == 0 else np.nan for i in range(100)],  # Monthly
            'afp_flows': [100 if i % 30 == 0 else np.nan for i in range(100)],  # Monthly
            'lme_inventory': np.random.uniform(200000, 300000, 100),  # Daily
        })
        df = df.set_index('date')

        # Apply Chilean indicator features
        logger.info("Applying Chilean indicator features...")
        features_df = add_chilean_indicators(df)

        # Check new features
        new_features = [col for col in features_df.columns if col not in df.columns]
        logger.success(f"Generated {len(new_features)} new features")

        # Verify key features exist
        expected_features = [
            'trade_balance_ffill',
            'imacec_yoy_ffill',
            'china_expansion',
            'afp_flows_ffill',
            'lme_inv_zscore'
        ]

        for feat in expected_features:
            if feat in features_df.columns:
                logger.info(f"  ✓ {feat}")
            else:
                logger.warning(f"  ✗ {feat} missing")

        # Check composite score
        if 'chile_composite_score' in features_df.columns:
            logger.success("Chilean composite score calculated")
            score = features_df['chile_composite_score'].dropna()
            if not score.empty:
                logger.info(f"  Latest score: {score.iloc[-1]:.3f}")

        return True

    except Exception as e:
        logger.error(f"Feature engineering test failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("CHILEAN INDICATORS INTEGRATION TEST")
    logger.info("=" * 60)

    tests = [
        ("Banco Central Provider", test_bcentral_provider),
        ("China PMI Provider", test_china_pmi_provider),
        ("AFP Flows Provider", test_afp_flows_provider),
        ("LME Inventory", test_lme_inventory),
        ("DataLoader Integration", test_data_loader_integration),
        ("Feature Engineering", test_feature_engineering),
    ]

    results = {}

    for name, test_func in tests:
        logger.info("")
        logger.info(f"Running: {name}")
        logger.info("-" * 40)

        try:
            success = test_func()
            results[name] = success
        except Exception as e:
            logger.error(f"Test crashed: {e}")
            results[name] = False

        logger.info("")

    # Summary
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, success in results.items():
        status = "✓ PASSED" if success else "✗ FAILED"
        logger.info(f"{status}: {name}")

    logger.info("")
    if passed == total:
        logger.success(f"All {total} tests passed!")
    else:
        logger.warning(f"{passed}/{total} tests passed")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)