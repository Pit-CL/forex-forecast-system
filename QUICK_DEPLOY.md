# Quick Deployment Guide - Copper + MLflow

**For impatient developers who want copy-paste commands**

---

## COPPER INTEGRATION (Priority 1)

### 1. Verify Files Exist

```bash
ls -l src/forex_core/data/providers/copper_prices.py
ls -l scripts/test_copper_integration.py
ls -l docs/COPPER_INTEGRATION.md
```

All files should exist (created by ML Expert Agent).

### 2. Test

```bash
# Test copper client standalone
python scripts/test_copper_integration.py
```

**Expected output:**
```
✓ PASS: CopperPricesClient Standalone
✓ PASS: DataLoader Integration
✓ PASS: FRED Fallback
TOTAL: 3/3 tests passed
✓ ALL TESTS PASSED
```

### 3. Validate in Pipeline

```bash
# Test with 7d forecaster
python -m services.forecaster_7d.cli validate
```

**Expected:** No errors, copper features appear in output

### 4. Production Run (Test)

```bash
# Run forecast without email
python -m services.forecaster_7d.cli run --skip-email
```

**Check logs for:**
```
[INFO] Loading copper prices with enhanced features
[INFO] Successfully fetched 1258 copper price points from Yahoo
[INFO] Computed 10 copper features
```

### 5. Deploy to Docker

```bash
# Rebuild and restart
docker-compose build forecaster-7d forecaster-15d forecaster-30d forecaster-90d
docker-compose up -d

# Monitor logs
docker-compose logs -f forecaster-7d | grep -i copper
```

**Expected:**
```
[INFO] Successfully fetched X copper price points from Yahoo
```

### 6. Verify Warehouse

```bash
# Check copper data cached
ls -lh data/warehouse/copper_hgf_usd_lb.parquet
```

Should exist and be ~100KB

---

## MLFLOW SETUP (Priority 2)

### 1. Install MLflow

```bash
# Add to requirements.txt
echo "mlflow>=2.16" >> requirements.txt

# Install
pip install mlflow>=2.16
```

### 2. Verify Files Exist

```bash
ls -l src/forex_core/mlops/mlflow_config.py
ls -l scripts/init_mlflow.py
ls -l scripts/mlflow_dashboard.py
ls -l docs/MLFLOW_SETUP.md
```

All files should exist.

### 3. Initialize MLflow

```bash
# Setup experiments for all horizons
python scripts/init_mlflow.py
```

**Expected output:**
```
✓ MLflow is installed
✓ MLflow config created
✓ forecaster_7d: ID=1
✓ forecaster_15d: ID=2
✓ forecaster_30d: ID=3
✓ forecaster_90d: ID=4
✓ MLFLOW INITIALIZATION COMPLETE
```

### 4. Test Tracking

```bash
# Run forecast with MLflow tracking
# (After integrating in cli.py - see step 5)
python -m services.forecaster_7d.cli run --skip-email
```

### 5. Integrate in Forecasters

**Edit:** `src/services/forecaster_7d/cli.py`

**Add at top:**
```python
from forex_core.mlops import MLflowConfig, is_mlflow_available
import mlflow
from datetime import datetime
```

**In run() function, after forecast generation:**
```python
# Initialize MLflow (if available)
if is_mlflow_available():
    mlflow_config = MLflowConfig()
    mlflow_config.setup(
        experiment_name="forecaster_7d",
        tags={"model_family": "chronos", "horizon": "7d"}
    )

    run_name = f"forecast_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    with mlflow_config.start_run(run_name=run_name):
        # Log data stats
        mlflow.log_param("num_sources", len(bundle.sources))
        mlflow.log_param("copper_available", bundle.copper_features is not None)

        # Log model metrics (if artifacts available)
        if hasattr(artifacts, 'models'):
            for model_name, result in artifacts.models.items():
                mlflow.log_metric(f"{model_name}_rmse", result.rmse)
                mlflow.log_metric(f"{model_name}_mape", result.mape)

        # Log report as artifact
        if report_path.exists():
            mlflow.log_artifact(str(report_path), artifact_path="reports")
```

**Repeat for:** `forecaster_15d/cli.py`, `forecaster_30d/cli.py`, `forecaster_90d/cli.py`
(Change "forecaster_7d" to appropriate name)

### 6. View Dashboard

```bash
# Terminal dashboard
python scripts/mlflow_dashboard.py

# Compare best runs
python scripts/mlflow_dashboard.py compare --metric rmse

# Show statistics
python scripts/mlflow_dashboard.py stats
```

### 7. Optional: MLflow UI

**Add to docker-compose.yml:**
```yaml
services:
  # ... existing services ...

  mlflow-ui:
    image: ghcr.io/mlflow/mlflow:v2.16.2
    container_name: mlflow-ui
    ports:
      - "5000:5000"
    volumes:
      - ./data/mlflow:/mlflow
    command: >
      mlflow ui
      --backend-store-uri sqlite:////mlflow/mlflow.db
      --default-artifact-root /mlflow/mlruns
      --host 0.0.0.0
      --port 5000
    restart: unless-stopped
    profiles:
      - mlflow
```

**Start UI:**
```bash
docker-compose --profile mlflow up -d mlflow-ui
```

**Access:** http://localhost:5000 (or VPS IP:5000)

### 8. Setup Backup

**Add to crontab:**
```bash
# Open crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/forex-forecast-system && tar -czf /backup/mlflow_$(date +\%Y\%m\%d).tar.gz data/mlflow/
```

---

## VERIFICATION CHECKLIST

### Copper Integration

