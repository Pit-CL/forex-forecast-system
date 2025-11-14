# USD/CLP Autonomous Forecasting System - Implementation Plan

## Executive Summary
This plan implements a complete transition from Chronos-T5 to an interpretable ensemble system (XGBoost + SARIMAX + GARCH) with full autonomy: auto-retraining, auto-optimization, and dual alert systems.

**Timeline**: 2-3 weeks
**Risk Level**: Medium (requires careful testing before production)
**Rollback Plan**: Keep Chronos models until new system validated

---

## 1. NEW FILES TO CREATE

### A. Core Models (`src/forex_core/models/`)

#### `xgboost_forecaster.py` (~400 lines)
**Purpose**: Gradient boosting forecaster for non-linear patterns
**Key Features**:
- 50+ engineered features (technical, copper, macro)
- SHAP values for feature importance
- Walk-forward validation
- Horizon-specific tuning (7d, 15d, 30d, 90d)

#### `sarimax_forecaster.py` (~350 lines)
**Purpose**: Seasonal ARIMA for temporal components
**Key Features**:
- Auto-ARIMA for order selection
- Exogenous variables (copper, DXY, VIX, TPM)
- Seasonal patterns (monthly, quarterly)
- AIC/BIC optimization

#### `garch_volatility.py` (~250 lines)
**Purpose**: Volatility modeling for confidence intervals
**Key Features**:
- GARCH(1,1) for 30d/90d
- EGARCH for 7d/15d (leverage effects)
- Dynamic confidence intervals
- Volatility regime detection

#### `ensemble_forecaster.py` (~300 lines)
**Purpose**: Weighted ensemble coordinator
**Key Features**:
- Horizon-specific weights:
  - 7d: XGBoost 60%, SARIMAX 40%
  - 15d: XGBoost 50%, SARIMAX 50%
  - 30d: SARIMAX 60%, XGBoost 40%
  - 90d: SARIMAX 70%, XGBoost 30%
- GARCH/EGARCH confidence bands
- Performance tracking per model
- Automatic fallback if one model fails

---

### B. Alert Systems (`src/forex_core/alerts/`)

#### `market_shock_detector.py` (~400 lines)
**Purpose**: Detect market events affecting USD/CLP
**Triggers** (from @agent-usdclp):
1. **Sudden Trend Change**:
   - USD/CLP change >2% in single day
   - 3-day trend reversal (>3% swing)

2. **Volatility Spike**:
   - Daily volatility >1.5x 30-day average
   - Intraday range >3%

3. **Copper Price Shock**:
   - Copper change >5% in day
   - Sustained decline >10% in week

4. **DXY Extreme Movement**:
   - DXY >105 (strong dollar) or <95 (weak dollar)
   - Daily DXY change >1%

5. **VIX Fear Spike**:
   - VIX >30 (global stress)
   - VIX change >+20% in day

6. **Chilean Political Events**:
   - TPM surprise change (±0.5% unexpected)
   - Presidential speeches (keyword detection)

**Output**: Email with HTML + short PDF (using existing format)

#### `model_performance_alerts.py` (~300 lines)
**Purpose**: Monitor model health and degradation
**Triggers** (from @agent-ml-expert):
1. **Degradation Warnings**:
   - WARNING: RMSE increase >15% vs. baseline
   - CRITICAL: RMSE increase >30%
   - Directional accuracy <55%

2. **Re-training Status**:
   - Weekly XGBoost re-training completion
   - Monthly SARIMAX re-training completion
   - Hyperparameter changes logged

3. **Model Failures**:
   - Training failures (convergence issues)
   - Prediction errors (NaN, infinite values)
   - Data quality issues (missing values >5%)

4. **Optimization Results**:
   - Optuna trial summaries
   - Best hyperparameters found
   - Performance improvements

**Output**: Email with model diagnostics + PDF report

#### `alert_email_generator.py` (~200 lines)
**Purpose**: Generate alert emails using existing format
**Key Features**:
- Reuse HTML templates from `test_email_and_pdf.py`
- Short PDF format (2 pages max)
- CID images for charts
- Priority levels (INFO, WARNING, CRITICAL)

---

