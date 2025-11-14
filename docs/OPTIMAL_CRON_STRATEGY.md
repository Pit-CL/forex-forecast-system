# USD/CLP Forex Forecast System - Optimal Cron Strategy
## Market-Driven Email Delivery and System Operations

---

## Executive Summary

This document defines the optimal scheduling strategy for the USD/CLP forecasting system based on market behavior patterns, user decision cycles, and Chilean corporate treasury operations. All times are in Chile time (America/Santiago).

---

## 📊 Market Context and User Behavior Analysis

### Chilean FX Market Timeline (Daily)

```
06:00 - Asian session closing influences
08:00 - Chilean corporate treasurers arrive
09:00 - BCCh repo operations begin
09:30 - Local FX market opens actively
10:00 - Peak corporate hedging decisions
11:00 - Central bank monitoring reports
13:00 - BCCh publishes official USD/CLP rate
14:00 - Main FX trading session closes
15:00 - Settlement cutoff for same-day operations
16:00 - International desk handover to NY
17:00 - After-market analysis available
18:00 - Complete daily data available
20:00 - NY session influences (Fed announcements)
```

### Decision-Making Patterns

**Corporate Treasurers:**
- Check emails: 08:00-09:00 (arrival), 14:00-15:00 (post-lunch)
- Make hedging decisions: 09:30-11:00 (morning), 15:00-16:00 (afternoon)
- Weekly planning: Monday mornings
- Monthly reviews: First week of month

**Portfolio Managers:**
- Review positions: 07:30-08:30 (pre-market)
- Rebalancing: Tuesday/Thursday (avoiding Monday volatility, Friday flows)
- Strategic reviews: Monthly, typically first Tuesday

**Risk Managers:**
- Daily VaR checks: 08:00 sharp
- Weekly risk reports: Friday afternoons
- Monthly risk committees: First Thursday

---

## 🎯 Optimal Email Delivery Strategy

### Core Principles

1. **Morning Delivery Window**: 07:30 AM Chile time
   - Users check email upon arrival (08:00-09:00)
   - Time to digest before market open (09:30)
   - Actionable for morning decisions

2. **Frequency Optimization**: Less is more
   - Avoid email fatigue
   - Each email must add value
   - Consolidate related horizons

3. **Day-of-Week Logic**:
   - **Monday**: Planning day (comprehensive view)
   - **Wednesday**: Mid-week tactical update
   - **Thursday**: Forward-looking preparation
   - **Friday**: Weekly wrap-up and monthly positioning

### Recommended Schedule

#### **MONDAY - 07:30 AM**
**Comprehensive Weekly Planning Email**
- ✅ 7-day forecast (tactical week ahead)
- ✅ 15-day forecast (two-week horizon)
- 📎 PDF attachments: Both reports
- **Rationale**: Monday morning planning meetings need complete picture

#### **WEDNESDAY - 07:30 AM**
**Mid-Week Tactical Update**
- ✅ 7-day forecast only
- 📎 PDF: Only if volatility > 2% or significant change
- **Rationale**: Quick tactical check, minimal interruption

#### **THURSDAY - 07:30 AM**
**Strategic Positioning Update**
- ✅ 15-day forecast (refreshed mid-term view)
- ✅ 30-day forecast (IF 1st or 15th of month)
- 📎 PDF: 15d always, 30d if included
- **Rationale**: Preparation for Friday flows and month-end positioning

#### **FRIDAY - 07:30 AM**
**Weekly Summary & Monthly Outlook**
- ✅ 7-day forecast (weekend and next week)
- ✅ 30-day forecast (monthly view)
- ✅ Weekly performance summary
- 📎 PDF: Both reports + weekly summary
- **Rationale**: Complete weekly wrap-up for reporting

#### **FIRST TUESDAY OF MONTH - 07:30 AM**
**Quarterly Strategic Review**
- ✅ 90-day forecast
- ✅ Monthly performance review
- 📎 PDF: Comprehensive quarterly report
- **Rationale**: Monthly risk committees and strategic planning

---

## ⚙️ Complete Cron Configuration

### Email Delivery Crons (Inside Docker Containers)

