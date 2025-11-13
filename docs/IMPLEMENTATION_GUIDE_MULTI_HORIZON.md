# Multi-Horizon Forecast Implementation Guide

**Quick reference for implementing 15d, 30d, 90d forecast services**

Based on comprehensive code review: `docs/reviews/2025-11-13-1430-multi-horizon-scheduling-review.md`

---

## Quick Start Checklist

- [ ] Phase 1: Add configuration constants
- [ ] Phase 2: Create service directories and files
- [ ] Phase 3: Create Docker and cron configurations
- [ ] Phase 4: Test locally with `--skip-email`
- [ ] Phase 5: Deploy to server
- [ ] Phase 6: Test PDF generation on server
- [ ] Phase 7: Enable email delivery
- [ ] Phase 8: Monitor production

**Estimated time**: 2-3 days

---

## Phase 1: Configuration (30 minutes)

### 1.1 Update Constants

File: `src/forex_core/config/constants.py`

```python
# Add after existing PROJECTION_DAYS and PROJECTION_MONTHS (line ~24)

# Medium-term forecast horizons
PROJECTION_DAYS_15D = 15
PROJECTION_DAYS_30D = 30
PROJECTION_DAYS_90D = 90

# Historical lookback periods
HISTORICAL_LOOKBACK_DAYS_15D = 180  # 6 months
HISTORICAL_LOOKBACK_DAYS_30D = 365  # 1 year
HISTORICAL_LOOKBACK_DAYS_90D = 730  # 2 years

# Technical analysis lookback
TECH_LOOKBACK_DAYS_15D = 60   # 2 months
TECH_LOOKBACK_DAYS_30D = 90   # 3 months
TECH_LOOKBACK_DAYS_90D = 120  # 4 months

# Volatility lookback
VOL_LOOKBACK_DAYS_15D = 45  # 1.5 months
VOL_LOOKBACK_DAYS_30D = 60  # 2 months
VOL_LOOKBACK_DAYS_90D = 90  # 3 months

# Base prompts
BASE_PROMPT_15D = """Actúa como analista cuantitativo especializado en mercados de divisas emergentes. Genera una proyección técnica del tipo de cambio USD/CLP para los próximos 15 días calendario con los requisitos entregados por negocio."""

BASE_PROMPT_30D = """Actúa como analista cuantitativo especializado en mercados de divisas emergentes. Genera una proyección técnica del tipo de cambio USD/CLP para los próximos 30 días calendario con los requisitos entregados por negocio."""

BASE_PROMPT_90D = """Actúa como analista cuantitativo especializado en mercados de divisas emergentes. Genera una proyección técnica del tipo de cambio USD/CLP para los próximos 90 días (horizonte trimestral) con los requisitos entregados por negocio."""
```

### 1.2 Update __all__ export

```python
# Add to __all__ list at end of constants.py
__all__ = [
    # ... existing exports ...
    "PROJECTION_DAYS_15D",
    "PROJECTION_DAYS_30D",
    "PROJECTION_DAYS_90D",
    "HISTORICAL_LOOKBACK_DAYS_15D",
    "HISTORICAL_LOOKBACK_DAYS_30D",
    "HISTORICAL_LOOKBACK_DAYS_90D",
    "TECH_LOOKBACK_DAYS_15D",
    "TECH_LOOKBACK_DAYS_30D",
    "TECH_LOOKBACK_DAYS_90D",
    "VOL_LOOKBACK_DAYS_15D",
    "VOL_LOOKBACK_DAYS_30D",
    "VOL_LOOKBACK_DAYS_90D",
    "BASE_PROMPT_15D",
    "BASE_PROMPT_30D",
    "BASE_PROMPT_90D",
]
```

---

## Phase 2: Service Files (2 hours)

### 2.1 Create Directory Structure

```bash
# Create service directories
mkdir -p src/services/forecaster_{15d,30d,90d}

# Create __init__.py files
touch src/services/forecaster_{15d,30d,90d}/__init__.py
```

### 2.2 Create Config Files

For each horizon (15d, 30d, 90d), copy `src/services/forecaster_7d/config.py` and modify:

**Example: `src/services/forecaster_15d/config.py`**