### C. MLOps Automation (`src/forex_core/mlops/`)

#### `auto_retrain_xgboost.py` (~350 lines)
**Purpose**: Weekly XGBoost re-training
**Process**:
1. Load last 180 days of data
2. Walk-forward validation (30-day windows)
3. Optuna hyperparameter tuning (50 trials)
4. Train on full dataset with best params
5. Save model with metadata
6. Send performance alert email

**Schedule**: Sundays 00:00 Chile time

#### `auto_retrain_sarimax.py` (~300 lines)
**Purpose**: Monthly SARIMAX re-training
**Process**:
1. Load last 2 years of data
2. Auto-ARIMA order selection
3. Cross-validation (12-fold)
4. Train final model
5. Diagnostic plots (residuals, ACF, PACF)
6. Save model + send alert

**Schedule**: 1st of each month, 01:00 Chile time

#### `hyperparameter_optimizer.py` (~250 lines)
**Purpose**: Optuna-based optimization
**Search Spaces**:
- **XGBoost**: learning_rate [0.01-0.3], max_depth [3-10], n_estimators [100-1000]
- **SARIMAX**: p [0-5], d [0-2], q [0-5], P [0-2], D [0-1], Q [0-2], s [7,30]
- **GARCH**: p [1-3], q [1-3]

**Objective**: Minimize RMSE on validation set

---

### D. Feature Engineering (`src/forex_core/features/`)

#### `feature_engineer.py` (~500 lines)
**Purpose**: Generate 50+ features for XGBoost/SARIMAX
**Feature Categories**:

1. **Lagged Features** (20):
   - USD/CLP lags: 1, 2, 3, 5, 7, 14, 21, 30 days
   - Copper lags: 1, 3, 7, 14 days
   - DXY lags: 1, 3, 7 days
   - VIX lags: 1, 3 days

2. **Technical Indicators** (15):
   - SMA: 5, 10, 20, 50 days
   - EMA: 10, 20, 50 days
   - RSI: 14-day
   - Bollinger Bands (20, 2σ)
   - ATR: 14-day
   - MACD (12, 26, 9)

3. **Copper Features** (7):
   - Copper price, volume
   - Copper RSI, SMA20, EMA50
   - Bollinger position
   - MACD

4. **Macro Features** (6):
   - DXY index
   - VIX volatility
   - TPM (Chilean rate)
   - Fed Funds rate
   - IMACEC (Chilean GDP proxy)
   - IPC (inflation)

5. **Derived Features** (8):
   - USD/CLP returns (1d, 7d, 30d)
   - Rolling std (7d, 30d)
   - Trend indicator (linear regression slope)
   - Seasonality (day of week, month)

---

### E. Updated Scripts (`scripts/`)

#### `forecast_with_ensemble.py` (~400 lines)
**Purpose**: Main forecasting script replacing Chronos
**Process**:
1. Load latest data
2. Generate features
3. Load trained models (XGBoost, SARIMAX, GARCH)
4. Generate individual forecasts
5. Ensemble with horizon-specific weights
6. Calculate confidence intervals
7. Generate charts
8. Save results

**Used by**: All 4 Docker containers (7d, 15d, 30d, 90d)

#### `send_alert_email.py` (~200 lines)
**Purpose**: Dispatch alert emails
**Triggers**:
- Market shock detected
- Model performance degradation
- Re-training completed
- System failures

---

## 2. FILES TO MODIFY

### A. Existing Core Files

#### `src/forex_core/data/loader.py`
**Changes**:
- Add feature engineering integration
- Ensure all macro data loaded (DXY, VIX, TPM, Fed Funds)
- Validate data quality (no missing >5%)

#### `src/forex_core/data/providers/__init__.py`
**Changes**:
- Export new feature engineering functions
- Add data validation utilities

---

### B. Docker Configuration

#### `Dockerfile.7d.prod`
**Changes** (same for 15d, 30d, 90d):
- Update Python dependencies (add xgboost, optuna, arch for GARCH)
- Ensure all requirements installed

#### `docker-compose.prod.yml`
**Changes**:
- Environment variable for model type: `MODEL_TYPE=ensemble`
- Volume mounts for model persistence

---

### C. Cron Schedules