```bash
# 7-DAY FORECAST CONTAINER (forex-7d)
# File: cron/7d/crontab

# Forecast generation - Daily at 18:30 Chile (after market data complete)
30 21 * * 1-5 cd /app && PYTHONPATH=/app/src python /app/scripts/forecast_with_ensemble.py --horizon 7 >> /var/log/cron.log 2>&1

# Email delivery - Monday, Wednesday, Friday at 07:30 Chile
30 10 * * 1,3,5 cd /app && PYTHONPATH=/app/src python /app/scripts/send_unified_email.py --horizon 7d >> /var/log/cron.log 2>&1

# Weekly XGBoost re-training - Sunday 02:00 Chile
0 5 * * 0 cd /app && PYTHONPATH=/app/src python /app/scripts/auto_retrain_xgboost.py --horizon 7 >> /var/log/cron.log 2>&1

# Health check
0 * * * * date > /tmp/healthcheck
```

```bash
# 15-DAY FORECAST CONTAINER (forex-15d)
# File: cron/15d/crontab

# Forecast generation - Daily at 18:30 Chile
30 21 * * 1-5 cd /app && PYTHONPATH=/app/src python /app/scripts/forecast_with_ensemble.py --horizon 15 >> /var/log/cron.log 2>&1

# Email delivery - Monday and Thursday at 07:30 Chile
30 10 * * 1,4 cd /app && PYTHONPATH=/app/src python /app/scripts/send_unified_email.py --horizon 15d >> /var/log/cron.log 2>&1

# Weekly XGBoost re-training - Sunday 02:30 Chile
30 5 * * 0 cd /app && PYTHONPATH=/app/src python /app/scripts/auto_retrain_xgboost.py --horizon 15 >> /var/log/cron.log 2>&1

# Health check
0 * * * * date > /tmp/healthcheck
```

```bash
# 30-DAY FORECAST CONTAINER (forex-30d)
# File: cron/30d/crontab

# Forecast generation - Daily at 18:30 Chile
30 21 * * 1-5 cd /app && PYTHONPATH=/app/src python /app/scripts/forecast_with_ensemble.py --horizon 30 >> /var/log/cron.log 2>&1

# Email delivery - Thursdays (1st & 15th) and Fridays at 07:30 Chile
30 10 1,15 * 4 cd /app && PYTHONPATH=/app/src python /app/scripts/send_unified_email.py --horizon 30d >> /var/log/cron.log 2>&1
30 10 * * 5 cd /app && PYTHONPATH=/app/src python /app/scripts/send_unified_email.py --horizon 30d >> /var/log/cron.log 2>&1

# Weekly XGBoost re-training - Sunday 03:00 Chile
0 6 * * 0 cd /app && PYTHONPATH=/app/src python /app/scripts/auto_retrain_xgboost.py --horizon 30 >> /var/log/cron.log 2>&1

# Monthly SARIMAX re-training - 1st of month, 01:00 Chile
0 4 1 * * cd /app && PYTHONPATH=/app/src python /app/scripts/auto_retrain_sarimax.py --horizon 30 >> /var/log/cron.log 2>&1

# Health check
0 * * * * date > /tmp/healthcheck
```

```bash
# 90-DAY FORECAST CONTAINER (forex-90d)
# File: cron/90d/crontab

# Forecast generation - Weekly on Sundays at 22:00 Chile
0 1 * * 1 cd /app && PYTHONPATH=/app/src python /app/scripts/forecast_with_ensemble.py --horizon 90 >> /var/log/cron.log 2>&1

# Email delivery - First Tuesday of month at 07:30 Chile
30 10 1-7 * 2 cd /app && PYTHONPATH=/app/src python /app/scripts/send_unified_email.py --horizon 90d >> /var/log/cron.log 2>&1

# Monthly XGBoost re-training - 1st Sunday of month, 03:30 Chile
30 6 1-7 * 0 cd /app && PYTHONPATH=/app/src python /app/scripts/auto_retrain_xgboost.py --horizon 90 >> /var/log/cron.log 2>&1

# Monthly SARIMAX re-training - 1st of month, 02:00 Chile
0 5 1 * * cd /app && PYTHONPATH=/app/src python /app/scripts/auto_retrain_sarimax.py --horizon 90 >> /var/log/cron.log 2>&1

# Health check
0 * * * * date > /tmp/healthcheck
```

### Unified Email Orchestrator (Optional Central Container)