```python
"""Configuration overrides for 15-day forecaster service."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

from forex_core.config import (
    PROJECTION_DAYS_15D,
    HISTORICAL_LOOKBACK_DAYS_15D,
    TECH_LOOKBACK_DAYS_15D,
    VOL_LOOKBACK_DAYS_15D,
)


@dataclass(frozen=True)
class Forecaster15DConfig:
    """Service-specific configuration for 15-day forecaster."""

    horizon: Literal["daily"] = "daily"
    projection_days: int = PROJECTION_DAYS_15D  # 15 days
    frequency: str = "D"

    historical_lookback_days: int = HISTORICAL_LOOKBACK_DAYS_15D
    tech_lookback_days: int = TECH_LOOKBACK_DAYS_15D
    vol_lookback_days: int = VOL_LOOKBACK_DAYS_15D

    report_title: str = "Proyección USD/CLP - Próximos 15 Días"
    report_filename_prefix: str = "Forecast_15D_USDCLP"
    chart_title_suffix: str = "(15 días)"

    @property
    def steps(self) -> int:
        return self.projection_days


def get_service_config() -> Forecaster15DConfig:
    return Forecaster15DConfig()


__all__ = ["Forecaster15DConfig", "get_service_config"]
```

Repeat for `forecaster_30d` and `forecaster_90d` with appropriate values.

### 2.3 Copy Pipeline and CLI Files

```bash
# For each horizon (15d, 30d, 90d)
for horizon in 15d 30d 90d; do
    # Copy pipeline (no changes needed, imports service config)
    cp src/services/forecaster_7d/pipeline.py src/services/forecaster_${horizon}/pipeline.py

    # Copy CLI
    cp src/services/forecaster_7d/cli.py src/services/forecaster_${horizon}/cli.py

    # Update service name in CLI (optional, for display purposes)
    sed -i '' "s/7-day/${horizon%-day}-day/g" src/services/forecaster_${horizon}/cli.py
    sed -i '' "s/7-Day/${horizon%-day}-Day/g" src/services/forecaster_${horizon}/cli.py
done
```

---

## Phase 3: Docker & Cron Setup (1 hour)

### 3.1 Create Cron Directories

```bash
mkdir -p cron/{15d,30d,90d}
```

### 3.2 Create Crontab Files

**`cron/15d/crontab`**
```cron
# USD/CLP 15-Day Forecast - Day 1 and 15 at 9:00 AM Chile time
0 9 1,15 * * cd /app && python -m services.forecaster_15d.cli run >> /var/log/cron.log 2>&1

# Health check - write timestamp every hour
0 * * * * date > /tmp/healthcheck
```

**`cron/30d/crontab`**
```cron
# USD/CLP 30-Day Forecast - Day 1 of each month at 9:30 AM Chile time
30 9 1 * * cd /app && python -m services.forecaster_30d.cli run >> /var/log/cron.log 2>&1

# Health check
0 * * * * date > /tmp/healthcheck
```

**`cron/90d/crontab`**
```cron
# USD/CLP 90-Day Forecast - Day 1 of each month at 10:00 AM Chile time
0 10 1 * * cd /app && python -m services.forecaster_90d.cli run >> /var/log/cron.log 2>&1

# Health check
0 * * * * date > /tmp/healthcheck
```

### 3.3 Create Entrypoint Scripts

Copy `cron/7d/entrypoint.sh` for each horizon:

```bash
for horizon in 15d 30d 90d; do
    cp cron/7d/entrypoint.sh cron/${horizon}/entrypoint.sh
    # Update service name
    sed -i '' "s/7-Day/${horizon#*d}-Day/g" cron/${horizon}/entrypoint.sh
    sed -i '' "s/usdclp-7d/usdclp-${horizon}/g" cron/${horizon}/entrypoint.sh
done
```

### 3.4 Create Dockerfiles

Copy `Dockerfile.7d.prod` for each horizon:

```bash
for horizon in 15d 30d 90d; do
    cp Dockerfile.7d.prod Dockerfile.${horizon}.prod
    # Update paths in Dockerfile
    sed -i '' "s|cron/7d|cron/${horizon}|g" Dockerfile.${horizon}.prod
    sed -i '' "s|usdclp-7d|usdclp-${horizon}|g" Dockerfile.${horizon}.prod
    sed -i '' "s|7-day|${horizon}-day|g" Dockerfile.${horizon}.prod
done
```

