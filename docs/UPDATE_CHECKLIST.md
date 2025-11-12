# Code Update Checklist - Migrating to forex_core

Use this checklist when updating code that uses the legacy `usdclp_forecaster` system.

## Import Changes

### Technical Analysis

#### Old
```python
from usdclp_forecaster.analysis.technical import (
    compute_technicals,
    calculate_rsi,
    calculate_macd
)
```

#### New
```python
from forex_core.analysis.technical import (
    compute_technicals,
    calculate_rsi,
    calculate_macd
)
```

**Changes:** None - API identical
**Action:** ✅ Simple find-replace of import path

---

### Fundamental Analysis

#### Old
```python
from usdclp_forecaster.analysis.fundamentals import (
    QuantFactor,
    extract_quant_factors,
    build_quant_factors,
    macro_events_table
)
```

#### New
```python
from forex_core.analysis.fundamental import (  # Note: singular "fundamental"
    QuantFactor,
    extract_quant_factors,
    build_quant_factors,
    macro_events_table
)
```

**Changes:** Module renamed from `fundamentals` (plural) to `fundamental` (singular)
**Action:** ✅ Update import path, check for consistency

---

### Macro Analysis

#### Old
```python
from usdclp_forecaster.analysis.macro import (
    RiskGauge,
    compute_risk_gauge
)
```

#### New
```python
from forex_core.analysis.macro import (
    RiskGauge,
    compute_risk_gauge
)
```

**Changes:** None - API identical
**Action:** ✅ Simple find-replace of import path

---

### Forecasting (MAJOR CHANGES)

#### Old
```python
from usdclp_forecaster.analysis.modeling import forecast_prices
from usdclp_forecaster.config import Settings
from usdclp_forecaster.constants import PROJECTION_DAYS

settings = Settings()
forecast, artifacts = forecast_prices(bundle, settings, steps=PROJECTION_DAYS)
```

#### New
```python
from forex_core.forecasting.models import ForecastEngine
from forex_core.config.base import ForecastConfig

config = ForecastConfig(
    enable_arima=True,
    enable_var=True,
    enable_rf=False,
    ensemble_window=30
)
engine = ForecastEngine(config, horizon="daily", steps=7)
forecast, artifacts = engine.forecast(bundle)
```

**Changes:**
1. `forecast_prices()` → `ForecastEngine.forecast()`
2. `Settings` → `ForecastConfig`
3. Function call → Method call on engine instance
4. Must specify `horizon` ("daily" or "monthly")

**Action:** ⚠️ Refactor to use ForecastEngine pattern

---

### Data Models

#### Old
```python
from usdclp_forecaster.models import (
    Indicator,
    MacroEvent,
    NewsHeadline,
    ForecastPoint,
    ForecastPackage
)
```

#### New
```python
from forex_core.data.models import (
    Indicator,
    MacroEvent,
    NewsHeadline,
    ForecastPoint,
    ForecastPackage
)
```

**Changes:** None - API identical, just moved to `data.models`
**Action:** ✅ Simple find-replace of import path

---

### Data Loading

#### Old
```python
from usdclp_forecaster.data_loader import DataBundle, load_data
```

#### New
```python
from forex_core.data.loader import DataBundle, load_data
```

**Changes:** None - API identical
**Action:** ✅ Simple find-replace of import path

---

## Configuration Changes

### Old Configuration (7d)
```python
from usdclp_forecaster.config import Settings

settings = Settings(
    enable_arima=True,
    enable_var=True,
    enable_rf=False,
    ensemble_window=30,
    metrics_log_path=Path("logs/metrics.jsonl")
)
```

### New Configuration
```python
from forex_core.config.base import ForecastConfig

config = ForecastConfig(
    # Model selection
    enable_arima=True,
    enable_var=True,
    enable_rf=False,

    # Ensemble
    ensemble_window=30,

    # Logging
    metrics_log_path="logs/metrics.jsonl"  # Can be string or Path
)
```

**Changes:** `Settings` → `ForecastConfig`
**Action:** ⚠️ Update class name and verify all parameters

---

## Usage Pattern Changes

### 7-Day Forecast

#### Old
```python
from usdclp_forecaster.analysis.modeling import forecast_prices
from usdclp_forecaster.constants import PROJECTION_DAYS

forecast, artifacts = forecast_prices(bundle, settings, steps=PROJECTION_DAYS)
```

#### New
```python
from forex_core.forecasting.models import ForecastEngine

engine = ForecastEngine(config, horizon="daily", steps=7)
forecast, artifacts = engine.forecast(bundle)
```

---

### 12-Month Forecast

#### Old
```python
# Separate codebase for 12m version
from usdclp_forecaster_12m.analysis.modeling import forecast_prices
from usdclp_forecaster_12m.constants import PROJECTION_MONTHS

forecast, artifacts = forecast_prices(bundle, settings, steps=PROJECTION_MONTHS)
```