#### `cron/7d/crontab`
**BEFORE**:
```cron
0 8 * * * cd /app && PYTHONPATH=/app/src python scripts/forecast_7d.py
```

**AFTER**:
```cron
# Data collection (18:00 Chile = 21:00 UTC in summer, 22:00 UTC in winter)
30 20 * * 1-5 cd /app && PYTHONPATH=/app/src python scripts/collect_data.py

# Forecast generation (18:45 Chile)
45 21 * * 1-5 cd /app && PYTHONPATH=/app/src python scripts/forecast_with_ensemble.py --horizon 7

# Weekly re-training (Sunday 00:00 Chile)
0 3 * * 0 cd /app && PYTHONPATH=/app/src python scripts/auto_retrain_xgboost.py

# Healthcheck update
30 22 * * 1-5 date > /tmp/healthcheck
```

**Note**: Adjust for Chile's DST (October-March: UTC-3, April-September: UTC-4)

#### `cron/15d/crontab`
```cron
30 20 * * 1-5 cd /app && PYTHONPATH=/app/src python scripts/collect_data.py
50 21 * * 1-5 cd /app && PYTHONPATH=/app/src python scripts/forecast_with_ensemble.py --horizon 15
0 3 * * 0 cd /app && PYTHONPATH=/app/src python scripts/auto_retrain_xgboost.py
50 22 * * 1-5 date > /tmp/healthcheck
```

#### `cron/30d/crontab`
```cron
30 20 * * 1-5 cd /app && PYTHONPATH=/app/src python scripts/collect_data.py
55 21 * * 1-5 cd /app && PYTHONPATH=/app/src python scripts/forecast_with_ensemble.py --horizon 30
0 3 * * 0 cd /app && PYTHONPATH=/app/src python scripts/auto_retrain_xgboost.py
0 4 1 * * cd /app && PYTHONPATH=/app/src python scripts/auto_retrain_sarimax.py
55 22 * * 1-5 date > /tmp/healthcheck
```

#### `cron/90d/crontab`
```cron
30 20 * * 1-5 cd /app && PYTHONPATH=/app/src python scripts/collect_data.py
0 22 * * 1-5 cd /app && PYTHONPATH=/app/src python scripts/forecast_with_ensemble.py --horizon 90
0 3 * * 0 cd /app && PYTHONPATH=/app/src python scripts/auto_retrain_xgboost.py
0 4 1 * * cd /app && PYTHONPATH=/app/src python scripts/auto_retrain_sarimax.py
0 23 * * 1-5 date > /tmp/healthcheck
```

---

### D. Email Scripts

#### `scripts/send_daily_email.sh`
**BEFORE**:
```bash
# Runs at 7:30 AM
30 7 * * 1,3,4,5 /app/scripts/send_daily_email.sh
```

**AFTER**:
```bash
# Runs at 19:00 Chile (after forecasts complete at 18:00)
0 22 * * 1,3,4,5 /app/scripts/send_daily_email.sh
```

---

## 3. FILES TO DELETE (REQUIRES APPROVAL)

### A. Chronos Models
- [ ] `src/forex_core/models/chronos_forecaster.py` (370 lines)
- [ ] `src/forex_core/models/chronos_model.py` (if exists)
- [ ] `scripts/test_chronos.py` (if exists)

### B. Unused Prophet/Neural Models
- [ ] `src/forex_core/models/prophet_forecaster.py` (if exists)
- [ ] `src/forex_core/models/neural_prophet.py` (if exists)

### C. Old Test Scripts
- [ ] `scripts/test_naive_model.py` (replaced by proper validation)
- [ ] `scripts/validate_model.py` (will be replaced with walk-forward validation)

### D. Deprecated Data Providers
- [ ] `src/forex_core/data/providers/yahoo_finance.py` (if not used)

**ACTION REQUIRED**: Review each file above and approve deletion individually.

---

## 4. NEW DEPENDENCIES (`requirements.txt`)

**To Add**:
```txt
# Machine Learning
xgboost>=2.0.0
optuna>=3.0.0
shap>=0.42.0

# Time Series
statsmodels>=0.14.0
arch>=6.0.0  # For GARCH/EGARCH

# Existing (verify versions)
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
```

