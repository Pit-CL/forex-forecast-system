# Quick Deploy Guide - High Impact Improvements

**Last Updated:** 2025-11-13
**Status:** Ready for Deployment

---

## Overview

This guide covers quick deployment of the three high-impact improvements implemented in session 2025-11-13:

1. **Copper Price Integration** (15-25% accuracy improvement expected)
2. **MLflow Tracking** (experiment tracking foundation)
3. **Auto-Retraining Pipeline** (automated optimization)

**Priority:** Deploy Copper first (highest immediate impact), then MLflow, then Auto-Retraining.

---

## 1. Copper Integration - Deploy First

**Time:** 2-3 hours
**Impact:** Immediate forecast accuracy improvement

### Quick Steps

```bash
# 1. Test integration (5 min)
cd /Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system
python scripts/test_copper_integration.py
# Expected: ALL TESTS PASSED

# 2. Validate in forecaster (5 min)
python -m services.forecaster_7d.cli validate

# 3. Build and deploy (30 min)
docker-compose build forecaster-7d forecaster-15d forecaster-30d forecaster-90d
docker-compose up -d

# 4. Monitor (ongoing)
docker-compose logs -f forecaster-7d | grep -i copper
# Expected: "Successfully fetched X copper price points"

# 5. Verify warehouse cache
ls -lh data/warehouse/copper_hgf_usd_lb.parquet
# Should exist after first run
```

### Files Involved

**New:**
- `src/forex_core/data/providers/copper_prices.py`
- `scripts/test_copper_integration.py`

**Modified:**
- `src/forex_core/data/providers/__init__.py` (add CopperPricesClient export)
- `src/forex_core/data/loader.py` (add copper integration)

### Success Criteria

- [ ] Tests pass
- [ ] Copper data in forecasts (check logs)
- [ ] Warehouse cache file exists
- [ ] No errors in production logs
- [ ] Reports show copper as data source

**Full Documentation:** `docs/COPPER_INTEGRATION.md`

---

## 2. MLflow Setup - Deploy Second

**Time:** 2 hours setup + 6-8 hours integration
**Impact:** Experiment tracking for all forecasts

### Quick Steps - Setup

```bash
# 1. Install MLflow (2 min)
pip install mlflow>=2.16
# Or add to requirements.txt and rebuild

# 2. Initialize experiments (5 min)
python scripts/init_mlflow.py
# Expected: MLFLOW INITIALIZATION COMPLETE

# 3. Test dashboard (2 min)
python scripts/mlflow_dashboard.py
# Should show empty experiments

# 4. Verify setup
ls -la data/mlflow/mlflow.db
ls -la data/mlflow/mlruns/
# Both should exist
```

### Quick Steps - Integration (Optional but Recommended)

Add to each forecaster's `cli.py` (example for forecaster_7d):

```python
from forex_core.mlops import MLflowConfig
import mlflow

# In run() function, after data loading:
mlflow_config = MLflowConfig()
mlflow_config.setup("forecaster_7d")

with mlflow_config.start_run(run_name=f"forecast_{datetime.now().strftime('%Y%m%d')}"):
    # Log parameters
    mlflow.log_param("num_sources", len(bundle.sources))
    mlflow.log_param("copper_available", bundle.copper_features is not None)

    # ... run forecast ...

    # Log metrics
    mlflow.log_metric("rmse", result.rmse)
    mlflow.log_metric("mae", result.mae)
    mlflow.log_metric("mape", result.mape)

    # Log report as artifact
    mlflow.log_artifact(str(report_path))
```

Repeat for forecaster_15d, forecaster_30d, forecaster_90d.

### Optional: MLflow UI

```bash
# Add to docker-compose.yml (already documented in MLFLOW_SETUP.md)
docker-compose --profile mlflow up -d mlflow-ui
# Visit http://localhost:5000 or http://your-vps-ip:5000
```

### Success Criteria

- [ ] MLflow installed
- [ ] Experiments initialized
- [ ] Dashboard shows experiments
- [ ] (Optional) Forecasters log to MLflow
- [ ] (Optional) UI accessible

