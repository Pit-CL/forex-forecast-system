# Implementation Guide: Optimal Cron Strategy

## Quick Start Commands

### Step 1: Audit Host System (On Vultr Server)

```bash
# First, check what's currently on the host
sudo crontab -l
crontab -l

# Run the audit script in dry-run mode
cd /path/to/forex-forecast-system
chmod +x scripts/audit_host_crons.sh
sudo ./scripts/audit_host_crons.sh

# If forex-related crons are found, clean them
sudo ./scripts/audit_host_crons.sh --clean
```

### Step 2: Update Docker Container Crontabs

```bash
# Copy optimized crontabs over current ones
cp cron/7d/crontab.optimized cron/7d/crontab
cp cron/15d/crontab.optimized cron/15d/crontab
cp cron/30d/crontab.optimized cron/30d/crontab
cp cron/90d/crontab.optimized cron/90d/crontab

# Rebuild Docker images
docker-compose build

# Stop and restart containers with new crontabs
docker-compose down
docker-compose up -d
```

### Step 3: Verify New Schedules

```bash
# Check that crons are loaded correctly
docker exec forex-7d crontab -l
docker exec forex-15d crontab -l
docker exec forex-30d crontab -l
docker exec forex-90d crontab -l

# Monitor initial execution
docker logs -f forex-7d --tail 100
```

---

## Critical Changes Summary

### Email Delivery Times (NEW)

| Day | Time | Horizons | Purpose |
|-----|------|----------|---------|
| **Monday** | 07:30 | 7d + 15d | Weekly planning package |
| **Wednesday** | 07:30 | 7d only | Mid-week tactical update |
| **Thursday** | 07:30 | 15d + 30d* | Forward positioning (*1st & 15th only) |
| **Friday** | 07:30 | 7d + 30d | Weekly wrap & monthly view |
| **1st Tuesday/month** | 07:30 | 90d | Quarterly strategic briefing |

### Forecast Generation Times (UPDATED)

| Horizon | Generation Time | Frequency | Reasoning |
|---------|----------------|-----------|-----------|
| 7-day | 18:30 daily | Mon-Fri | After market close |
| 15-day | 18:45 daily | Mon-Fri | Staggered to avoid contention |
| 30-day | 19:00 daily | Mon-Fri | After shorter horizons |
| 90-day | 22:00 Sunday | Weekly | No need for daily updates |

### Re-training Schedule (OPTIMIZED)

| Model | Horizon | Schedule | Time (Chile) |
|-------|---------|----------|--------------|
| XGBoost | 7d | Weekly (Sun) | 02:00 |
| XGBoost | 15d | Weekly (Sun) | 02:30 |
| XGBoost | 30d | Weekly (Sun) | 03:00 |
| XGBoost | 90d | Monthly (1st Sun) | 03:30 |
| SARIMAX | 30d | Monthly (1st) | 01:00 |
| SARIMAX | 90d | Monthly (1st) | 02:00 |
| LSTM | 15d | Bi-weekly (1st & 15th) | 03:00 |
| LSTM | 30d | Monthly (2nd Sun) | 04:00 |
| LSTM | 90d | Quarterly (2nd Sun) | 04:00 |

---

## File Changes Required

### 1. Update Unified Email Strategy

Edit `src/forex_core/notifications/unified_email.py`:

```python
# Line 127-135: Update WEEKLY_STRATEGY
WEEKLY_STRATEGY = {
    0: [ForecastHorizon.H_7D, ForecastHorizon.H_15D],  # Monday
    1: [],  # Tuesday (90d on 1st Tuesday only)
    2: [ForecastHorizon.H_7D],  # Wednesday
    3: [ForecastHorizon.H_15D],  # Thursday (+ 30d on 1st & 15th)
    4: [ForecastHorizon.H_7D, ForecastHorizon.H_30D],  # Friday
    5: [],  # Saturday
    6: [],  # Sunday
}
```