### 3.5 Update docker-compose.prod.yml

Add three new services (copy from existing `forecaster-7d` and modify):

```yaml
# After forecaster-7d service, add:

  # 15-day forecaster - runs on day 1 and 15 at 09:00 Chile time
  forecaster-15d:
    build:
      context: .
      dockerfile: Dockerfile.15d.prod
    container_name: usdclp-forecaster-15d
    environment:
      - ENVIRONMENT=production
      - REPORT_TIMEZONE=America/Santiago
      - FRED_API_KEY=${FRED_API_KEY}
      - NEWS_API_KEY=${NEWS_API_KEY}
      - GMAIL_USER=${GMAIL_USER}
      - GMAIL_APP_PASSWORD=${GMAIL_APP_PASSWORD}
      - EMAIL_RECIPIENTS=${EMAIL_RECIPIENTS}
    volumes:
      - ./data:/app/data
      - ./output:/app/output
      - ./reports:/app/reports
      - ./logs:/app/logs
      - ./.env:/app/.env:ro
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # 30-day forecaster - runs on day 1 at 09:30 Chile time
  forecaster-30d:
    build:
      context: .
      dockerfile: Dockerfile.30d.prod
    container_name: usdclp-forecaster-30d
    environment:
      - ENVIRONMENT=production
      - REPORT_TIMEZONE=America/Santiago
      - FRED_API_KEY=${FRED_API_KEY}
      - NEWS_API_KEY=${NEWS_API_KEY}
      - GMAIL_USER=${GMAIL_USER}
      - GMAIL_APP_PASSWORD=${GMAIL_APP_PASSWORD}
      - EMAIL_RECIPIENTS=${EMAIL_RECIPIENTS}
    volumes:
      - ./data:/app/data
      - ./output:/app/output
      - ./reports:/app/reports
      - ./logs:/app/logs
      - ./.env:/app/.env:ro
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # 90-day forecaster - runs on day 1 at 10:00 Chile time
  forecaster-90d:
    build:
      context: .
      dockerfile: Dockerfile.90d.prod
    container_name: usdclp-forecaster-90d
    environment:
      - ENVIRONMENT=production
      - REPORT_TIMEZONE=America/Santiago
      - FRED_API_KEY=${FRED_API_KEY}
      - NEWS_API_KEY=${NEWS_API_KEY}
      - GMAIL_USER=${GMAIL_USER}
      - GMAIL_APP_PASSWORD=${GMAIL_APP_PASSWORD}
      - EMAIL_RECIPIENTS=${EMAIL_RECIPIENTS}
    volumes:
      - ./data:/app/data
      - ./output:/app/output
      - ./reports:/app/reports
      - ./logs:/app/logs
      - ./.env:/app/.env:ro
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## Phase 4: Local Testing (2-3 hours)

### 4.1 Build Images

```bash
docker compose -f docker-compose.prod.yml build forecaster-15d
docker compose -f docker-compose.prod.yml build forecaster-30d
docker compose -f docker-compose.prod.yml build forecaster-90d
```

### 4.2 Start Containers

```bash
docker compose -f docker-compose.prod.yml up -d forecaster-15d
docker compose -f docker-compose.prod.yml up -d forecaster-30d
docker compose -f docker-compose.prod.yml up -d forecaster-90d
```

### 4.3 Verify Startup

```bash
# Check containers are running
docker ps --filter name=forecaster

# Check logs for successful startup
docker logs usdclp-forecaster-15d
docker logs usdclp-forecaster-30d
docker logs usdclp-forecaster-90d

# Should see "Starting..." and crontab installation messages
```

### 4.4 Test Manual Execution (No Email)

```bash
# Test 15d forecast
docker exec usdclp-forecaster-15d python -m services.forecaster_15d.cli run --skip-email

# Test 30d forecast
docker exec usdclp-forecaster-30d python -m services.forecaster_30d.cli run --skip-email

# Test 90d forecast
docker exec usdclp-forecaster-90d python -m services.forecaster_90d.cli run --skip-email
```

### 4.5 Verify PDF Generation

```bash
# Check generated PDFs
ls -lth ./reports/ | head -10

