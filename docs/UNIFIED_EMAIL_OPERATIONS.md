# Unified Email System - Operations and Maintenance Guide

**Version:** 1.0
**Date:** 2025-11-13
**Audience:** Operations, DevOps, System Administrators

---

## Overview

This guide covers day-to-day operations, monitoring, maintenance, and troubleshooting of the unified email system in production.

**Quick Facts:**
- **Environment:** Vultr VPS
- **User:** deployer
- **Location:** `/home/deployer/forex-forecast-system`
- **Schedule:** Mon/Wed/Thu/Fri 7:30 AM Santiago time
- **Log Location:** `/home/deployer/forex-forecast-system/logs/unified_email*.log`
- **Configuration:** `/home/deployer/forex-forecast-system/config/email_strategy.yaml`

---

## Daily Operations

### Morning Checks (Before 7:30 AM)

1. **System Health**
   ```bash
   ssh reporting
   cd /home/deployer/forex-forecast-system

   # Check disk space
   df -h | grep home

   # Check recent logs
   tail -20 logs/unified_email.log

   # Verify cron is running
   pgrep -f "send_daily_email" || echo "Not running (OK if before schedule)"
   ```

2. **Configuration Verification**
   ```bash
   # Check today's schedule
   date +%u  # Should return day of week

   # What should send today?
   grep -A 5 "days_of_week" config/email_strategy.yaml
   ```

### Post-Execution Verification (After 8:00 AM)

1. **Check Execution Status**
   ```bash
   # View latest log file
   ls -lh logs/unified_email*.log | tail -1

   # Check for success
   tail -10 logs/unified_email.log | grep -E "SUCCESS|FAIL"

   # Full execution log
   tail -100 logs/unified_email.log
   ```

2. **Verify Email Delivery**
   ```bash
   # Check Gmail logs (if available)
   grep "gmail\|email" logs/unified_email.log | tail -10

   # Look for SMTP errors
   grep -i "smtp\|error\|fail" logs/unified_email.log
   ```

3. **Check System Resources**
   ```bash
   # Memory usage during execution
   free -h

   # CPU load
   uptime

   # Disk usage increase
   du -sh data/ reports/ logs/
   ```

---

## Weekly Monitoring

### Every Monday Morning

1. **Week Schedule Review**
   ```bash
   # Display entire week schedule
   echo "Weekly Schedule:"
   echo "Monday (1): Mon, Wed, Fri → 7d, 15d"
   echo "Wednesday (3): → 7d"
   echo "Thursday (4): → 15d"
   echo "Friday (5): → 7d, 30d, summary"
   ```

2. **Log Review and Cleanup**
   ```bash
   # Archive previous week logs
   mkdir -p logs/archive/
   mv logs/unified_email_2025-11-0[6-7]*.log logs/archive/ 2>/dev/null

   # Compress archived logs
   gzip logs/archive/unified_email*.log

   # Count this week's successes
   grep "SUCCESS" logs/unified_email_2025-11-1[0-2]*.log | wc -l
   ```

3. **Performance Trending**
   ```bash
   # Extract execution times from logs
   grep -h "Total time" logs/unified_email_2025-11-1[0-2]*.log | \
     sed 's/.*Total time: //g' | \
     awk '{sum+=$1; count++} END {print "Avg:", sum/count, "s"}'
   ```

4. **Error Analysis**
   ```bash
   # Find all errors from past week
   grep -h "ERROR\|FAIL" logs/unified_email_2025-11-1[0-2]*.log

   # Count errors by type
   grep -h "ERROR:" logs/unified_email_2025-11-1[0-2]*.log | \
     cut -d: -f2 | sort | uniq -c
   ```

### Every Friday EOD

