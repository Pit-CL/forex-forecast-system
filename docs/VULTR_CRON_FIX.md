# Vultr Cron Schedule Fix

## Summary of Changes

This guide documents the fixes applied to the cron schedules on the Vultr production server.

## Issues Identified

1. **7d Forecast**: Container cron was configured to run only on Mondays instead of daily
2. **90d Forecast**: Running monthly instead of quarterly
3. **Host Cron Duplicate**: Host cron at `0 8 * * *` conflicts with container cron

## Fixes Applied

### 1. Container Cron Updates

The following crontab files have been updated in the repository:

#### `cron/7d/crontab`
```bash
# Before:
0 8 * * 1 cd /app && python -m services.forecaster_7d.cli run >> /var/log/cron.log 2>&1

# After:
0 8 * * * cd /app && python -m services.forecaster_7d.cli run >> /var/log/cron.log 2>&1
```
Changed from Monday-only (`* * 1`) to daily (`* * *`).

#### `cron/90d/crontab`
```bash
# Before:
0 10 1 * * cd /app && python -m services.forecaster_90d.cli run >> /var/log/cron.log 2>&1

# After:
0 10 1 1,4,7,10 * cd /app && python -m services.forecaster_90d.cli run >> /var/log/cron.log 2>&1
```
Changed from monthly (day 1 of every month) to quarterly (day 1 of Jan, Apr, Jul, Oct).

### 2. Host Cron Removal

**IMPORTANT**: The host cron needs to be manually removed on Vultr.

#### Steps to Remove Host Cron

SSH into the Vultr server and execute:

```bash
# 1. Connect to Vultr
ssh deployer@<vultr-ip>

# 2. Check current crontab
crontab -l

# 3. Edit crontab
crontab -e

# 4. Remove the following line if it exists:
# 0 8 * * * cd /home/deployer/forex-forecast-system && docker-compose exec -T forecaster-7d python -m services.forecaster_7d.cli run

# 5. Save and exit

# 6. Verify it was removed
crontab -l
```

#### Why Remove Host Cron?

The host cron conflicts with the container cron:
- **Host cron**: Runs daily at 8:00 AM, tries to execute inside container
- **Container cron**: Runs daily at 8:00 AM inside the container
- **Problem**: Double execution, potential race conditions

The container cron is preferred because:
- It runs inside the application environment
- Better isolation and resource management
- Consistent with other services (15d, 30d, 90d)

### 3. Deployment Steps

To apply these changes on Vultr:

```bash
# 1. SSH into Vultr
ssh deployer@<vultr-ip>

# 2. Navigate to project
cd forex-forecast-system

# 3. Pull latest changes
git pull origin develop

# 4. Rebuild affected containers
docker-compose build forecaster-7d forecaster-90d

# 5. Restart containers with new cron schedules
docker-compose up -d forecaster-7d forecaster-90d

# 6. Verify cron schedules inside containers
docker-compose exec forecaster-7d crontab -l
docker-compose exec forecaster-90d crontab -l

# 7. Remove host cron (see instructions above)
crontab -e

# 8. Monitor logs to ensure it works
docker-compose logs -f forecaster-7d
```

## Current Schedule After Fix

| Service | Frequency | Schedule | Cron Expression |
|---------|-----------|----------|-----------------|
| 7d      | Daily     | 8:00 AM  | `0 8 * * *` |
| 15d     | Bi-monthly| Day 1, 15 @ 9:00 AM | `0 9 1,15 * *` |
| 30d     | Monthly   | Day 1 @ 9:30 AM | `30 9 1 * *` |
| 90d     | Quarterly | Jan/Apr/Jul/Oct 1 @ 10:00 AM | `0 10 1 1,4,7,10 *` |

## Verification

After deployment, verify the fix worked:

```bash
# Check if 7d runs daily (should see logs every day at 8 AM)
docker-compose logs forecaster-7d | grep "Starting 7-day"

# Check if 90d only runs quarterly
docker-compose logs forecaster-90d | grep "Starting 90-day"

# Ensure no duplicate execution (check for same timestamp appearing twice)
docker-compose logs forecaster-7d | grep "$(date +%Y-%m-%d)"
```

## Rollback Plan

If issues occur, rollback:

```bash
# 1. Revert code changes
git checkout HEAD~1 cron/7d/crontab cron/90d/crontab

# 2. Rebuild containers
docker-compose build forecaster-7d forecaster-90d

# 3. Restart containers
docker-compose up -d forecaster-7d forecaster-90d
```

## Related Documentation

- [Chronos Deployment Checklist](../CHRONOS_DEPLOYMENT_CHECKLIST.md)
- [MLOps Roadmap](MLOPS_ROADMAP.md)
- [Docker Cleanup Automation](../scripts/auto_cleanup_docker.sh)

---
**Updated**: 2025-11-13
**Status**: Ready for deployment
**Reviewed**: System automation improvements