```bash
# UNIFIED EMAIL CONTAINER (forex-email)
# This is an alternative approach using a dedicated email container
# File: cron/email/crontab

# Unified email delivery - Market days at 07:30 Chile
30 10 * * 1,3,4,5 cd /app && ./scripts/send_daily_email.sh >> /var/log/cron.log 2>&1

# First Tuesday quarterly email - 07:30 Chile
30 10 1-7 * 2 cd /app && PYTHONPATH=/app/src python /app/scripts/send_unified_email.py --quarterly >> /var/log/cron.log 2>&1

# Weekly summary generation - Fridays at 17:00 Chile
0 20 * * 5 cd /app && PYTHONPATH=/app/src python /app/scripts/generate_weekly_summary.py >> /var/log/cron.log 2>&1

# Health check
0 * * * * date > /tmp/healthcheck
```

---

## 🏗️ Infrastructure Philosophy: Docker-First Architecture

### Core Principles

1. **ALL application crons MUST be inside Docker containers**
   - Ensures reproducibility
   - Simplifies deployment
   - Version controlled
   - Environment isolation

2. **Host system crons are ONLY for infrastructure**
   - System backups
   - Docker health monitoring
   - Log rotation
   - Security updates

3. **No forex-forecast-system crons on host**
   - Violates containerization principle
   - Creates deployment inconsistencies
   - Harder to maintain

### Host System Cron Audit

#### Commands to Check Host Crons

```bash
# Check current user's crontab
crontab -l

# Check system-wide crons
sudo ls -la /etc/cron.* /etc/cron.d/

# Check for any forex-related crons
sudo grep -r "forex" /etc/cron* /var/spool/cron/

# List all user crontabs
sudo ls -la /var/spool/cron/crontabs/
```

#### Crons to REMOVE from Host

```bash
# Remove any of these patterns if found:
# - */forecast_with_ensemble.py
# - */auto_retrain_*.py
# - */send_*_email.py
# - */daily_dashboard.sh
# - Any path containing "forex-forecast-system"

# To remove from current user:
crontab -e  # Then delete the lines

# To remove from root:
sudo crontab -e  # Then delete the lines

# To remove from /etc/cron.d/:
sudo rm /etc/cron.d/forex-*  # If any exist
```

#### Crons to KEEP on Host

```bash
# Example acceptable host crons:

# Daily backup of Docker volumes
0 2 * * * /usr/local/bin/backup-docker-volumes.sh

# Docker system prune weekly
0 3 * * 0 docker system prune -af

# Monitor Docker health
*/5 * * * * /usr/local/bin/check-docker-health.sh

# Certbot SSL renewal (if applicable)
0 0,12 * * * /usr/bin/certbot renew --quiet
```

---

## 📈 Performance Metrics and Optimization

### Email Engagement Tracking

Monitor these KPIs:
- Open rates by day/time
- Click-through rates on PDF attachments
- Time-to-open after delivery
- Unsubscribe rates

### Forecast Accuracy Windows

- **7-day**: Most accurate 1-3 days ahead
- **15-day**: Reliable 5-10 days ahead
- **30-day**: Best for 15-25 day window
- **90-day**: Directional bias more important than point forecast

### Resource Optimization

```bash
# Stagger compute-intensive tasks
# 18:30 - Generate 7d, 15d forecasts
# 19:00 - Generate 30d forecast
# 22:00 - Generate 90d forecast (weekly)
# 02:00 - Model retraining (overnight)
# 07:30 - Email delivery (low compute)
```

---

## 🚨 Critical System Alerts

### When to Send IMMEDIATE Alerts (Outside Schedule)

1. **Volatility Spike**: USD/CLP moves >3% intraday
2. **BCCh Intervention**: Central bank announces FX operations
3. **System Degradation**: Model accuracy drops >20%
4. **Data Feed Issues**: Missing >2 hours of data
5. **Copper Flash Crash**: >10% move in copper prices

### Alert Delivery Mechanism

```python
# Separate alert system (not in regular crons)
# Runs every 15 minutes during market hours
*/15 9-17 * * 1-5 cd /app && python /app/scripts/check_alerts.py

# Alert criteria:
# - Volatility: 20-day realized vol > 2.5 std from mean
# - Price: Breaks 2-std Bollinger Bands
# - Volume: >3x average in 15 minutes
# - News: Critical keywords detected
```