1. **Weekly Summary Report**
   ```bash
   #!/bin/bash
   # Create weekly summary

   WEEK_START="2025-11-10"
   WEEK_END="2025-11-14"

   echo "=== Weekly Email System Report ==="
   echo "Week: $WEEK_START to $WEEK_END"
   echo

   echo "Executions:"
   ls -1 logs/unified_email_2025-11-1[0-4]*.log | wc -l

   echo "Successes:"
   grep "SUCCESS" logs/unified_email_2025-11-1[0-4]*.log | wc -l

   echo "Failures:"
   grep "ERROR\|FAIL" logs/unified_email_2025-11-1[0-4]*.log | wc -l

   echo "Email sizes (MB):"
   ls -lh data/sent_emails/2025-11-1[0-4]*.eml | awk '{print $5}' | \
     paste -sd+ | bc

   echo "Status: $(grep 'SUCCESS' logs/unified_email_2025-11-1[0-4]*.log | wc -l)/4 emails sent"
   ```

2. **Recipient Feedback Check**
   - Ask: Did emails arrive on time?
   - Ask: Were PDFs included when expected?
   - Ask: Any formatting issues?
   - Document any issues for fixes

---

## Monthly Maintenance

### First of Month

1. **Full System Audit**
   ```bash
   # Check disk usage
   du -sh /home/deployer/forex-forecast-system/{data,logs,reports}

   # Verify all critical files present
   ls -l config/email_strategy.yaml
   ls -l src/forex_core/notifications/unified_email.py
   ls -l scripts/send_daily_email.sh

   # Check file permissions
   stat config/email_strategy.yaml | grep Access
   stat scripts/send_daily_email.sh | grep Access
   ```

2. **Cron Job Verification**
   ```bash
   # Display current cron schedule
   crontab -l | grep -E "email|send_daily"

   # Verify syntax is correct
   grep -E "^[0-9].*send_daily_email" <(crontab -l)

   # Calculate next 3 executions
   date
   echo "Next Monday: $(date -d 'next Monday' '+%Y-%m-%d %H:%M')"
   echo "Next Wednesday: $(date -d 'next Wednesday' '+%Y-%m-%d %H:%M')"
   echo "Next Thursday: $(date -d 'next Thursday' '+%Y-%m-%d %H:%M')"
   echo "Next Friday: $(date -d 'next Friday' '+%Y-%m-%d %H:%M')"
   ```

3. **Log Rotation**
   ```bash
   # Archive logs older than 30 days
   find logs/ -name "unified_email*.log" -mtime +30 -exec \
     mv {} logs/archive/ \;

   # Compress archived logs
   gzip logs/archive/*.log

   # Calculate disk freed
   du -sh logs/archive/
   ```

4. **Configuration Backup**
   ```bash
   # Backup current configuration
   cp config/email_strategy.yaml \
      config/backups/email_strategy_$(date +%Y%m%d).yaml

   # Keep last 3 backups
   ls -t config/backups/email_strategy*.yaml | tail -n +4 | xargs rm -f
   ```

5. **Metrics Summary**
   ```bash
   # Execution stats for past month
   echo "=== November Metrics ==="
   echo "Total executions:"
   ls logs/unified_email_2025-11*.log | wc -l

   echo "Success rate:"
   SUCCESS=$(grep "SUCCESS" logs/unified_email_2025-11*.log | wc -l)
   TOTAL=$(ls logs/unified_email_2025-11*.log | wc -l)
   echo "scale=2; $SUCCESS / $TOTAL * 100" | bc

   echo "Total emails sent:"
   grep "Successfully sent" logs/unified_email_2025-11*.log | wc -l

   echo "Average execution time (seconds):"
   grep -h "completed in" logs/unified_email_2025-11*.log | \
     sed 's/.*in //g; s/ seconds.*//' | \
     awk '{sum+=$1; count++} END {print sum/count}'

   echo "PDFs attached:"
   grep "with PDF" logs/unified_email_2025-11*.log | wc -l
   ```

### Mid-Month (15th)

1. **Performance Review**
   ```bash
   # Check for performance degradation
   FIRST_HALF=$(grep "completed in" logs/unified_email_2025-11-0[1-7]*.log | \
                 sed 's/.*in //g; s/ seconds.*//' | \
                 awk '{sum+=$1; count++} END {print sum/count}')

   echo "First half avg execution time: ${FIRST_HALF} seconds"
   echo "Target: <3 seconds"

   if (( $(echo "$FIRST_HALF > 5" | bc -l) )); then
     echo "WARNING: Performance degradation detected"
   fi
   ```