#### New
```python
# Same codebase, different parameters
from forex_core.forecasting.models import ForecastEngine

engine = ForecastEngine(config, horizon="monthly", steps=12)
forecast, artifacts = engine.forecast(bundle)
```

**Major Improvement:** Single codebase for both horizons!

---

## Advanced Forecasting (Optional)

If your code directly uses ARIMA/GARCH/VAR functions:

### Old (modeling.py internals)
```python
# These were private functions in modeling.py
_run_arima_garch(series, steps, settings)
_run_var(bundle, steps, settings)
_run_random_forest(bundle, steps, settings)
```

### New (Public API)
```python
from forex_core.forecasting.arima import auto_select_arima_order, fit_arima, forecast_arima
from forex_core.forecasting.garch import fit_garch, forecast_garch_volatility
from forex_core.forecasting.var import fit_var, forecast_var, var_price_reconstruction

# ARIMA
log_returns = np.log(prices).diff().dropna()
order = auto_select_arima_order(log_returns)
arima_model = fit_arima(log_returns, order)
price_forecast, _ = forecast_arima(arima_model, steps=7, last_price=prices.iloc[-1])

# GARCH
garch_model = fit_garch(log_returns)
volatility = forecast_garch_volatility(garch_model, horizon=7)

# VAR
data = pd.DataFrame({'usdclp': ..., 'copper': ..., 'dxy': ..., 'tpm': ...})
var_model = fit_var(data, maxlags=5)
forecast_df = forecast_var(var_model, steps=7)
prices = var_price_reconstruction(forecast_df, 'usdclp', last_price=950.0)
```

**Action:** ⚠️ Refactor to use new modular API

---

## File-by-File Update Guide

### Step 1: Find all files using legacy imports
```bash
# Search for legacy imports
grep -r "from usdclp_forecaster" . --include="*.py"
grep -r "from usdclp_forecaster_12m" . --include="*.py"
grep -r "import usdclp_forecaster" . --include="*.py"
```

### Step 2: Update imports (simple cases)
```bash
# Technical analysis
find . -name "*.py" -exec sed -i '' 's/from usdclp_forecaster\.analysis\.technical/from forex_core.analysis.technical/g' {} +

# Fundamental analysis (note plural → singular)
find . -name "*.py" -exec sed -i '' 's/from usdclp_forecaster\.analysis\.fundamentals/from forex_core.analysis.fundamental/g' {} +

# Macro analysis
find . -name "*.py" -exec sed -i '' 's/from usdclp_forecaster\.analysis\.macro/from forex_core.analysis.macro/g' {} +

# Data models
find . -name "*.py" -exec sed -i '' 's/from usdclp_forecaster\.models/from forex_core.data.models/g' {} +

# Data loader
find . -name "*.py" -exec sed -i '' 's/from usdclp_forecaster\.data_loader/from forex_core.data.loader/g' {} +
```

### Step 3: Update forecasting code (manual)
Files using `forecast_prices()` need manual refactoring:

1. Replace `from usdclp_forecaster.analysis.modeling import forecast_prices`
   with `from forex_core.forecasting.models import ForecastEngine`

2. Replace:
   ```python
   forecast, artifacts = forecast_prices(bundle, settings, steps)
   ```
   with:
   ```python
   engine = ForecastEngine(config, horizon="daily", steps=7)
   forecast, artifacts = engine.forecast(bundle)
   ```

### Step 4: Update configuration
Replace `Settings` with `ForecastConfig`:

```bash
find . -name "*.py" -exec sed -i '' 's/from usdclp_forecaster\.config import Settings/from forex_core.config.base import ForecastConfig/g' {} +
```

Then manually verify each usage of `Settings()` → `ForecastConfig()`.

### Step 5: Update constants
Replace:
```python
from usdclp_forecaster.constants import PROJECTION_DAYS
steps = PROJECTION_DAYS
```

with:
```python
steps = 7  # Or make it a configuration parameter
```

### Step 6: Test each updated file
```bash
python -m pytest tests/test_<module>.py -v
```

---

## Common Patterns and Their Migrations

### Pattern 1: Simple Technical Analysis
```python
# OLD
from usdclp_forecaster.analysis.technical import compute_technicals
technicals = compute_technicals(prices)

# NEW (identical API)
from forex_core.analysis.technical import compute_technicals
technicals = compute_technicals(prices)
```
**Effort:** Low - Just update import

---

### Pattern 2: Complete Forecast Pipeline
```python
# OLD (7d version)
from usdclp_forecaster.data_loader import load_data
from usdclp_forecaster.analysis.modeling import forecast_prices
from usdclp_forecaster.config import Settings
from usdclp_forecaster.constants import PROJECTION_DAYS

bundle = load_data()
settings = Settings()
forecast, artifacts = forecast_prices(bundle, settings, PROJECTION_DAYS)

# NEW
from forex_core.data.loader import load_data
from forex_core.forecasting.models import ForecastEngine
from forex_core.config.base import ForecastConfig

bundle = load_data()
config = ForecastConfig()
engine = ForecastEngine(config, horizon="daily", steps=7)
forecast, artifacts = engine.forecast(bundle)
```
**Effort:** Medium - Refactor to engine pattern

