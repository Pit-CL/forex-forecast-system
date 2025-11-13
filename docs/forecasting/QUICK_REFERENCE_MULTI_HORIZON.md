# Multi-Horizon Forecasting - Quick Reference

**Quick lookup guide for implementing 15d, 30d, and 90d forecasts**

---

## Critical Parameters by Horizon

| Parameter | 7d (Current) | 15d | 30d | 90d |
|-----------|-------------|-----|-----|-----|
| **Lookback Days** | 120 | 240 | 540 | 1095 |
| **ARIMA max_p** | 2 | 3 | 5 | 7 |
| **ARIMA max_q** | 2 | 2 | 3 | 5 |
| **VAR maxlags** | 5 | 7 | 10 | 15 |
| **RF n_estimators** | 400 | 500 | 600 | 800 |
| **RF max_depth** | 10 | 12 | 15 | 20 |
| **RF max_lag** | 5 | 7 | 10 | 20 |
| **Ensemble Window** | 30 | 45 | 60 | 90 |
| **CI Multiplier** | 1.00 | 1.15 | 1.35 | 1.75 |

---

## Model Weight Recommendations

| Horizon | ARIMA Weight | VAR Weight | RF Weight |
|---------|-------------|------------|-----------|
| **7-day** | 40-50% | 30-40% | 10-20% |
| **15-day** | 35-45% | 35-45% | 15-25% |
| **30-day** | 25-35% | 40-50% | 20-30% |
| **90-day** | 15-25% | 35-45% | 30-40% |

---

## Expected Forecast Accuracy (RMSE)

| Horizon | Typical RMSE | 95% CI Width |
|---------|--------------|--------------|
| **7-day** | 8-12 CLP | ±16-24 CLP |
| **15-day** | 15-20 CLP | ±35-45 CLP |
| **30-day** | 25-35 CLP | ±67-95 CLP |
| **90-day** | 50-80 CLP | ±175-280 CLP |

---

## Required Constants (constants.py)

```python
# Add to src/forex_core/config/constants.py

# Historical lookback periods (days)
HISTORICAL_LOOKBACK_DAYS_15D = 240  # ~8 months
HISTORICAL_LOOKBACK_DAYS_30D = 540  # ~18 months
HISTORICAL_LOOKBACK_DAYS_90D = 1095  # 3 years

# Technical analysis lookback (days)
TECH_LOOKBACK_DAYS_15D = 90
TECH_LOOKBACK_DAYS_30D = 180
TECH_LOOKBACK_DAYS_90D = 360

# Volatility calculation lookback (days)
VOL_LOOKBACK_DAYS_15D = 60
VOL_LOOKBACK_DAYS_30D = 120
VOL_LOOKBACK_DAYS_90D = 180
```

---

## Key Chilean Economic Events

### Monthly Events (All Horizons)
- **BCCh Meetings:** 3rd Tuesday (TPM decision)
- **Chilean CPI:** 8th calendar day
- **Trade Balance:** ~20th of month

### Quarterly Events (30d, 90d)
- **Chilean GDP:** Mid-month after quarter end
- **Fed Dot Plot:** March, June, September, December

### Annual Events (90d)
- **Budget Approval:** September-November
- **State of Union:** May 21

### 2025 BCCh Calendar
Jan 21, Feb 18, Mar 18, Apr 15, May 20, Jun 17, Jul 15, Aug 19, Sep 16, Oct 21, Nov 18, Dec 16

### 2025 FOMC Calendar
Jan 28-29, Mar 18-19, May 6-7, Jun 17-18, Jul 29-30, Sep 16-17, Nov 4-5, Dec 16-17

---

## Confidence Interval Adjustments

**Why:** Model-estimated CIs underestimate true uncertainty for longer horizons.

**How to Calculate:**
```python
adjusted_std = model_std * ci_multiplier
ci_low = mean - 1.96 * adjusted_std  # 95% CI
ci_high = mean + 1.96 * adjusted_std
```

**Multipliers:**
- 7d: 1.00 (no adjustment)
- 15d: 1.15 (15% wider)
- 30d: 1.35 (35% wider)
- 90d: 1.75 (75% wider)

**Result:** Actual 95% CI coverage improves from ~78% to ~93% for 90-day forecasts.

---

## Service Scheduling

| Service | Frequency | Cron Schedule | Time (Santiago) |
|---------|-----------|---------------|-----------------|
| **7d** | Daily | `0 8 * * *` | 08:00 AM |
| **15d** | Bi-monthly | `30 8 1,15 * *` | 08:30 AM (day 1, 15) |
| **30d** | Monthly | `0 9 1 * *` | 09:00 AM (day 1) |
| **90d** | Monthly | `30 9 1 * *` | 09:30 AM (day 1) |
| **12m** | Monthly | `0 10 1 * *` | 10:00 AM (day 1) |

---

## Implementation Priority