2. **Update Health Check**
   ```bash
   # Verify all integrations still working
   python3 -c "
   from src.forex_core.data.prediction_tracker import PredictionTracker
   pt = PredictionTracker()
   print('PredictionTracker: OK')

   from src.forex_core.monitoring.performance import PerformanceMonitor
   pm = PerformanceMonitor()
   print('PerformanceMonitor: OK')
   "
   ```

---

## Troubleshooting Guide

### Issue: Email Not Sent Expected Day

**Diagnosis:**
```bash
# Step 1: Check if script ran
grep "2025-11-XX" logs/unified_email*.log
# Expected: Log entry for that date

# Step 2: Check schedule day
date +%u
# Expected: 1 (Mon), 3 (Wed), 4 (Thu), or 5 (Fri)

# Step 3: Verify cron configuration
crontab -l | grep "send_daily"
# Expected: 30 7 * * 1,3,4,5
```

**Solutions:**
1. If no log entry: Cron didn't execute
   - Check: `service cron status`
   - Check system time: `timedatectl`
   - Restart cron: `sudo systemctl restart cron`

2. If wrong day: Day calculation error
   - Check: `date` command gives correct day
   - Verify timezone: `timedatectl | grep "Time zone"`
   - Manually test: `./scripts/send_daily_email.sh`

3. If email not delivered:
   - Check Gmail account not disabled
   - Check recipient emails valid
   - Verify PYTHONPATH set correctly

### Issue: Email Has Wrong Content

**Diagnosis:**
```bash
# Check what horizons were included
grep "Horizons to send:" logs/unified_email*.log | tail -5

# Expected for Monday: [7d, 15d]
# Expected for Wednesday: [7d]
# etc.

# Check strategy configuration
grep -A 5 "days_of_week\|days_of_month" config/email_strategy.yaml
```

**Solutions:**
1. If horizons wrong: Configuration mismatch
   - Edit `config/email_strategy.yaml`
   - Verify days_of_week arrays
   - Test with: `./scripts/test_unified_email.sh`

2. If data stale: PredictionTracker has no new data
   - Check: `head -5 data/predictions_tracker.csv`
   - Verify forecast generation ran
   - Check forecast logs: `tail logs/7d_forecast*.log`

3. If formatting broken: HTML generation error
   - Test locally: `python -m src.forex_core.notifications.email_builder`
   - Check: Email client settings (may be stripping CSS)
   - Try different email client (Gmail, Outlook, etc.)

### Issue: PDF Not Attached When Expected

**Diagnosis:**
```bash
# Check PDF attachment logic in logs
grep "PDF\|attachment" logs/unified_email.log

# Check what rules triggered
grep "price change\|volatility\|alert" logs/unified_email.log
```

**Solutions:**
1. Check attachment rules in `config/email_strategy.yaml`:
   ```yaml
   pdf_attachment:
     price_change_threshold: 1.5  # Adjust if needed
   ```

2. Verify price change calculation:
   ```bash
   grep "change_pct\|Change:" logs/unified_email.log
   # Expected: 1.5%+ for conditional attachment
   ```

3. Verify horizon in always_attach:
   ```yaml
   always_attach: ["30d", "90d", "12m"]
   # Check if your horizon is listed
   ```

### Issue: Script Fails with "PYTHONPATH: unbound variable"

**Diagnosis:**
```bash
# Check PYTHONPATH in script
grep PYTHONPATH scripts/send_daily_email.sh
# Should show: export PYTHONPATH="${PROJECT_DIR}/src:${PYTHONPATH:-}"
```

**Solution:**
If missing `:-` syntax:
```bash
# Edit script
nano scripts/send_daily_email.sh

# Change:
# export PYTHONPATH="${PROJECT_DIR}/src:${PYTHONPATH}"
# To:
# export PYTHONPATH="${PROJECT_DIR}/src:${PYTHONPATH:-}"

# Save and restart cron
sudo systemctl restart cron
```

### Issue: SMTP Authentication Fails

**Diagnosis:**
```bash
# Check error in logs
grep -i "smtp\|auth\|gmail\|password" logs/unified_email.log
```

**Common Causes:**
1. Gmail password expired or changed
2. Gmail app password revoked
3. Two-factor authentication enabled without app password
4. Credentials not set in `.env`