---

### Pattern 3: Accessing Forecast Results
```python
# OLD
for point in forecast.series:
    print(point.date, point.mean, point.ci95_low, point.ci95_high)

# NEW (identical API)
for point in forecast.series:
    print(point.date, point.mean, point.ci95_low, point.ci95_high)
```
**Effort:** Low - No changes needed

---

### Pattern 4: Risk Analysis
```python
# OLD
from usdclp_forecaster.analysis.macro import compute_risk_gauge
gauge = compute_risk_gauge(bundle)

# NEW (identical API)
from forex_core.analysis.macro import compute_risk_gauge
gauge = compute_risk_gauge(bundle)
```
**Effort:** Low - Just update import

---

## Testing Checklist

After updating each file:

- [ ] Imports resolve without errors
- [ ] No `ModuleNotFoundError` or `ImportError`
- [ ] Configuration objects work correctly
- [ ] Forecast results have expected structure
- [ ] All tests pass
- [ ] No deprecation warnings
- [ ] Performance is comparable to legacy system

---

## Rollback Plan

If issues arise:

1. **Keep legacy code:** Don't delete old imports until fully tested
2. **Use git branches:** Create `migrate-to-forex-core` branch
3. **Gradual migration:** Update one module at a time
4. **Feature flags:** Use config to toggle between old/new implementations

Example feature flag:
```python
if config.use_new_forecasting:
    from forex_core.forecasting.models import ForecastEngine
    engine = ForecastEngine(config, horizon="daily", steps=7)
    forecast, artifacts = engine.forecast(bundle)
else:
    from usdclp_forecaster.analysis.modeling import forecast_prices
    forecast, artifacts = forecast_prices(bundle, settings, steps)
```

---

## Support Resources

- **Migration Report:** `/docs/MIGRATION_REPORT.md` - Detailed analysis
- **Quick Start:** `/docs/FORECASTING_QUICKSTART.md` - Usage examples
- **API Docs:** Module docstrings with examples
- **Issues:** GitHub issues for bugs or questions

---

## Estimated Migration Time

| Component | Effort | Time |
|-----------|--------|------|
| Simple imports (technical, fundamental, macro) | Low | 30 min |
| Data models and loader | Low | 15 min |
| Configuration updates | Medium | 1 hour |
| Forecasting refactor | High | 2-4 hours |
| Testing and validation | High | 2-3 hours |
| **Total** | | **6-9 hours** |

**Recommendation:** Allocate 2 full days for migration including testing.

---

## Quick Migration Script

Save as `migrate_imports.py`:

```python
#!/usr/bin/env python3
import re
import sys
from pathlib import Path

REPLACEMENTS = {
    # Simple imports
    'from usdclp_forecaster.analysis.technical': 'from forex_core.analysis.technical',
    'from usdclp_forecaster.analysis.fundamentals': 'from forex_core.analysis.fundamental',
    'from usdclp_forecaster.analysis.macro': 'from forex_core.analysis.macro',
    'from usdclp_forecaster.models': 'from forex_core.data.models',
    'from usdclp_forecaster.data_loader': 'from forex_core.data.loader',

    # 12m version
    'from usdclp_forecaster_12m.analysis.technical': 'from forex_core.analysis.technical',
    'from usdclp_forecaster_12m.analysis.fundamentals': 'from forex_core.analysis.fundamental',
    'from usdclp_forecaster_12m.analysis.macro': 'from forex_core.analysis.macro',
}

def migrate_file(file_path):
    content = file_path.read_text()
    modified = False

    for old, new in REPLACEMENTS.items():
        if old in content:
            content = content.replace(old, new)
            modified = True
            print(f"✅ {file_path}: {old} → {new}")

    if modified:
        file_path.write_text(content)

    return modified

if __name__ == "__main__":
    target_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    py_files = list(target_dir.rglob("*.py"))

    print(f"Scanning {len(py_files)} Python files...")
    modified_count = sum(migrate_file(f) for f in py_files)
    print(f"\n✅ Modified {modified_count} files")
    print("⚠️  Manual review needed for forecasting code!")
```

Usage:
```bash
python migrate_imports.py /path/to/your/code
```

---

## Completion Checklist

- [ ] All imports updated
- [ ] Configuration migrated to ForecastConfig
- [ ] Forecasting code refactored to ForecastEngine
- [ ] All tests pass
- [ ] Performance benchmarks comparable
- [ ] Documentation updated
- [ ] Team trained on new API
- [ ] Legacy code deprecated with warnings
- [ ] Migration announced to stakeholders

**When all checked:** ✅ Migration complete!
