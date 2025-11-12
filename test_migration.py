#!/usr/bin/env python3
"""
Test script to verify Phase 1 migration.

This script tests all migrated utilities to ensure they work correctly.
Run from project root: python test_migration.py
"""

import sys
from pathlib import Path

# Add src to path for testing
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

print("=" * 60)
print("FOREX_CORE PHASE 1 MIGRATION TEST")
print("=" * 60)


def test_imports():
    """Test that all modules can be imported."""
    print("\n[1/5] Testing imports...")

    try:
        from forex_core import __version__
        from forex_core.config import Settings, get_settings
        from forex_core.config import (
            CHILE_GMT_OFFSET,
            DEFAULT_RECIPIENTS,
            HISTORICAL_LOOKBACK_DAYS_12M,
            HISTORICAL_LOOKBACK_DAYS_7D,
            LOCAL_TZ,
            PROJECTION_DAYS,
            PROJECTION_MONTHS,
            TECH_LOOKBACK_DAYS_12M,
            TECH_LOOKBACK_DAYS_7D,
            VOL_LOOKBACK_DAYS_12M,
            VOL_LOOKBACK_DAYS_7D,
            get_base_prompt,
        )
        from forex_core.utils import (
            chunk,
            configure_logging,
            dump_json,
            ensure_parent,
            format_decimal,
            load_json,
            logger,
            percent_change,
            sanitize_filename,
            timestamp_now,
            to_markdown_table,
            word_count,
        )

        print(f"   ✓ forex_core version: {__version__}")
        print("   ✓ All imports successful!")
        return True
    except ImportError as e:
        print(f"   ✗ Import failed: {e}")
        return False


def test_logging():
    """Test logging utilities."""
    print("\n[2/5] Testing logging...")

    try:
        from forex_core.utils import configure_logging, logger

        # Configure with console only (no file for testing)
        configure_logging(level="INFO")
        logger.info("Test log message")
        logger.debug("This should not appear (level=INFO)")

        print("   ✓ Logging configured successfully!")
        return True
    except Exception as e:
        print(f"   ✗ Logging test failed: {e}")
        return False


def test_config():
    """Test configuration loading."""
    print("\n[3/5] Testing configuration...")

    try:
        from forex_core.config import get_settings

        settings = get_settings()

        assert settings.environment is not None
        assert settings.data_dir == Path("./data")
        assert settings.cache_ttl_minutes == 30
        assert isinstance(settings.email_recipients, list)
        assert len(settings.email_recipients) >= 2

        print(f"   ✓ Environment: {settings.environment}")
        print(f"   ✓ Data dir: {settings.data_dir}")
        print(f"   ✓ Email recipients: {len(settings.email_recipients)}")
        print("   ✓ Configuration loaded successfully!")
        return True
    except Exception as e:
        print(f"   ✗ Configuration test failed: {e}")
        return False


def test_constants():
    """Test constants."""
    print("\n[4/5] Testing constants...")

    try:
        from forex_core.config import (
            HISTORICAL_LOOKBACK_DAYS_12M,
            HISTORICAL_LOOKBACK_DAYS_7D,
            PROJECTION_DAYS,
            PROJECTION_MONTHS,
            get_base_prompt,
        )

        # Test 7-day constants
        assert PROJECTION_DAYS == 7
        assert HISTORICAL_LOOKBACK_DAYS_7D == 120

        # Test 12-month constants
        assert PROJECTION_MONTHS == 12
        assert HISTORICAL_LOOKBACK_DAYS_12M == 365 * 3

        # Test prompt function
        prompt_7d = get_base_prompt("7d")
        prompt_12m = get_base_prompt("12m")
        assert "7 días" in prompt_7d
        assert "12 meses" in prompt_12m

        print(f"   ✓ PROJECTION_DAYS = {PROJECTION_DAYS}")
        print(f"   ✓ PROJECTION_MONTHS = {PROJECTION_MONTHS}")
        print(f"   ✓ 7D lookback = {HISTORICAL_LOOKBACK_DAYS_7D} days")
        print(f"   ✓ 12M lookback = {HISTORICAL_LOOKBACK_DAYS_12M} days")
        print("   ✓ Base prompts working!")
        print("   ✓ Constants validated successfully!")
        return True
    except Exception as e:
        print(f"   ✗ Constants test failed: {e}")
        return False


def test_helpers():
    """Test helper utilities."""
    print("\n[5/5] Testing helper functions...")

    try:
        from forex_core.utils import (
            chunk,
            dump_json,
            format_decimal,
            load_json,
            percent_change,
            sanitize_filename,
            word_count,
        )

        # Test percent_change
        assert percent_change(110, 100) == 10.0
        assert percent_change(90, 100) == -10.0
        assert percent_change(100, 0) == 0.0

        # Test format_decimal
        assert format_decimal(3.14159, 2) == 3.14
        assert format_decimal(3.14159, 4) == 3.1416

        # Test sanitize_filename
        assert sanitize_filename("USD/CLP Forecast 2025!") == "usd-clp-forecast-2025"

        # Test word_count
        assert word_count("The quick brown fox") == 4

        # Test chunk
        assert list(chunk([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]

        # Test JSON operations
        test_path = project_root / "test_output.json"
        test_data = {"test": 123, "values": [1, 2, 3]}
        dump_json(test_path, test_data)
        loaded = load_json(test_path)
        assert loaded == test_data
        test_path.unlink()  # Cleanup

        print("   ✓ percent_change() working")
        print("   ✓ format_decimal() working")
        print("   ✓ sanitize_filename() working")
        print("   ✓ word_count() working")
        print("   ✓ chunk() working")
        print("   ✓ JSON operations working")
        print("   ✓ All helpers validated successfully!")
        return True
    except Exception as e:
        print(f"   ✗ Helpers test failed: {e}")
        return False


def main():
    """Run all tests."""
    results = [
        test_imports(),
        test_logging(),
        test_config(),
        test_constants(),
        test_helpers(),
    ]

    print("\n" + "=" * 60)
    if all(results):
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nPhase 1 migration successful!")
        print("Ready to proceed to Phase 2: Data Layer Migration")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 60)
        print("\nPlease review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