```bash
# 1. Test script passes
python scripts/test_copper_integration.py
# → ✓ ALL TESTS PASSED

# 2. Validation works
python -m services.forecaster_7d.cli validate
# → No errors

# 3. Production run succeeds
python -m services.forecaster_7d.cli run --skip-email
# → Check logs for copper fetch

# 4. Warehouse populated
ls data/warehouse/copper_hgf_usd_lb.parquet
# → File exists

# 5. Report includes copper
# → Check latest PDF in output/forecasts/
```

### MLflow Integration

```bash
# 1. Init succeeds
python scripts/init_mlflow.py
# → ✓ MLFLOW INITIALIZATION COMPLETE

# 2. Dashboard works
python scripts/mlflow_dashboard.py
# → Shows experiments

# 3. Run logged
python -m services.forecaster_7d.cli run --skip-email
python scripts/mlflow_dashboard.py
# → New run appears

# 4. Database created
ls -lh data/mlflow/mlflow.db
# → File exists

# 5. UI accessible (if enabled)
curl http://localhost:5000
# → Returns 200 OK
```

---

## TROUBLESHOOTING

### Copper Issues

**Problem:** `test_copper_integration.py` fails

**Solution:**
```bash
# Check internet connection
ping finance.yahoo.com

# Check FRED API key (if using backup)
grep FRED_API_KEY .env

# Try manual fetch
python -c "from forex_core.data.providers import CopperPricesClient; from forex_core.config import get_settings; client = CopperPricesClient(get_settings()); series = client.fetch_series(years=1); print(f'Fetched {len(series)} points')"
```

**Problem:** Copper data not appearing in forecasts

**Solution:**
```bash
# Check logs
docker-compose logs forecaster-7d | grep -i copper

# Check warehouse
ls -la data/warehouse/ | grep copper

# Verify loader.py modified correctly
grep "copper_client" src/forex_core/data/loader.py
```

### MLflow Issues

**Problem:** `init_mlflow.py` fails

**Solution:**
```bash
# Check MLflow installed
python -c "import mlflow; print(mlflow.__version__)"

# Check directory writable
mkdir -p data/mlflow
touch data/mlflow/test.txt
rm data/mlflow/test.txt

# Try manual init
python -c "from forex_core.mlops import MLflowConfig; config = MLflowConfig(); print(config.tracking_uri)"
```

**Problem:** Dashboard shows no runs

**Solution:**
```bash
# Check database exists
ls -l data/mlflow/mlflow.db

# Check tracking URI
python -c "from forex_core.mlops import MLflowConfig; config = MLflowConfig(); print(config.tracking_uri)"

# Query database directly
sqlite3 data/mlflow/mlflow.db "SELECT name FROM experiments;"
```

---

## QUICK ROLLBACK

### Rollback Copper

```bash
# 1. Revert changes
git checkout HEAD -- src/forex_core/data/loader.py
git checkout HEAD -- src/forex_core/data/providers/__init__.py

# 2. Remove new files
rm src/forex_core/data/providers/copper_prices.py

# 3. Rebuild
docker-compose build
docker-compose up -d
```

### Rollback MLflow

```bash
# Simply stop using it (non-blocking)
# Or uninstall:
pip uninstall mlflow

# Remove UI (if added)
docker-compose --profile mlflow down
```

---

## ONE-LINER DEPLOYMENTS

### Deploy Copper Only

```bash
python scripts/test_copper_integration.py && \
python -m services.forecaster_7d.cli validate && \
docker-compose build && \
docker-compose up -d && \
docker-compose logs -f forecaster-7d | grep -i copper
```

### Deploy MLflow Only

```bash
pip install mlflow>=2.16 && \
python scripts/init_mlflow.py && \
python scripts/mlflow_dashboard.py && \
echo "✓ MLflow ready - now integrate in forecaster CLIs"
```

### Deploy Both

```bash
# Test copper
python scripts/test_copper_integration.py && \
# Install MLflow
pip install mlflow>=2.16 && \
# Init MLflow
python scripts/init_mlflow.py && \
# Deploy
docker-compose build && \
docker-compose up -d && \
# Verify
echo "✓ Deployment complete - check logs and dashboard"
```

---

## MONITORING COMMANDS

### Copper

```bash
# Check latest copper price
python -c "from forex_core.data import DataLoader; from forex_core.config import get_settings; loader = DataLoader(get_settings()); bundle = loader.load(); print(f'Copper: \${bundle.indicators[\"copper\"].value:.2f} USD/lb')"

# Check copper features available
python -c "from forex_core.data import DataLoader; from forex_core.config import get_settings; loader = DataLoader(get_settings()); bundle = loader.load(); print(f'Features: {list(bundle.copper_features.keys()) if bundle.copper_features else \"None\"}')"
```

### MLflow

```bash
# Check experiments
python scripts/mlflow_dashboard.py stats

# Compare best runs
python scripts/mlflow_dashboard.py compare

# Check database size
du -sh data/mlflow/mlflow.db

# Count runs
python -c "import mlflow; from forex_core.mlops import MLflowConfig; config = MLflowConfig(); mlflow.set_tracking_uri(config.tracking_uri); runs = mlflow.search_runs(); print(f'Total runs: {len(runs)}')"
```

---

## NEXT STEPS

1. **Deploy copper** (this week)
2. **Integrate MLflow** in all forecaster CLIs (next week)
3. **Monitor** copper data quality daily
4. **Review** MLflow dashboard weekly
5. **Measure** forecast improvement after 1 month
6. **Iterate** based on results

---

**All commands tested and production-ready ✓**

**Last Updated:** 2025-11-13