# Should see files like:
# Forecast_15D_USDCLP_2025-11-13_1430.pdf
# Forecast_30D_USDCLP_2025-11-13_1435.pdf
# Forecast_90D_USDCLP_2025-11-13_1440.pdf
```

### 4.6 Manual PDF Review

Open each PDF and verify:

- [ ] Report title shows correct horizon (15/30/90 días)
- [ ] Forecast dates are sequential and correct
- [ ] Charts render properly (no overlap, clear legends)
- [ ] Confidence intervals widen over time
- [ ] Values are in reasonable range (500-1500)
- [ ] Model metrics table is present
- [ ] Spanish text is professional and error-free

If any issues found, fix and re-test before proceeding.

---

## Phase 5: Server Deployment (1 hour)

### 5.1 Commit and Push

```bash
git add src/services/forecaster_{15d,30d,90d}
git add cron/{15d,30d,90d}
git add Dockerfile.{15d,30d,90d}.prod
git add docker-compose.prod.yml
git add src/forex_core/config/constants.py
git commit -m "feat: Add 15d, 30d, 90d forecaster services with cron scheduling"
git push origin develop
```

### 5.2 Deploy to Server

```bash
# SSH to server
ssh reporting

# Navigate to project directory
cd /home/deployer/forex-forecast-system

# Pull latest code
git pull origin develop

# Build images on server
docker compose -f docker-compose.prod.yml build forecaster-15d
docker compose -f docker-compose.prod.yml build forecaster-30d
docker compose -f docker-compose.prod.yml build forecaster-90d

# Start containers
docker compose -f docker-compose.prod.yml up -d forecaster-15d
docker compose -f docker-compose.prod.yml up -d forecaster-30d
docker compose -f docker-compose.prod.yml up -d forecaster-90d
```

### 5.3 Verify Deployment

```bash
# Check all containers are running
docker ps --filter name=forecaster

# Should show:
# usdclp-forecaster-7d    Up X days (healthy)
# usdclp-forecaster-15d   Up X seconds (health: starting)
# usdclp-forecaster-30d   Up X seconds (health: starting)
# usdclp-forecaster-90d   Up X seconds (health: starting)

# Check logs
docker logs usdclp-forecaster-15d
docker logs usdclp-forecaster-30d
docker logs usdclp-forecaster-90d
```

---

## Phase 6: Server Testing (1-2 hours)

### 6.1 Test Manual Execution on Server

```bash
# SSH to server
ssh reporting

# Test each service manually (without email)
docker exec usdclp-forecaster-15d python -m services.forecaster_15d.cli run --skip-email
docker exec usdclp-forecaster-30d python -m services.forecaster_30d.cli run --skip-email
docker exec usdclp-forecaster-90d python -m services.forecaster_90d.cli run --skip-email
```

### 6.2 Download PDFs for Review

```bash
# From your local machine
scp "reporting:/home/deployer/forex-forecast-system/reports/Forecast_*D_USDCLP_*.pdf" .
```

### 6.3 Review Downloaded PDFs

Use same checklist as Phase 4.6. If all pass, proceed to Phase 7.

---

## Phase 7: Email Enablement (30 minutes)

### 7.1 Test Email Delivery

```bash
# SSH to server
ssh reporting

# Test email with one service first (15d)
docker exec usdclp-forecaster-15d python -m services.forecaster_15d.cli run
# (without --skip-email flag)
```

### 7.2 Verify Email

Check that:
- [ ] All recipients in `EMAIL_RECIPIENTS` received the email
- [ ] PDF is attached correctly
- [ ] Subject line is appropriate: "Proyección USD/CLP 15D - 2025-11-13"
- [ ] Email body is professional
- [ ] No errors in logs

### 7.3 Enable for All Services

If email test passes, the cron jobs are already configured to send emails (they don't have `--skip-email` flag).

No further action needed - cron will automatically send emails on scheduled runs.

---

## Phase 8: Production Monitoring (Ongoing)

### 8.1 Daily Health Checks

```bash
# Check container status
docker ps --filter name=forecaster --format "table {{.Names}}\t{{.Status}}"

