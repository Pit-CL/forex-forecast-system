# Migration Quick Reference Guide

Quick reference for developers migrating from legacy systems to forex_core.

---

## Import Changes Cheat Sheet

### Logging
```python
# OLD (7d/12m)
from usdclp_forecaster.logger import logger, configure_logging
from usdclp_forecaster_12m.logger import logger, configure_logging

# NEW (unified)
from forex_core.utils import logger, configure_logging
```

### Configuration
```python
# OLD (7d/12m)
from usdclp_forecaster.config import get_settings
from usdclp_forecaster_12m.config import get_settings

# NEW (unified)
from forex_core.config import get_settings
```

### Constants - Basic
```python
# OLD (7d)
from usdclp_forecaster.constants import LOCAL_TZ, DEFAULT_RECIPIENTS

# OLD (12m)
from usdclp_forecaster_12m.constants import LOCAL_TZ, DEFAULT_RECIPIENTS

# NEW (unified - these are the same)
from forex_core.config import LOCAL_TZ, DEFAULT_RECIPIENTS, CHILE_GMT_OFFSET
```

### Constants - Horizon-Specific
```python
# OLD (7d)
from usdclp_forecaster.constants import (
    PROJECTION_DAYS,           # 7
    HISTORICAL_LOOKBACK_DAYS,  # 120
    TECH_LOOKBACK_DAYS,        # 60
    VOL_LOOKBACK_DAYS,         # 30
)

# NEW (7d specific)
from forex_core.config import (
    PROJECTION_DAYS,                 # 7
    HISTORICAL_LOOKBACK_DAYS_7D,     # 120
    TECH_LOOKBACK_DAYS_7D,           # 60
    VOL_LOOKBACK_DAYS_7D,            # 30
)

# OLD (12m)
from usdclp_forecaster_12m.constants import (
    PROJECTION_MONTHS,         # 12
    HISTORICAL_LOOKBACK_DAYS,  # 365 * 3
    TECH_LOOKBACK_DAYS,        # 120
    VOL_LOOKBACK_DAYS,         # 120
)

# NEW (12m specific)
from forex_core.config import (
    PROJECTION_MONTHS,               # 12
    HISTORICAL_LOOKBACK_DAYS_12M,    # 365 * 3
    TECH_LOOKBACK_DAYS_12M,          # 120
    VOL_LOOKBACK_DAYS_12M,           # 120
)
```

### Base Prompt (AI Analysis)
```python
# OLD (7d)
from usdclp_forecaster.constants import BASE_PROMPT

# OLD (12m)
from usdclp_forecaster_12m.constants import BASE_PROMPT

# NEW (dynamic selection)
from forex_core.config import get_base_prompt

prompt_7d = get_base_prompt("7d")    # For 7-day forecasts
prompt_12m = get_base_prompt("12m")  # For 12-month forecasts
```

### Helper Utilities
```python
# OLD (7d/12m)
from usdclp_forecaster.utils import (
    percent_change,
    format_decimal,
    dump_json,
    load_json,
    # ... etc
)

# NEW (unified)
from forex_core.utils import (
    percent_change,
    format_decimal,
    dump_json,
    load_json,
    ensure_parent,
    to_markdown_table,
    timestamp_now,
    sanitize_filename,
    word_count,
    chunk,
)
```

---

## Common Patterns

### Pattern 1: Initialize Logging
```python
# OLD
from usdclp_forecaster.logger import configure_logging, logger
configure_logging(log_path=Path("./logs/app.log"))

# NEW (same API!)
from forex_core.utils import configure_logging, logger
configure_logging(log_path=Path("./logs/app.log"))

# NEW (with enhanced options)
from forex_core.utils import configure_logging, logger
configure_logging(
    log_path=Path("./logs/app.log"),
    level="DEBUG",
    rotation="10 MB",
    retention=14,
    backtrace=True,
)
```

### Pattern 2: Load Settings
```python
# OLD
from usdclp_forecaster.config import get_settings
settings = get_settings()

# NEW (same API!)
from forex_core.config import get_settings
settings = get_settings()

# Both systems use the same Settings class
print(settings.data_dir)
print(settings.fred_api_key)
print(settings.email_recipients)
```

### Pattern 3: Get Forecast Horizon Config
```python
# NEW: For 7-day forecast service
from forex_core.config import (
    PROJECTION_DAYS,
    HISTORICAL_LOOKBACK_DAYS_7D,
    TECH_LOOKBACK_DAYS_7D,
    VOL_LOOKBACK_DAYS_7D,
    get_base_prompt,
)

forecast_days = PROJECTION_DAYS
lookback = HISTORICAL_LOOKBACK_DAYS_7D
prompt = get_base_prompt("7d")

# NEW: For 12-month forecast service
from forex_core.config import (
    PROJECTION_MONTHS,
    HISTORICAL_LOOKBACK_DAYS_12M,
    TECH_LOOKBACK_DAYS_12M,
    VOL_LOOKBACK_DAYS_12M,
    get_base_prompt,
)

forecast_months = PROJECTION_MONTHS
lookback = HISTORICAL_LOOKBACK_DAYS_12M
prompt = get_base_prompt("12m")
```

### Pattern 4: Helper Functions (unchanged)
```python
# OLD & NEW (identical API)
from forex_core.utils import percent_change, dump_json, load_json

# Calculate percentage change
change = percent_change(new_value, old_value)

# Save forecast results
dump_json(Path("./output/forecast.json"), results)

# Load cached data
cached = load_json(Path("./cache/data.json"))
```

---

## Environment Variables

No changes to environment variables! All variables remain the same:

```bash
# General
ENVIRONMENT=production
REPORT_TIMEZONE=America/Santiago

# Directories
DATA_DIR=./data
OUTPUT_DIR=./reports
CHART_DIR=./charts
WAREHOUSE_DIR=./data/warehouse
METRICS_LOG_PATH=./logs/metrics.jsonl

# API Keys
FRED_API_KEY=your_key_here
NEWS_API_KEY=your_key_here
ALPHAVANTAGE_API_KEY=your_key_here

# Email
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password
EMAIL_RECIPIENTS=email1@example.com,email2@example.com

# Models
ENABLE_ARIMA=true
ENABLE_VAR=true
ENABLE_RF=true
ENSEMBLE_WINDOW=30

# Cache
CACHE_TTL_MINUTES=30
```

---

## Migration Steps for Existing Code

### Step 1: Update Imports
```python
# Find and replace:
# from usdclp_forecaster.logger → from forex_core.utils
# from usdclp_forecaster.config → from forex_core.config
# from usdclp_forecaster.constants → from forex_core.config
# from usdclp_forecaster.utils → from forex_core.utils

# Same for _12m variant
```

### Step 2: Update Constant Names (Horizon-Specific)
```python
# If using 7d:
HISTORICAL_LOOKBACK_DAYS → HISTORICAL_LOOKBACK_DAYS_7D
TECH_LOOKBACK_DAYS → TECH_LOOKBACK_DAYS_7D
VOL_LOOKBACK_DAYS → VOL_LOOKBACK_DAYS_7D

# If using 12m:
HISTORICAL_LOOKBACK_DAYS → HISTORICAL_LOOKBACK_DAYS_12M
TECH_LOOKBACK_DAYS → TECH_LOOKBACK_DAYS_12M
VOL_LOOKBACK_DAYS → VOL_LOOKBACK_DAYS_12M
```

### Step 3: Update BASE_PROMPT
```python
# OLD
from usdclp_forecaster.constants import BASE_PROMPT

# NEW
from forex_core.config import get_base_prompt
BASE_PROMPT = get_base_prompt("7d")  # or "12m"
```

### Step 4: Test
```python
# Verify imports work
from forex_core.utils import logger
from forex_core.config import get_settings

logger.info("Migration successful!")
settings = get_settings()
assert settings.environment is not None
```

---

## Backwards Compatibility Notes

### Fully Compatible (No Changes Required)
- `logger` object and usage
- `configure_logging()` function (enhanced with optional params)
- `get_settings()` function
- All Settings class fields
- All helper functions in utils
- Shared constants (LOCAL_TZ, DEFAULT_RECIPIENTS, CHILE_GMT_OFFSET)

### Requires Import Path Update Only
- Module paths changed (usdclp_forecaster → forex_core)
- No API changes

### Requires Constant Name Update
- Horizon-specific constants now have suffix (_7D or _12M)
- Alternative: Use helper function `get_base_prompt(horizon)`

---

## Testing Your Migration

```python
# test_migration.py
from pathlib import Path
from forex_core.utils import logger, configure_logging, percent_change, dump_json
from forex_core.config import get_settings, PROJECTION_DAYS, get_base_prompt

def test_logging():
    configure_logging(level="INFO")
    logger.info("Logging works!")
    assert True

def test_config():
    settings = get_settings()
    assert settings.environment in ["production", "staging", "development"]
    print(f"Environment: {settings.environment}")

def test_constants():
    assert PROJECTION_DAYS == 7
    prompt_7d = get_base_prompt("7d")
    prompt_12m = get_base_prompt("12m")
    assert "7 días" in prompt_7d
    assert "12 meses" in prompt_12m
    print("Constants work!")

def test_helpers():
    change = percent_change(110, 100)
    assert change == 10.0

    data = {"test": 123}
    test_path = Path("./test_output.json")
    dump_json(test_path, data)
    assert test_path.exists()
    test_path.unlink()  # Cleanup
    print("Helpers work!")

if __name__ == "__main__":
    test_logging()
    test_config()
    test_constants()
    test_helpers()
    print("\n✅ All migration tests passed!")
```

Run with:
```bash
cd /Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system
python test_migration.py
```

---

## Common Issues & Solutions

### Issue 1: Import Error
```
ModuleNotFoundError: No module named 'forex_core'
```

**Solution:** Add project root to PYTHONPATH:
```bash
export PYTHONPATH="/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src:$PYTHONPATH"
```

Or install as editable package:
```bash
pip install -e /Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system
```

### Issue 2: Constant Not Found
```
ImportError: cannot import name 'HISTORICAL_LOOKBACK_DAYS' from 'forex_core.config'
```

**Solution:** Update to horizon-specific constant:
```python
# Old
from forex_core.config import HISTORICAL_LOOKBACK_DAYS

# New
from forex_core.config import HISTORICAL_LOOKBACK_DAYS_7D
# or
from forex_core.config import HISTORICAL_LOOKBACK_DAYS_12M
```

### Issue 3: Settings Not Loading .env
```
Settings fields are None or default values
```

**Solution:** Ensure .env file is in the working directory or specify path:
```python
# Option 1: Run from directory with .env
cd /path/to/project && python script.py

# Option 2: Use env_file parameter (Pydantic v2)
# Settings already configured to look for .env automatically
```

---

## Next Steps After Migration

1. Update your scripts to use new imports
2. Run your test suite
3. Update documentation with new import paths
4. Consider adding unit tests for forex_core utilities
5. Proceed to Phase 2: Data Layer Migration

---

**Need Help?** Check the full migration summary:
`/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/docs/MIGRATION_PHASE1_SUMMARY.md`