### 2. Update Docker Compose

Edit `docker-compose.yml` to ensure cron service is enabled:

```yaml
services:
  forex-7d:
    build:
      context: .
      args:
        FORECAST_HORIZON: 7
    volumes:
      - ./cron/7d/crontab:/etc/cron.d/forecast-cron
    environment:
      - TZ=America/Santiago
```

### 3. Ensure Scripts Support New Parameters

Check these scripts support the new parameters:

```bash
# send_unified_email.py should support:
--horizon [7d|15d|30d|90d]
--attach-pdf
--conditional-pdf
--weekly-summary
--monthly-analysis
--quarterly-report
```

---

## Monitoring & Validation

### Daily Checks (First Week)

```bash
# Morning check - 08:00 Chile time
docker exec forex-7d tail -100 /var/log/email.log
docker exec forex-15d tail -100 /var/log/email.log

# Evening check - 19:00 Chile time
docker exec forex-7d tail -100 /var/log/cron.log
docker exec forex-30d tail -100 /var/log/cron.log
```

### Weekly Validation

```bash
# Check successful executions
docker exec forex-7d grep "SUCCESS" /var/log/email.log | tail -20
docker exec forex-15d grep "SUCCESS" /var/log/email.log | tail -20

# Check for errors
docker exec forex-7d grep "ERROR" /var/log/cron.log | tail -20

# Verify email delivery
grep "Email sent" /var/log/mail.log | tail -20
```

### Performance Metrics to Track

1. **Email Metrics** (after 30 days):
   - Open rates by day/time
   - PDF attachment downloads
   - Unsubscribe rates

2. **System Metrics**:
   - CPU usage during forecast generation
   - Memory consumption patterns
   - Disk I/O during retraining

3. **Forecast Quality**:
   - RMSE by horizon
   - Directional accuracy
   - Confidence interval calibration

---

## Rollback Plan

If issues arise, quickly revert:

```bash
# Restore original crontabs
git checkout -- cron/*/crontab

# Rebuild and restart
docker-compose build
docker-compose down
docker-compose up -d

# Restore any removed host crons (if needed)
sudo crontab -e  # Re-add necessary crons
```

---

## Common Issues & Solutions

### Issue 1: Emails Not Sending

```bash
# Check cron is running in container
docker exec forex-7d service cron status

# Restart cron service
docker exec forex-7d service cron restart

# Check environment variables
docker exec forex-7d env | grep -E "(EMAIL|SMTP)"
```

### Issue 2: Wrong Timezone

```bash
# Verify container timezone
docker exec forex-7d date

# Fix timezone
docker exec forex-7d ln -sf /usr/share/zoneinfo/America/Santiago /etc/localtime
```

### Issue 3: Resource Contention

```bash
# If forecasts are slow, stagger more:
# Edit crontabs to space out by 15 minutes
# 7d:  18:30
# 15d: 18:45
# 30d: 19:00
# 90d: 19:15
```

---

## Success Criteria (After 30 Days)

✅ **Email Delivery**
- [ ] >95% successful delivery rate
- [ ] >80% open rate
- [ ] <5% unsubscribe rate

✅ **System Performance**
- [ ] Zero missed forecasts
- [ ] <5 minute generation time for 7d/15d
- [ ] <10 minute generation time for 30d/90d

✅ **User Feedback**
- [ ] Positive feedback on timing
- [ ] No complaints about email frequency
- [ ] Increased engagement with PDFs

---

## Contact for Issues

If you encounter issues during implementation:

1. Check logs: `/var/log/cron.log`, `/var/log/email.log`
2. Review Docker logs: `docker logs [container] --tail 100`
3. Verify network connectivity for email sending
4. Ensure all environment variables are set correctly

---

**Document Version**: 1.0.0
**Implementation Date**: _________________
**Implemented By**: _________________
**Sign-off**: _________________