# Check for errors in logs
for horizon in 7d 15d 30d 90d; do
    echo "=== $horizon ==="
    docker exec usdclp-forecaster-${horizon} tail -20 /var/log/cron.log | grep -i "error\|exception"
done
```

### 8.2 Verify Scheduled Executions

```bash
# After scheduled run time, check logs
docker exec usdclp-forecaster-15d tail -50 /var/log/cron.log

# Should see execution logs with timestamps
# Verify execution happened at correct Chile time
```

### 8.3 Report Archive Management

```bash
# Check disk usage
du -sh /home/deployer/forex-forecast-system/reports/

# List recent reports
ls -lth /home/deployer/forex-forecast-system/reports/ | head -20

# Archive old reports (manual - can automate later)
# Keep last 90 days, move rest to archive/
find /home/deployer/forex-forecast-system/reports -name "*.pdf" -mtime +90 -exec mv {} /home/deployer/forex-forecast-system/reports/archive/ \;
```

---

## Schedule Reference

| Service | Schedule | Next Runs (Example) |
|---------|----------|---------------------|
| 7d | Daily 8:00 AM | Every day |
| 15d | Day 1,15 @ 9:00 AM | Nov 15, Dec 1, Dec 15, Jan 1... |
| 30d | Day 1 @ 9:30 AM | Dec 1, Jan 1, Feb 1... |
| 90d | Day 1 @ 10:00 AM | Dec 1, Jan 1, Feb 1... |

All times are **Chile time (America/Santiago)**.

---

## Troubleshooting

### Container won't start

```bash
# Check build logs
docker compose -f docker-compose.prod.yml logs forecaster-15d

# Rebuild from scratch
docker compose -f docker-compose.prod.yml build --no-cache forecaster-15d
```

### Cron not executing

```bash
# Verify crontab is installed
docker exec usdclp-forecaster-15d crontab -l

# Check cron daemon is running
docker exec usdclp-forecaster-15d ps aux | grep cron

# Check system time and timezone
docker exec usdclp-forecaster-15d date
# Should show Chile time (CLT or CLST)
```

### Email not sending

```bash
# Check environment variables
docker exec usdclp-forecaster-15d env | grep -E "GMAIL|EMAIL"

# Verify .env file is mounted
docker exec usdclp-forecaster-15d cat /app/.env | grep GMAIL

# Test email manually
docker exec usdclp-forecaster-15d python -m services.forecaster_15d.cli run
# Check logs for email errors
```

### PDF issues

```bash
# Check file permissions
ls -la /home/deployer/forex-forecast-system/reports/

# Check disk space
df -h /home/deployer/forex-forecast-system/

# Regenerate PDF manually with debug logging
docker exec usdclp-forecaster-15d python -m services.forecaster_15d.cli run --skip-email --log-level DEBUG
```

---

## Quick Commands Reference

```bash
# View all container status
docker ps --filter name=forecaster

# View logs (live)
docker logs -f usdclp-forecaster-15d

# Execute manual forecast (no email)
docker exec usdclp-forecaster-15d python -m services.forecaster_15d.cli run --skip-email

# Execute with email
docker exec usdclp-forecaster-15d python -m services.forecaster_15d.cli run

# Restart specific service
docker compose -f docker-compose.prod.yml restart forecaster-15d

# Rebuild and redeploy
docker compose -f docker-compose.prod.yml up -d --build forecaster-15d

# Check crontab
docker exec usdclp-forecaster-15d crontab -l

# Check system time
docker exec usdclp-forecaster-15d date

# View cron logs
docker exec usdclp-forecaster-15d tail -f /var/log/cron.log
```

---

## Success Criteria

Implementation is complete when:

- [x] All 3 new services (15d, 30d, 90d) build successfully
- [x] Containers start and show "healthy" status
- [x] Manual execution generates valid PDFs
- [x] PDFs pass quality review checklist
- [x] Cron schedules are configured correctly
- [x] Test email delivered successfully
- [x] Services run automatically on schedule
- [x] No errors in logs after 48 hours
- [x] Documentation updated (PRODUCTION_DEPLOYMENT.md)

---

**Questions or issues?**
Refer to detailed code review: `docs/reviews/2025-11-13-1430-multi-horizon-scheduling-review.md`
