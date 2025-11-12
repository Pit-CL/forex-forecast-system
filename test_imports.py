#!/usr/bin/env python3
"""
Test script to verify all imports work correctly.

This script tests the basic import structure without running full forecasts.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 60)
print("TESTING IMPORTS - Forex Forecast System")
print("=" * 60)

errors = []

# Test 1: Core configuration
print("\n1. Testing core configuration...")
try:
    from forex_core.config import base, constants
    print("   ✓ forex_core.config imports OK")
except Exception as e:
    errors.append(f"forex_core.config: {e}")
    print(f"   ✗ ERROR: {e}")

# Test 2: Core utilities
print("\n2. Testing core utilities...")
try:
    from forex_core.utils import logging, helpers
    print("   ✓ forex_core.utils imports OK")
except Exception as e:
    errors.append(f"forex_core.utils: {e}")
    print(f"   ✗ ERROR: {e}")

# Test 3: Data models
print("\n3. Testing data models...")
try:
    from forex_core.data import models
    print("   ✓ forex_core.data.models imports OK")
except Exception as e:
    errors.append(f"forex_core.data.models: {e}")
    print(f"   ✗ ERROR: {e}")

# Test 4: Data providers (may fail if dependencies missing)
print("\n4. Testing data providers...")
try:
    from forex_core.data.providers import base as prov_base
    print("   ✓ forex_core.data.providers.base imports OK")
except Exception as e:
    errors.append(f"forex_core.data.providers: {e}")
    print(f"   ✗ ERROR: {e}")

# Test 5: Forecasting modules
print("\n5. Testing forecasting modules...")
try:
    from forex_core.forecasting import ForecastEngine, compute_weights
    print("   ✓ forex_core.forecasting imports OK")
except Exception as e:
    errors.append(f"forex_core.forecasting: {e}")
    print(f"   ✗ ERROR: {e}")

# Test 6: Reporting modules (skip for now - needs full dependencies)
print("\n6. Testing reporting modules...")
try:
    from forex_core.reporting import ChartGenerator, ReportBuilder
    print("   ✓ forex_core.reporting imports OK")
except Exception as e:
    # This may fail if WeasyPrint/matplotlib dependencies missing
    print(f"   ⚠ WARNING: {e}")
    print("   (This is OK if system dependencies not installed)")

# Test 7: Notifications
print("\n7. Testing notifications...")
try:
    from forex_core.notifications import email
    print("   ✓ forex_core.notifications imports OK")
except Exception as e:
    errors.append(f"forex_core.notifications: {e}")
    print(f"   ✗ ERROR: {e}")

# Test 8: Services
print("\n8. Testing services...")
try:
    from services.forecaster_7d import config as config_7d
    print("   ✓ services.forecaster_7d imports OK")
except Exception as e:
    errors.append(f"services.forecaster_7d: {e}")
    print(f"   ✗ ERROR: {e}")

try:
    from services.forecaster_12m import config as config_12m
    print("   ✓ services.forecaster_12m imports OK")
except Exception as e:
    errors.append(f"services.forecaster_12m: {e}")
    print(f"   ✗ ERROR: {e}")

try:
    from services.importer_report import config as config_imp
    print("   ✓ services.importer_report imports OK")
except Exception as e:
    errors.append(f"services.importer_report: {e}")
    print(f"   ✗ ERROR: {e}")

# Summary
print("\n" + "=" * 60)
if errors:
    print(f"RESULT: {len(errors)} ERROR(S) FOUND")
    print("=" * 60)
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
else:
    print("RESULT: ALL IMPORTS SUCCESSFUL ✓")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Install dependencies: pip install -r requirements.txt")
    print("  2. Configure .env file with your credentials")
    print("  3. Run tests: make test")
    print("  4. Run services: make run-7d")
    sys.exit(0)