**Full Documentation:** `docs/MLFLOW_SETUP.md`

---

## 3. Auto-Retraining Pipeline - Deploy Third

**Time:** 8-10 hours Docker integration + testing
**Impact:** Automated model optimization
**Status:** Code complete, Docker integration pending

### Architecture

```
Container: model-optimizer
  - Runs weekly (cron)
  - Checks triggers (performance, drift, time)
  - Optimizes hyperparameters (grid search)
  - Validates new config
  - Deploys if approved
  - Monitors post-deployment
```

### What's Ready

**Core code (100% complete):**
- `src/forex_core/optimization/triggers.py` - Trigger detection
- `src/forex_core/optimization/chronos_optimizer.py` - Grid search
- `src/forex_core/optimization/validator.py` - Config validation
- `src/forex_core/optimization/deployment.py` - Safe deployment
- `src/services/model_optimizer/pipeline.py` - Main pipeline
- `src/services/model_optimizer/cli.py` - CLI interface

**What's Pending:**
- Dockerfile.optimizer (needs to be created)
- docker-compose integration (needs to be added)
- Cron job setup (needs configuration)
- Unit tests (recommended before production)

### Manual Testing (Can Do Now)

```bash
# Test trigger detection
python -c "
from forex_core.optimization.triggers import TriggerManager
manager = TriggerManager()
should_opt, reasons = manager.check_triggers('7d')
print(f'Should optimize: {should_opt}')
print(f'Reasons: {reasons}')
"

# Test optimizer (dry-run)
python -m services.model_optimizer.cli run --horizon 7d --dry-run

# Check status
python -m services.model_optimizer.cli status
```

### Production Deployment (Future)

**Recommended timeline:** 2-3 weeks after copper + MLflow deployed

**Steps:**
1. Create Dockerfile.optimizer
2. Add to docker-compose.prod.yml
3. Setup cron: `0 2 * * 0 docker-compose run model-optimizer`
4. Test in staging
5. Deploy to production
6. Monitor first run

### Success Criteria (When Deployed)

- [ ] Container builds successfully
- [ ] Can run optimization manually
- [ ] Validation works
- [ ] Deployment updates configs
- [ ] Rollback tested
- [ ] Cron job executes

**Full Documentation:**
- `docs/AUTO_RETRAINING_SUMMARY.md` - Executive summary
- `docs/decisions/ADR-001-auto-retraining-pipeline.md` - Architecture decision
- `docs/technical/auto-retraining-architecture.md` - Technical details
- `docs/technical/auto-retraining-roadmap.md` - Implementation roadmap

---

## Deployment Timeline Recommendation

### Week 1: Copper (High Priority)
- **Day 1-2:** Deploy copper integration
- **Day 3-5:** Monitor impact, measure RMSE improvement
- **Deliverable:** Copper data in all forecasts

### Week 2: MLflow (Medium Priority)
- **Day 1-2:** Setup MLflow infrastructure
- **Day 3-5:** Integrate in forecasters (optional)
- **Deliverable:** All forecasts tracked in MLflow

### Week 3-4: Auto-Retraining (Lower Priority)
- **Week 3:** Docker integration, testing
- **Week 4:** Staging deployment, validation
- **Deliverable:** Automated optimization pipeline

---

## Rollback Plans

### Copper Rollback

If issues arise:

```bash
# 1. Revert loader.py changes
git checkout HEAD -- src/forex_core/data/loader.py

# 2. Remove copper provider
rm src/forex_core/data/providers/copper_prices.py

# 3. Update __init__.py
# Remove CopperPricesClient import from providers/__init__.py

# 4. Rebuild and redeploy
docker-compose build && docker-compose up -d
```

**Impact:** Returns to mindicador copper data (fewer features but functional)

### MLflow Rollback

MLflow is optional and non-blocking:

```bash
# Simply don't use it, or:
pip uninstall mlflow
```

**Impact:** No impact on forecasts (only lose tracking)