**No removal** - keep all existing dependencies for email/PDF generation.

---

## 5. ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│                     DATA COLLECTION                          │
│  (18:00 Chile daily - Mon-Fri)                              │
│                                                              │
│  Sources: BCCh, Investing.com, Copper API                   │
│  Output: /app/data/usdclp_latest.csv                        │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                  FEATURE ENGINEERING                         │
│                                                              │
│  Input: Raw data (USD/CLP, Copper, DXY, VIX, TPM)          │
│  Output: 50+ engineered features                            │
│  - Lags (1-30 days)                                         │
│  - Technical indicators (SMA, RSI, BB, MACD)                │
│  - Macro features                                           │
│  - Derived (returns, volatility)                            │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                   MODEL ENSEMBLE                             │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   XGBoost    │  │   SARIMAX    │  │  GARCH/      │     │
│  │              │  │              │  │  EGARCH      │     │
│  │ • 50 features│  │ • Auto-ARIMA │  │              │     │
│  │ • Walk-fwd   │  │ • Seasonal   │  │ • Volatility │     │
│  │ • SHAP       │  │ • Exog vars  │  │ • Confidence │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                 │
│                            ▼                                 │
│                  ┌──────────────────┐                        │
│                  │  WEIGHTED AVG    │                        │
│                  │                  │                        │
│                  │  7d:  60/40      │                        │
│                  │  15d: 50/50      │                        │
│                  │  30d: 40/60      │                        │
│                  │  90d: 30/70      │                        │
│                  └────────┬─────────┘                        │
└───────────────────────────┼──────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    DUAL ALERT SYSTEMS                        │
│                                                              │
│  ┌──────────────────────┐  ┌──────────────────────┐        │
│  │  MARKET SHOCK        │  │  MODEL PERFORMANCE   │        │
│  │  DETECTOR            │  │  MONITOR             │        │
│  │                      │  │                      │        │
│  │ • USD/CLP >2% move   │  │ • RMSE degradation   │        │
│  │ • Volatility spike   │  │ • Re-training status │        │
│  │ • Copper shock       │  │ • Failures logged    │        │
│  │ • DXY extremes       │  │ • Optimization done  │        │
│  │ • VIX >30            │  │                      │        │
│  └──────────┬───────────┘  └──────────┬───────────┘        │
│             │                          │                     │
│             └──────────┬───────────────┘                     │
│                        │                                     │
│                        ▼                                     │
│              ┌──────────────────┐                            │
│              │  ALERT EMAIL     │                            │
│              │  GENERATOR       │                            │
│              │                  │                            │
│              │ • HTML format    │                            │
│              │ • Short PDF      │                            │
│              │ • CID images     │                            │
│              └──────────────────┘                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   AUTO-RETRAINING                            │
│                                                              │
│  WEEKLY (Sunday 00:00 Chile):                               │
│  • XGBoost re-training (all horizons)                       │
│  • Optuna hyperparameter tuning (50 trials)                 │
│  • Walk-forward validation                                  │
│  • Performance alert email                                  │
│                                                              │
│  MONTHLY (1st of month, 01:00 Chile):                       │
│  • SARIMAX re-training (30d, 90d only)                      │
│  • Auto-ARIMA order selection                               │
│  • Cross-validation (12-fold)                               │
│  • Diagnostic plots + alert email                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. IMPLEMENTATION SEQUENCE

### Phase 1: Core Models (Week 1)
1. Create `feature_engineer.py` with all 50+ features
2. Implement `xgboost_forecaster.py` with SHAP
3. Implement `sarimax_forecaster.py` with Auto-ARIMA
4. Implement `garch_volatility.py` (GARCH + EGARCH)
5. Create `ensemble_forecaster.py` with weighted averaging
6. **Test locally** with historical data (2023-2024)

### Phase 2: Alert Systems (Week 1-2)
7. Create `market_shock_detector.py` with 6 triggers
8. Create `model_performance_alerts.py` with degradation monitoring
9. Create `alert_email_generator.py` reusing existing HTML/PDF
10. **Test alerts** with simulated shocks

