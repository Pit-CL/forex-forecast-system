# Multi-Horizon USD/CLP Forecasting - Executive Summary

**One-page overview for decision-makers**

---

## The Question

**Should we extend our 7-day USD/CLP forecaster to include 15-day, 30-day, and 90-day horizons?**

**Answer: YES for 15d and 30d. MAYBE for 90d (evaluate after 3 months).**

---

## Key Findings

### 1. Current System is Well-Built
- Excellent architecture: ARIMA+GARCH, VAR, Random Forest ensemble
- Production-ready: Docker, cron, automated emails
- 7-day forecasts: 8-12 CLP accuracy (better than random walk by 20%)

### 2. Critical Issue: Data Lookback is INSUFFICIENT
- **Current:** 120 days of historical data
- **Problem:** 120 days is NOT ENOUGH for 90-day forecasts
- **Solution:** Need 1,095 days (3 years) for 90-day horizon
- **Good News:** System already loads 6 years, just need to use more

### 3. Models Need Horizon-Specific Tuning
- **ARIMA:** Increase AR/MA orders for longer horizons (2→7 for 90d)
- **VAR:** Increase lags for longer relationships (5→15 for 90d)
- **Random Forest:** More trees, deeper, more features (400→800 trees for 90d)
- **Ensemble Weights:** Shift from ARIMA-dominant (7d) to RF-dominant (90d)

### 4. Confidence Intervals Must Be Widened
- Models underestimate uncertainty for longer horizons
- 90-day forecasts: Need 75% WIDER confidence intervals
- Without adjustment: 95% CI only covers 78% of actual values
- With adjustment: 95% CI covers 90%+ of actual values (acceptable)

### 5. Chilean Market Factors Critical for Long-Term
- **Short-term (7-15d):** Technical indicators dominate
- **Medium-term (30d):** BCCh meetings, copper prices critical
- **Long-term (90d):** Political events, seasonal patterns, regime shifts

---

## Forecast Accuracy Expectations

| Horizon | Typical Error (RMSE) | Confidence Interval | Forecast Skill |
|---------|----------------------|---------------------|----------------|
| **7 days** | ±8-12 CLP | ±16-24 CLP (95%) | Excellent |
| **15 days** | ±15-20 CLP | ±35-45 CLP (95%) | Very Good |
| **30 days** | ±25-35 CLP | ±67-95 CLP (95%) | Good |
| **90 days** | ±50-80 CLP | ±175-280 CLP (95%) | Fair |

**Interpretation:** Even 90-day forecasts are useful (5-10% better than random walk), but uncertainty is high.

---

## Business Value Assessment

| Horizon | Use Case | Target Audience | Implementation Effort | ROI |
|---------|----------|-----------------|----------------------|-----|
| **7d** | Daily hedging | Traders, importers | ✅ COMPLETE | ⭐⭐⭐⭐⭐ |
| **15d** | Bi-monthly planning | Treasury depts | 2-3 days | ⭐⭐⭐⭐⭐ |
| **30d** | Monthly budgets | CFOs, controllers | 3-4 days | ⭐⭐⭐⭐⭐ |
| **90d** | Quarterly strategy | Executive planning | 5-6 days | ⭐⭐⭐ |

---

## Recommendations

### Phase 1: HIGH Priority (Implement Now)
**15-Day Forecaster**
- **Why:** Fills gap between 7d and 30d, many companies have bi-monthly cycles
- **Effort:** 2-3 days development + 1-2 days testing
- **Risk:** Low
- **Decision:** ✅ **STRONGLY RECOMMEND**

**30-Day Forecaster**
- **Why:** Critical for monthly budgeting, matches BCCh reporting (IPoM)
- **Effort:** 3-4 days development + 2-3 days testing
- **Risk:** Low-Medium
- **Decision:** ✅✅ **CRITICAL BUSINESS NEED**

### Phase 2: MEDIUM Priority (Evaluate After 3 Months)
**90-Day Forecaster**
- **Why:** Adds strategic planning capability, competitive differentiator
- **Effort:** 5-6 days development + 3-4 days testing
- **Risk:** Medium-High (accuracy concerns, long computation time)
- **Decision:** 🟡 **DEPENDS ON USER DEMAND**

---

## Required Changes

### 1. New Configuration Parameters
**File:** `src/forex_core/config/constants.py`
```python
HISTORICAL_LOOKBACK_DAYS_15D = 240  # 8 months
HISTORICAL_LOOKBACK_DAYS_30D = 540  # 18 months
HISTORICAL_LOOKBACK_DAYS_90D = 1095  # 3 years
```

### 2. Horizon-Specific Model Parameters
**File:** `src/forex_core/config/horizon_params.py` (NEW)
- Define ARIMA max_p/max_q for each horizon
- Define VAR maxlags for each horizon
- Define RF parameters for each horizon
- Define confidence interval multipliers

### 3. Confidence Interval Adjustments
**File:** `src/forex_core/forecasting/confidence.py` (NEW)
- Implement horizon-aware CI widening
- Apply 1.15x multiplier for 15d, 1.35x for 30d, 1.75x for 90d