**Solutions:**
```bash
# Check if credentials present
grep -E "GMAIL_USER|GMAIL_APP_PASSWORD" .env | wc -l
# Expected: 2 (both present)

# If missing or incorrect:
nano .env
# Update credentials from password manager

# Test email manually
python3 -c "
from src.forex_core.notifications.email import EmailSender
sender = EmailSender()
sender.send_test_email()
"
```

### Issue: Email Size Too Large

**Diagnosis:**
```bash
# Check email file size
ls -lh data/sent_emails/latest.eml 2>/dev/null || echo "No sent emails saved"

# Check what's included
grep -i "pdf\|attachment" logs/unified_email.log | tail -5
```

**Solutions:**
1. Disable unnecessary PDFs in `config/email_strategy.yaml`:
   ```yaml
   pdf_attachment:
     conditional_rules:
       high_volatility: false  # Disable
   ```

2. Reduce content in HTML:
   - Edit `src/forex_core/notifications/email_builder.py`
   - Reduce driver count: `max_drivers: 3` → `max_drivers: 2`

3. Compress images in templates:
   - Use smaller resolution charts
   - Convert to WebP format (if client supports)

### Issue: Cron Not Executing at All

**Diagnosis:**
```bash
# Check if cron daemon running
sudo systemctl status cron

# Check cron logs
sudo tail -50 /var/log/syslog | grep CRON

# Check if job exists
crontab -l | grep "send_daily"
```

**Solutions:**
1. Start cron if stopped:
   ```bash
   sudo systemctl start cron
   ```

2. Add job if missing:
   ```bash
   crontab -e
   # Add line: 30 7 * * 1,3,4,5 cd /home/deployer/forex-forecast-system && ./scripts/send_daily_email.sh >> logs/unified_email.log 2>&1
   ```

3. Check file permissions:
   ```bash
   ls -l scripts/send_daily_email.sh
   # Should show: -rwxr-xr-x (755)

   # If not, fix:
   chmod +x scripts/send_daily_email.sh
   ```

---

## Performance Tuning

### Monitor Execution Time

```bash
# Extract all execution times
grep -h "completed in" logs/unified_email*.log | \
  sed 's/.*in //g; s/ seconds.*//' > /tmp/times.txt

# Calculate statistics
awk '{
  sum += $1
  count++
  if (NR==1 || $1 < min) min = $1
  if (NR==1 || $1 > max) max = $1
}
END {
  print "Min:", min, "seconds"
  print "Max:", max, "seconds"
  print "Avg:", sum/count, "seconds"
  print "Runs:", count
}' /tmp/times.txt
```

### Identify Slow Components

**If execution time > 5 seconds:**

1. Check data loading time:
   ```bash
   grep "Loading predictions\|Loading system health" logs/unified_email.log | tail -2
   ```

2. Check HTML generation time:
   ```bash
   grep "Building HTML\|HTML generated" logs/unified_email.log | tail -2
   ```

3. Check SMTP sending time:
   ```bash
   grep "Sending email\|Email sent" logs/unified_email.log | tail -2
   ```

**Optimization options:**
- Cache system health data (save ~0.5s)
- Reduce data validation (save ~0.3s)
- Async SMTP sending (save ~1.0s, non-blocking)

---

## Backup and Recovery

### Regular Backups

**Weekly backup script:**
```bash
#!/bin/bash
# Backup unified email system

BACKUP_DIR="/home/deployer/forex-forecast-system/backups"
TIMESTAMP=$(date +%Y%m%d)

mkdir -p "$BACKUP_DIR"

# Backup configuration
tar -czf "$BACKUP_DIR/email_config_$TIMESTAMP.tar.gz" config/email_strategy.yaml

# Backup code
tar -czf "$BACKUP_DIR/email_code_$TIMESTAMP.tar.gz" \
  src/forex_core/notifications/unified_email.py \
  src/forex_core/notifications/email_builder.py

# Backup logs (last 7 days)
find logs -name "unified_email*.log" -mtime -7 -exec \
  tar -czf "$BACKUP_DIR/email_logs_$TIMESTAMP.tar.gz" {} \;

# Clean old backups (>30 days)
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $(du -sh $BACKUP_DIR | cut -f1)"
```

