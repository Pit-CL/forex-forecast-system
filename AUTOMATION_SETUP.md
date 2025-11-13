# Automation Setup - Forex Forecasting System

Quick guide to set up automated monitoring and reporting.

## Prerequisites

- System deployed (locally or on Vultr)
- Python environment configured
- Dependencies installed: `pip install -r requirements.txt`
- Email credentials configured (optional, for notifications)

## Email Configuration (Optional)

If you want email notifications, configure in `.env`:

```bash
EMAIL_ENABLED=true
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password
EMAIL_RECIPIENTS=recipient1@email.com,recipient2@email.com
```

**Note:** For Gmail, you need to create an [App Password](https://support.google.com/accounts/answer/185833).

## Installation

### Quick Install (Recommended)

```bash
# Make installer executable
chmod +x scripts/install_cron_jobs.sh

# Install all cron jobs
./scripts/install_cron_jobs.sh
```

This installs:
- **Weekly Validation** - Mondays at 9:00 AM
- **Daily Dashboard** - Daily at 8:00 AM
- **Performance Check** - Daily at 10:00 AM

### Verify Installation

```bash
# View installed cron jobs
crontab -l

# Check cron log
tail -f logs/cron.log
```

### Uninstall

```bash
./scripts/install_cron_jobs.sh --uninstall
```

## Manual Execution

You can run scripts manually to test them:

### Weekly Validation

```bash
./scripts/weekly_validation.sh
# Report saved to: reports/validation/weekly_summary_YYYY-MM-DD_HH-MM-SS.txt
```

### Daily Dashboard

```bash
./scripts/daily_dashboard.sh
# Dashboard saved to: reports/daily/dashboard_YYYY-MM-DD.html
```

### Performance Check

```bash
python scripts/check_performance.py --all
# Or for specific horizon:
python scripts/check_performance.py --horizon 7d
```

### USD/CLP Calibration

```bash
# Analyze and generate calibration
python scripts/calibrate_usdclp.py analyze

# Update system configuration
python scripts/calibrate_usdclp.py update-config
```

## Scheduled Tasks

### Weekly Validation (Mondays 9:00 AM)

Runs comprehensive model validation for all horizons:
- 3-fold rolling window validation
- Generates detailed metrics (RMSE, MAE, MAPE, CI coverage)
- Sends email report if configured
- Logs: `logs/weekly_validation_*.log`
- Reports: `reports/validation/`

### Daily Dashboard (Daily 8:00 AM)

Generates and emails HTML dashboard with:
- System status
- Performance metrics per horizon
- Readiness checks
- Recent predictions summary
- HTML: `reports/daily/dashboard_*.html`

### Performance Check (Daily 10:00 AM)

Automated performance degradation detection:
- Compares recent vs baseline performance
- Statistical significance testing
- Sends alerts if degradation detected
- Console output logged to `logs/cron.log`

## Logs

All cron jobs log to:
- **Cron output**: `logs/cron.log`
- **Weekly validation**: `logs/weekly_validation_*.log`
- **Daily dashboard**: `logs/daily_dashboard_*.log`

### View Logs

```bash
# Live cron log
tail -f logs/cron.log

# Recent validation logs
ls -lt logs/weekly_validation_*.log | head -5

# View latest validation
cat logs/weekly_validation_*.log | tail -100
```

## Cleanup

Old logs and reports are automatically cleaned up:
- Cron logs: Kept for 30 days
- Validation reports: Kept for 90 days
- Dashboard HTML: Kept for 30 days

## Troubleshooting

### Cron Jobs Not Running

1. **Check crontab is installed:**
   ```bash
   crontab -l
   ```

2. **Verify scripts are executable:**
   ```bash
   ls -lh scripts/*.sh
   # Should show: -rwxr-xr-x
   ```

3. **Check cron log for errors:**
   ```bash
   tail -50 logs/cron.log
   ```

4. **Test script manually:**
   ```bash
   ./scripts/weekly_validation.sh
   # Check for errors
   ```

### Email Not Sending

1. **Verify .env configuration:**
   ```bash
   grep EMAIL .env
   ```

2. **Test email sender:**
   ```python
   from forex_core.notifications.email_sender import EmailSender

   sender = EmailSender()
   sender.send_email(
       subject="Test",
       body="Testing email functionality"
   )
   ```

3. **Check Gmail App Password:**
   - Must use App Password, not regular password
   - Generate at: https://myaccount.google.com/apppasswords

### Permission Issues

```bash
# Fix permissions
chmod +x scripts/*.sh
chmod +x scripts/*.py

# Check file ownership
ls -l scripts/
```

## Production Deployment (Vultr)

### Initial Setup

```bash
# SSH to server
ssh reporting

# Navigate to project
cd forex-forecast-system

# Update code
git pull origin develop

# Install dependencies
pip install -r requirements.txt

# Install cron jobs
./scripts/install_cron_jobs.sh

# Verify installation
crontab -l
```

### Verify Automation

```bash
# Wait for first cron run, or run manually:
./scripts/daily_dashboard.sh

# Check logs
tail -f logs/cron.log

# View generated reports
ls -lt reports/daily/
ls -lt reports/validation/
```

## Custom Schedule

To customize cron schedule, edit crontab manually:

```bash
crontab -e
```

Cron format: `minute hour day month weekday command`

Examples:
```
# Every day at 2:30 PM
30 14 * * * cd /path/to/project && ./scripts/daily_dashboard.sh

# Every Monday and Friday at 8 AM
0 8 * * 1,5 cd /path/to/project && ./scripts/weekly_validation.sh

# Every 6 hours
0 */6 * * * cd /path/to/project && python scripts/check_performance.py --all
```

## Monitoring Best Practices

1. **Review daily dashboards** - Check email each morning
2. **Act on alerts** - Performance degradation requires investigation
3. **Weekly validation** - Review comprehensive metrics Monday mornings
4. **Log rotation** - Automatic, but monitor disk space
5. **Calibration** - Re-run quarterly or after major market events

## Support

For issues or questions:
- **Documentation**: `/docs/FINAL_SESSION_SUMMARY_2025-11-13.md`
- **Examples**: `/examples/` directory
- **Tests**: `/tests/` for reference implementations
- **Logs**: Check `/logs/` for detailed error messages

---

**System Status:** ✅ Production Ready
**Automation:** ✅ Fully Configured
**Last Updated:** 2025-11-13