---

## 📋 Implementation Checklist

### Phase 1: Update Docker Crontabs
- [ ] Update `cron/7d/crontab` with new schedule
- [ ] Update `cron/15d/crontab` with new schedule
- [ ] Update `cron/30d/crontab` with new schedule
- [ ] Update `cron/90d/crontab` with new schedule
- [ ] Test cron expressions with `cronitor` or similar

### Phase 2: Clean Host System
- [ ] Audit current host crontabs
- [ ] Remove forex-related crons from host
- [ ] Document remaining infrastructure crons
- [ ] Set up monitoring for Docker container crons

### Phase 3: Update Email Logic
- [ ] Modify `unified_email.py` WEEKLY_STRATEGY
- [ ] Update PDF attachment logic
- [ ] Implement volatility-based PDF decisions
- [ ] Add weekly summary generation

### Phase 4: Deploy and Monitor
- [ ] Rebuild Docker images with new crontabs
- [ ] Deploy to staging environment
- [ ] Monitor for 1 week in staging
- [ ] Deploy to production
- [ ] Track email engagement metrics

---

## 📊 Expected Outcomes

### Efficiency Gains
- **50% reduction** in total emails sent
- **75% increase** in email open rates
- **Better decision timing** aligned with market hours
- **Reduced infrastructure load** during peak hours

### User Benefits
- **No email fatigue** - Maximum 4 emails per week
- **Actionable timing** - Emails arrive when needed
- **Relevant content** - Each email has clear purpose
- **Professional rhythm** - Predictable, reliable schedule

---

## 🔄 Continuous Improvement

### Monthly Review Metrics
1. Email engagement statistics
2. Forecast accuracy by horizon
3. System resource utilization
4. User feedback and requests

### Quarterly Adjustments
- Seasonal patterns (summer/winter time changes)
- Market regime changes
- User behavior evolution
- Model performance drift

---

## 📞 Support and Maintenance

### Monitoring Commands

```bash
# Check Docker container crons are running
docker exec forex-7d crontab -l
docker exec forex-15d crontab -l
docker exec forex-30d crontab -l
docker exec forex-90d crontab -l

# Check last execution
docker exec forex-7d tail -100 /var/log/cron.log

# Monitor email queue
docker logs forex-email --tail 50 -f
```

### Troubleshooting

```bash
# If crons not executing:
# 1. Check container timezone
docker exec forex-7d date

# 2. Verify cron service is running
docker exec forex-7d service cron status

# 3. Check permissions
docker exec forex-7d ls -la /app/scripts/

# 4. Test script manually
docker exec forex-7d bash -c "cd /app && PYTHONPATH=/app/src python /app/scripts/forecast_with_ensemble.py --horizon 7"
```

---

## ✅ Final Recommendations

### Immediate Actions
1. **Implement new email schedule** focusing on 07:30 AM delivery
2. **Remove ALL forex crons from host system**
3. **Update Docker crontabs** with market-optimized timing

### Strategic Priorities
1. **User-centric scheduling** over data availability
2. **Quality over quantity** in email frequency
3. **Containerization** for all application logic
4. **Continuous monitoring** of engagement metrics

### Success Metrics (30 days)
- [ ] >80% email open rate
- [ ] Zero missed forecasts
- [ ] <5% unsubscribe rate
- [ ] 100% containerized crons

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-14
**Author**: USD/CLP Market Strategy Expert
**Review Cycle**: Monthly

---

## Appendix A: Time Zone Conversions

```
Chile Summer (Oct-Mar): UTC-3
Chile Winter (Apr-Sep): UTC-4

Key conversions (Summer Time):
07:30 Chile = 10:30 UTC
18:30 Chile = 21:30 UTC
00:00 Chile = 03:00 UTC

Key conversions (Winter Time):
07:30 Chile = 11:30 UTC
18:30 Chile = 22:30 UTC
00:00 Chile = 04:00 UTC
```

## Appendix B: Chilean Market Calendar 2025

Key dates affecting scheduling:
- Daylight Saving ends: First Sunday of April
- Daylight Saving starts: First Sunday of September
- Banking holidays: Check BCCh calendar
- Year-end reduced operations: Dec 24-31