### Recovery Procedures

**If configuration corrupted:**
```bash
# Restore from backup
cp backups/email_config_20251110.tar.gz .
tar -xzf email_config_20251110.tar.gz
# No restart needed (picked up at next execution)
```

**If script corrupted:**
```bash
# Restore from backup
cp backups/email_code_20251110.tar.gz .
tar -xzf email_code_20251110.tar.gz

# Verify
python3 -m py_compile src/forex_core/notifications/unified_email.py

# Test
./scripts/test_unified_email.sh
```

---

## Alert and Escalation

### Create Alert Rules

**Monitoring service (e.g., Nagios, Prometheus):**

```bash
# Alert if execution took >5 seconds
if grep "completed in [5-9]\|completed in [0-9][0-9]" logs/unified_email.log; then
  # Send Slack/email alert: Slow execution detected
fi

# Alert if any failures
if grep "ERROR\|FAIL" logs/unified_email.log; then
  # Send Slack/email alert: Execution failed
fi

# Alert if no execution today
if ! ls logs/unified_email_$(date +%Y-%m-%d)*.log 2>/dev/null; then
  # Send Slack/email alert: No execution recorded
fi
```

### Escalation Contacts

**For immediate issues:**
- Ops Team: ops@company.com
- Developer: rafael@cavara.cl

**For non-critical issues:**
- Create GitHub issue
- Document in ops log
- Review in weekly meeting

---

## Change Management

### Process for Configuration Changes

1. **Planning**
   - Document desired change
   - Identify affected systems
   - Plan rollback procedure

2. **Testing**
   - Make change locally
   - Run `./scripts/test_unified_email.sh`
   - Verify email generation

3. **Staging**
   - Apply to staging server (if available)
   - Run full test suite
   - Verify no side effects

4. **Production**
   - Apply change during low-traffic window (evening)
   - Monitor logs for next execution
   - Be ready to rollback

5. **Documentation**
   - Update `config/email_strategy.yaml` comments
   - Document rationale in git commit
   - Add entry to change log

**Example: Change send time**
```bash
# 1. Edit config
nano config/email_strategy.yaml
# Change: default_send_time: "07:30" → "08:00"

# 2. Test
./scripts/test_unified_email.sh

# 3. Update cron
crontab -e
# Change: 30 7 → 0 8

# 4. Verify
crontab -l | grep send_daily

# 5. Document
echo "Changed send time from 7:30 to 8:00 AM per request" > CHANGELOG_$(date +%Y%m%d).txt
```

---

## Documentation and Runbooks

### Create a Runbook for Common Tasks

**Daily check runbook:**
```bash
#!/bin/bash
# Daily check - run each morning

echo "=== Daily Email System Check ==="
echo "Time: $(date)"
echo

echo "1. Check latest execution:"
tail -3 logs/unified_email.log | grep -E "SUCCESS|ERROR"
echo

echo "2. Check today's schedule:"
DAY=$(date +%u)
case $DAY in
  1) echo "Today is Monday - should send 7d, 15d" ;;
  3) echo "Today is Wednesday - should send 7d" ;;
  4) echo "Today is Thursday - should send 15d" ;;
  5) echo "Today is Friday - should send 7d, 30d" ;;
  *) echo "Today is $DAY - no regular email scheduled" ;;
esac
echo

echo "3. Check system health:"
df -h /home/deployer | grep -v Filesystem
echo

echo "Check complete."
```

---

## Summary

This operations guide provides everything needed to:
- Monitor daily execution
- Perform weekly reviews
- Execute monthly maintenance
- Troubleshoot common issues
- Optimize performance
- Manage backups and recovery
- Handle changes safely

**Key takeaways:**
1. Check logs daily at `/home/deployer/forex-forecast-system/logs/`
2. Verify execution within 15 minutes of schedule
3. Archive logs monthly
4. Test changes before applying to production
5. Keep configuration backed up
6. Monitor trends for performance degradation
7. Document all changes

---

**Document Version:** 1.0
**Last Updated:** 2025-11-13
**Maintained By:** Operations Team
**Review Frequency:** Monthly or when procedures change