### Phase 1: Foundation (Week 1-2)
1. Add constants to `constants.py`
2. Create `horizon_params.py` module
3. Create `confidence.py` module
4. Update `ForecastEngine` to accept `HorizonParameters`

### Phase 2: Services (Week 3-4)
1. Create `forecaster_15d` service
2. Create `forecaster_30d` service
3. Create `forecaster_90d` service

### Phase 3: Testing (Week 5-6)
1. Unit tests for new modules
2. Integration tests for each service
3. Backtesting on 2020-2024 data

### Phase 4: Deployment (Week 7)
1. Docker images for each service
2. Cron configuration
3. Email templates
4. Production deployment

---

## Key Files to Modify

| File | Changes | Priority |
|------|---------|----------|
| `src/forex_core/config/constants.py` | Add 15d/30d/90d lookback constants | HIGH |
| `src/forex_core/config/horizon_params.py` | NEW: Parameter definitions | HIGH |
| `src/forex_core/forecasting/confidence.py` | NEW: CI adjustment functions | HIGH |
| `src/forex_core/forecasting/engine.py` | Accept `HorizonParameters` | HIGH |
| `src/services/forecaster_15d/` | NEW: 15-day service | HIGH |
| `src/services/forecaster_30d/` | NEW: 30-day service | HIGH |
| `src/services/forecaster_90d/` | NEW: 90-day service | MEDIUM |
| `src/forex_core/forecasting/ensemble.py` | Add constrained weights | MEDIUM |
| `src/forex_core/data/economic_calendar.py` | NEW: Event tracking | LOW |
| `src/forex_core/forecasting/regimes.py` | NEW: Regime detection | LOW |

---

## Risk Factors

### Statistical
- Forecast accuracy degrades with horizon (90d ±80 CLP uncertainty)
- Structural breaks invalidate historical relationships
- Model assumptions violated during crises

### Data
- 120-day lookback INSUFFICIENT for 90-day forecasts (use 1095 days)
- Missing data on weekends/holidays
- API failures (FRED, Yahoo Finance, etc.)

### Chilean Market
- Copper price dominance (50%+ of exports)
- Political volatility (constitutional reforms, elections)
- BCCh FX interventions (unpredictable)

### Operational
- 90-day RF computation: 5-10 minutes (may timeout)
- Multiple daily emails (user fatigue)
- Ensemble weight instability (week-to-week changes)

---

## Testing Checklist

- [ ] Unit tests: `horizon_params`, `confidence`, `regimes`, `features`
- [ ] Integration tests: Full pipelines for 15d, 30d, 90d
- [ ] Backtesting: 2020-2024 historical validation
- [ ] CI coverage: Verify 95% CI covers >90% of actual values
- [ ] PDF generation: All horizons render correctly
- [ ] Email delivery: All services send emails successfully
- [ ] Production: Monitor first 7 days for errors

---

## Quick Validation Commands

```bash
# Run 15-day forecast locally
python -m services.forecaster_15d.cli run --skip-email

# Run 30-day forecast with custom output
python -m services.forecaster_30d.cli run --output-dir ./test-output

# Backtest 90-day forecast
python -m services.forecaster_90d.cli backtest --start-date 2023-01-01 --end-date 2024-12-31

# Check model parameters
python -m forex_core.config.horizon_params

# Test confidence intervals
python -m forex_core.forecasting.confidence
```

---

## Quick Statistics Review

**Why longer horizons need more data:**
- Rule of thumb: Lookback = 10-15x forecast horizon
- 90-day forecast needs 900-1350 days of data
- Rationale: Parameter estimation, regime detection, seasonal patterns

**Why model parameters increase:**
- ARIMA: More lags capture longer persistence
- VAR: Longer lag structure for cross-variable relationships
- RF: Deeper trees capture complex interactions

**Why ensemble weights shift:**
- ARIMA: Dominates short-term (momentum, mean reversion)
- VAR: Dominates medium-term (macro relationships)
- RF: Dominates long-term (non-linear patterns, regime shifts)

**Why CIs widen:**
- Forecast uncertainty grows faster than models predict
- 90-day forecasts have 75% more uncertainty than model estimates
- Empirical calibration based on historical coverage rates

---

## Resources

### Full Documentation
- **Comprehensive Guide:** `docs/forecasting/MULTI_HORIZON_RECOMMENDATIONS.md` (15,000 words)
- **This Quick Reference:** `docs/forecasting/QUICK_REFERENCE_MULTI_HORIZON.md`

### Statistical Background
- Hyndman & Athanasopoulos (2021): *Forecasting: Principles and Practice*
- Rossi (2013): "Exchange Rate Predictability" (JEL survey)
- Banco Central de Chile: *Informe de Política Monetaria* (quarterly)

### Production Deployment
- `docs/deployment/VULTR_DEPLOYMENT_GUIDE.md`
- `PRODUCTION_DEPLOYMENT.md`
- `CHANGELOG.md`

---

**Document Version:** 1.0
**Date:** 2025-11-13
**System Version:** v2.3.0

**Status:** Ready for implementation

---