### Phase 3: MLOps Automation (Week 2)
11. Create `auto_retrain_xgboost.py` with Optuna
12. Create `auto_retrain_sarimax.py` with Auto-ARIMA
13. Create `hyperparameter_optimizer.py`
14. **Test re-training** on historical windows

### Phase 4: Integration (Week 2-3)
15. Update `forecast_with_ensemble.py` script
16. Modify Docker configurations
17. Update all cron schedules to 18:00 Chile
18. Update email dispatch timing
19. **Integration testing** on local Docker

### Phase 5: Cleanup & Deployment (Week 3)
20. Review and delete Chronos files (with approval)
21. Remove unused code (with approval)
22. Final testing on local system
23. **Deploy to Vultr** server
24. Monitor first week of production

---

## 7. TESTING STRATEGY

### A. Unit Tests
- Each model tested independently on 2023-2024 data
- Feature engineering validation (no NaN, infinite values)
- Alert triggers tested with synthetic shocks

### B. Integration Tests
- Full ensemble tested on last 90 days
- Email generation verified (HTML + PDF)
- Docker containers built and run locally

### C. Walk-Forward Validation
- 30-day windows rolling through 2024
- Compare ensemble vs. individual models
- Verify RMSE improvements

### D. Alert System Tests
- Inject historical shocks (Oct 2024 political events)
- Verify email dispatch
- Check degradation detection

---

## 8. ROLLBACK PLAN

**If new system fails**:
1. Keep Chronos models in `/app/models/backup/`
2. Restore old cron schedules
3. Switch Docker `MODEL_TYPE=chronos`
4. Investigate issues, fix, re-deploy

**Rollback trigger**:
- RMSE >20% worse than Chronos
- More than 2 prediction failures per week
- Alert system false positives >10/day

---

## 9. SUCCESS METRICS

### A. Model Performance (vs. Chronos baseline)
- **7d RMSE**: <10 CLP (target: 8 CLP)
- **15d RMSE**: <15 CLP (target: 12 CLP)
- **30d RMSE**: <25 CLP (target: 20 CLP)
- **90d RMSE**: <50 CLP (target: 40 CLP)
- **Directional accuracy**: >60% (all horizons)

### B. System Reliability
- **Uptime**: >99.5%
- **Failed forecasts**: <1% of total
- **Email delivery**: >99%
- **Re-training success**: >95%

### C. Alert Quality
- **Market shock false positives**: <5/month
- **Model degradation early detection**: Within 3 days
- **Alert email delivery time**: <2 minutes

---

## 10. RISKS & MITIGATIONS

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| XGBoost overfitting | Medium | High | Walk-forward validation, regularization |
| SARIMAX non-stationarity | Medium | Medium | ADF tests, differencing, regime detection |
| Alert fatigue | Low | Medium | Tune thresholds based on first month |
| Re-training failures | Low | High | Email alerts, automatic fallback to last model |
| Chile DST issues | High | Low | Use pytz for Chile/Santiago timezone |
| Data provider outages | Medium | High | Multiple providers, cached data fallback |

---

## 11. POST-DEPLOYMENT MONITORING

### First Week:
- Daily review of forecast emails
- Check all alerts (expect tuning needed)
- Monitor Docker logs for errors
- Validate re-training executes Sunday

### First Month:
- Compare RMSE vs. Chronos baseline
- Tune alert thresholds
- Optimize hyperparameters if needed
- Add missing features (NDF, AFP flows)

### Ongoing:
- Monthly performance reports
- Quarterly model audits
- Annual feature engineering review

---

## 12. NEXT STEPS

**USER APPROVAL REQUIRED**:
1. ✅ Approve overall architecture
2. ✅ Approve files to delete (Section 3)
3. ✅ Approve cron schedule changes (18:00 Chile)
4. ✅ Approve alert triggers (market + model)

**AFTER APPROVAL**:
- Invoke @code-reviewer and @code-simplifier to begin implementation
- Start with Phase 1 (Core Models)
- Provide progress updates after each phase

---

**END OF IMPLEMENTATION PLAN**

Generated: 2025-11-14
Author: @agent-ml-expert, @agent-usdclp, @code-reviewer, @code-simplifier (coordinated)
Status: AWAITING USER APPROVAL