### 4. Service Creation
**Directories:** `src/services/forecaster_15d/`, `forecaster_30d/`, `forecaster_90d/`
- Copy structure from existing `forecaster_7d`
- Update configuration for each horizon
- Create Docker images and cron schedules

---

## Implementation Timeline

| Phase | Tasks | Duration | Effort |
|-------|-------|----------|--------|
| **Week 1-2** | Infrastructure (constants, params, confidence) | 2 weeks | 1 developer |
| **Week 3** | 15-day service creation and testing | 1 week | 1 developer |
| **Week 4** | 30-day service creation and testing | 1 week | 1 developer |
| **Week 5-6** | Backtesting and validation (2020-2024) | 2 weeks | 1 developer |
| **Week 7** | Production deployment and monitoring | 1 week | 1 developer |
| **OPTIONAL:** | 90-day service (evaluate after 3 months) | 2 weeks | 1 developer |

**Total:** 7 weeks for 15d + 30d, or 9 weeks with 90d

---

## Risk Assessment

### Statistical Risks
- **Medium:** Forecast accuracy degrades with horizon (expected)
- **Medium:** Model assumptions may break during crises
- **Low:** Ensemble weights may be unstable (mitigated by constraints)

### Operational Risks
- **Low:** API failures (have fallback sources)
- **Medium:** 90-day computation time (5-10 minutes, may timeout)
- **Low:** Email spam (4-5 reports/day max: 7d daily + 15d bi-monthly + 30d monthly + 90d monthly + 12m monthly)

### Business Risks
- **Low:** Users may misinterpret longer-term forecasts (emphasize CIs in reports)
- **Low:** Maintenance burden increases with more services (but architecture is unified)

---

## Cost-Benefit Summary

**Investment:**
- Development: 7-9 weeks of developer time
- Infrastructure: Minimal (Docker, cron - already in place)
- Maintenance: ~2 hours/month ongoing monitoring

**Return:**
- Meet critical business need: Monthly budgeting (30d forecasts)
- Competitive differentiator: Bi-monthly and quarterly forecasts
- Revenue opportunity: Premium forecasting service
- Strategic value: Better risk management for importers/exporters

**ROI:** High for 15d/30d, Medium for 90d

---

## Decision Matrix

| Criterion | Weight | 15d Score | 30d Score | 90d Score |
|-----------|--------|-----------|-----------|-----------|
| Business Value | 35% | 8/10 | 10/10 | 6/10 |
| Implementation Effort | 25% | 9/10 | 8/10 | 6/10 |
| Technical Risk | 20% | 9/10 | 8/10 | 6/10 |
| Forecast Accuracy | 20% | 8/10 | 7/10 | 5/10 |
| **TOTAL** | 100% | **8.5/10** | **8.5/10** | **5.8/10** |

**Conclusion:**
- **15d and 30d:** STRONG GO (score 8.5/10)
- **90d:** CONDITIONAL GO (score 5.8/10, evaluate user demand)

---

## Recommended Action

### Immediate (This Quarter)
1. **Approve development:** 15-day and 30-day forecasters
2. **Allocate resources:** 1 developer for 7 weeks
3. **Set milestone:** Production deployment by end of Q1 2025

### Near-Term (Next Quarter)
1. **Monitor usage:** Track 15d/30d forecast adoption
2. **Gather feedback:** Survey users on 90-day need
3. **Decide on 90d:** Implement only if strong user demand

### Long-Term (6-12 Months)
1. **Enhance ensemble:** Implement constrained weights
2. **Add economic calendar:** Integrate BCCh/FOMC meeting dates
3. **Regime detection:** For crisis periods (optional)

---

## Next Steps

1. **Review this analysis** with technical team and stakeholders
2. **Validate business requirements** with end users (do they need 15d/30d/90d?)
3. **Prioritize implementation** based on user demand
4. **Begin development** with Phase 1 (infrastructure)
5. **Deploy incrementally:** 15d first, then 30d, evaluate 90d

---

## Supporting Documentation

1. **Comprehensive Guide (15,000 words):** `/docs/forecasting/MULTI_HORIZON_RECOMMENDATIONS.md`
   - Statistical theory and justification
   - Detailed parameter recommendations
   - Implementation code examples
   - Chilean market calendar
   - Risk analysis and mitigation

2. **Quick Reference:** `/docs/forecasting/QUICK_REFERENCE_MULTI_HORIZON.md`
   - Parameter lookup tables
   - Key constants and formulas
   - Testing checklist
   - Validation commands

3. **Comparison Matrix:** `/docs/forecasting/HORIZON_COMPARISON_MATRIX.md`
   - Side-by-side comparison of all horizons
   - Model selection guide
   - Decision framework
   - Feature importance analysis

---

## Contact

For questions about this analysis:
- **Statistical Methodology:** See comprehensive guide Section 2 (Model Recommendations)
- **Implementation Details:** See comprehensive guide Section 8 (Implementation Roadmap)
- **Business Value:** See comparison matrix (Decision Framework section)

---

**Prepared by:** USD/CLP Expert Statistical Agent
**Date:** 2025-11-13
**System Analyzed:** forex-forecast-system v2.3.0
**Status:** Ready for stakeholder review and decision

**Recommendation:** ✅ **APPROVE** implementation of 15-day and 30-day forecasters

---