### Auto-Retraining Rollback

```bash
# Stop container
docker-compose stop model-optimizer

# Disable cron job
# (Comment out cron entry)

# Restore config if needed
python -m services.model_optimizer.cli rollback --horizon 7d
```

**Impact:** Returns to manual optimization process

---

## Monitoring

### Copper Health Checks

```bash
# Daily: Check logs
docker-compose logs --tail=100 forecaster-7d | grep -i copper

# Expected output:
# "Successfully fetched 1258 copper price points from Yahoo Finance"
# OR "Using FRED backup for copper prices"
# OR "Using 1258 cached copper data points"

# Weekly: Check warehouse
ls -lh data/warehouse/copper_hgf_usd_lb.parquet
# Should be updated regularly
```

### MLflow Health Checks

```bash
# Weekly: Check database size
du -sh data/mlflow/mlflow.db
# Should be < 100 MB

# Monthly: Check runs
python scripts/mlflow_dashboard.py stats
# All experiments should have recent runs
```

### Auto-Retraining Health Checks (When Deployed)

```bash
# Weekly: Check optimization history
python -m services.model_optimizer.cli status

# After each run: Check logs
docker-compose logs model-optimizer

# Monitor for:
# - Trigger detections
# - Validation results
# - Deployment success/failure
# - Rollback events
```

---

## Support

### Issue Resolution

1. **Check relevant documentation first:**
   - Copper: `docs/COPPER_INTEGRATION.md`
   - MLflow: `docs/MLFLOW_SETUP.md`
   - Auto-retraining: `docs/AUTO_RETRAINING_SUMMARY.md`

2. **Run test scripts:**
   ```bash
   python scripts/test_copper_integration.py
   python scripts/init_mlflow.py
   python -m services.model_optimizer.cli validate --horizon 7d
   ```

3. **Check logs:**
   ```bash
   docker-compose logs -f [service-name]
   ```

4. **Review this session's documentation:**
   - `docs/sessions/2025-11-13-HIGH-IMPACT-IMPROVEMENTS.md`

5. **If still stuck:** Create GitHub issue with:
   - Error logs
   - Steps to reproduce
   - Environment info

---

## Quick Reference

### File Locations

**Source Code:**
- Copper: `src/forex_core/data/providers/copper_prices.py`
- MLflow: `src/forex_core/mlops/mlflow_config.py`
- Auto-retraining: `src/forex_core/optimization/` + `src/services/model_optimizer/`

**Scripts:**
- Copper test: `scripts/test_copper_integration.py`
- MLflow init: `scripts/init_mlflow.py`
- MLflow dashboard: `scripts/mlflow_dashboard.py`

**Documentation:**
- Copper: `docs/COPPER_INTEGRATION.md`
- MLflow: `docs/MLFLOW_SETUP.md`
- Auto-retraining: `docs/AUTO_RETRAINING_SUMMARY.md`
- Combined: `docs/COPPER_MLFLOW_IMPLEMENTATION.md`
- Session: `docs/sessions/2025-11-13-HIGH-IMPACT-IMPROVEMENTS.md`

**Data:**
- Copper cache: `data/warehouse/copper_hgf_usd_lb.parquet`
- MLflow DB: `data/mlflow/mlflow.db`
- MLflow artifacts: `data/mlflow/mlruns/`
- Config backups: `configs/backups/`

---

## Expected Impact Summary

| Component | Timeline | Expected Improvement |
|-----------|----------|---------------------|
| **Copper** | 1 month | +15-25% accuracy (RMSE reduction) |
| **MLflow** | 3 months | Full experiment tracking, model comparison |
| **Auto-Retraining** | 6 months | 80% automation, <7 day adaptation |

**Combined 6-month target:**
- RMSE: 8-12 CLP → 6-9 CLP
- Manual interventions: 2/month → 0.5/month
- Adaptation speed: 30 days → <7 days

---

**Last Updated:** 2025-11-13
**Version:** 1.0
**Status:** Ready for Deployment
