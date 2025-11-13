# Quick Start Guide: Implementing New Forecast Horizons

**Version:** 1.0
**Target:** Development Team
**Estimated Implementation Time:** 5-6 hours

---

## Summary of Required Changes

### What Needs to Be Done

1. Add 3 new service folders (15d, 30d, 90d) - **Copy from 7d template**
2. Add constants for new horizons - **Update `constants.py`**
3. Create Dockerfiles for each - **Copy from `Dockerfile.7d.prod`**
4. Create cron configurations - **Create cron/15d/`, `cron/30d/`, `cron/90d/`**
5. Update docker-compose - **Add 3 new service definitions**
6. Deploy and test on Vultr - **Same process as existing services**

### What Stays Exactly the Same

- **Forecasting logic** (uses generic ForecastEngine)
- **Report generation** (same charting, PDF building)
- **Email delivery** (same Gmail configuration)
- **Data loading** (same 5 data sources)
- **Configuration system** (Pydantic Settings)

---

## Step-by-Step Implementation

### Phase 1: Update Core Constants (30 mins)

**File:** `src/forex_core/config/constants.py`

Add these lines after `PROJECTION_DAYS = 7`:

```python
# New 15-day forecast
PROJECTION_DAYS_15D = 15
HISTORICAL_LOOKBACK_DAYS_15D = 150   # 5 months
TECH_LOOKBACK_DAYS_15D = 60          # 2 months
VOL_LOOKBACK_DAYS_15D = 30           # 1 month
BASE_PROMPT_15D = """Actúa como analista cuantitativo especializado en mercados de divisas emergentes. Genera una proyección técnica del tipo de cambio USD/CLP para los próximos 15 días calendario con los requisitos entregados por negocio."""

# New 30-day forecast
PROJECTION_DAYS_30D = 30
HISTORICAL_LOOKBACK_DAYS_30D = 180   # 6 months
TECH_LOOKBACK_DAYS_30D = 60          # 2 months
VOL_LOOKBACK_DAYS_30D = 30           # 1 month
BASE_PROMPT_30D = """Actúa como analista cuantitativo especializado en mercados de divisas emergentes. Genera una proyección técnica del tipo de cambio USD/CLP para los próximos 30 días calendario con los requisitos entregados por negocio."""

# New 90-day forecast
PROJECTION_DAYS_90D = 90
HISTORICAL_LOOKBACK_DAYS_90D = 365   # 1 year
TECH_LOOKBACK_DAYS_90D = 90          # 3 months
VOL_LOOKBACK_DAYS_90D = 60           # 2 months
BASE_PROMPT_90D = """Actúa como analista cuantitativo especializado en mercados de divisas emergentes. Genera una proyección técnica del tipo de cambio USD/CLP para los próximos 90 días calendario con los requisitos entregados por negocio."""
```

Also update `__all__` export list to include new constants.

---

### Phase 2: Create Service Directories (1 hour)

**Pattern:** Copy `forecaster_7d` and edit 4 files per horizon

#### For Each Horizon (15d, 30d, 90d):

**2a. Create directory structure:**
```bash
mkdir -p src/services/forecaster_15d
mkdir -p src/services/forecaster_30d
mkdir -p src/services/forecaster_90d
```

**2b. Copy files from forecaster_7d:**
```bash
# For 15d
cp src/services/forecaster_7d/__init__.py src/services/forecaster_15d/
cp src/services/forecaster_7d/cli.py src/services/forecaster_15d/
cp src/services/forecaster_7d/config.py src/services/forecaster_15d/
cp src/services/forecaster_7d/pipeline.py src/services/forecaster_15d/

# Repeat for 30d and 90d
```

**2c. Edit `forecaster_15d/config.py`:**

```python
# Change class name
class Forecaster15DConfig:
    # Update these lines
    horizon: Literal["daily"] = "daily"
    projection_days: int = 15  # CHANGED
    frequency: str = "D"

    # Update lookback periods
    historical_lookback_days: int = 150  # CHANGED
    tech_lookback_days: int = 60
    vol_lookback_days: int = 30

    # Update report configuration
    report_title: str = "Proyección USD/CLP - Próximos 15 Días"  # CHANGED
    report_filename_prefix: str = "Forecast_15D_USDCLP"  # CHANGED
    chart_title_suffix: str = "(15 días)"  # CHANGED

def get_service_config() -> Forecaster15DConfig:  # CHANGED TYPE
    return Forecaster15DConfig()
```

**2d. Edit `forecaster_15d/cli.py`:**

Find and replace:
- `"7d"` → `"15d"` (in app name, log paths, messages)
- `"7-day"` → `"15-day"` (in help text)
- `forecaster_7d` → `forecaster_15d` (in imports)
- `Forecaster7DConfig` → `Forecaster15DConfig` (in type hints)

Key lines to change:
```python
app = typer.Typer(
    name="forecaster-15d",  # CHANGED
    help="15-day USD/CLP forex forecasting service",  # CHANGED
    # ...
)

# In run() function
if log_file is None:
    log_file = Path("./logs/forecaster_15d.log")  # CHANGED

# In validate() docstring
console.print("\n[bold cyan]Validating 15-Day Forecast[/bold cyan]")  # CHANGED
```

**2e. Edit `forecaster_15d/pipeline.py`:**

Change imports:
```python
from .config import get_service_config  # Same

# Find the import comment and update:
# OLD: "from forex_core.config import get_settings"
# NEW: "from forex_core.config import get_settings"  (same)
```

**Repeat steps 2c-2e for 30d and 90d** with appropriate values:

```
30-day:
- Class: Forecaster30DConfig
- projection_days: 30
- historical_lookback_days: 180
- report_title: "Próximos 30 Días"
- filename: "Forecast_30D_USDCLP"
- chart_suffix: "(30 días)"

90-day:
- Class: Forecaster90DConfig
- projection_days: 90
- historical_lookback_days: 365
- report_title: "Próximos 90 Días"
- filename: "Forecast_90D_USDCLP"
- chart_suffix: "(90 días)"
```

---

### Phase 3: Create Dockerfiles (20 mins)

**3a. Copy Dockerfile.7d.prod for each horizon:**

```bash
cp Dockerfile.7d.prod Dockerfile.15d.prod
cp Dockerfile.7d.prod Dockerfile.30d.prod
cp Dockerfile.7d.prod Dockerfile.90d.prod

# For local development (optional)
cp Dockerfile.7d Dockerfile.15d
cp Dockerfile.7d Dockerfile.30d
cp Dockerfile.7d Dockerfile.90d
```

**3b. Edit each Dockerfile to update references:**

In `Dockerfile.15d.prod`, change these lines:

```dockerfile
# OLD:
COPY cron/7d/crontab /etc/cron.d/usdclp-7d
RUN chmod 0644 /etc/cron.d/usdclp-7d
COPY cron/7d/entrypoint.sh /entrypoint.sh

# NEW:
COPY cron/15d/crontab /etc/cron.d/usdclp-15d
RUN chmod 0644 /etc/cron.d/usdclp-15d
COPY cron/15d/entrypoint.sh /entrypoint.sh
```

Repeat for 30d and 90d.

---

### Phase 4: Create Cron Configurations (30 mins)

**4a. Create cron directories:**

```bash
mkdir -p cron/15d
mkdir -p cron/30d
mkdir -p cron/90d
```

**4b. Create cron/15d/crontab:**

```cron
# USD/CLP 15-Day Forecast - Day 1 and 15 of each month at 9:00 AM Chile time
0 9 1,15 * * cd /app && python -m services.forecaster_15d.cli run >> /var/log/cron.log 2>&1

# Health check - write timestamp every hour
0 * * * * date > /tmp/healthcheck
```

**4c. Create cron/15d/entrypoint.sh:**

Copy from `cron/7d/entrypoint.sh` and change:

```bash
# OLD:
echo "🚀 Starting USD/CLP 7-Day Forecaster Service"
crontab /etc/cron.d/usdclp-7d

# NEW:
echo "🚀 Starting USD/CLP 15-Day Forecaster Service"
crontab /etc/cron.d/usdclp-15d
```

**Cron schedules for all horizons:**

```cron
# 15-day: Day 1 and 15 at 9:00 AM
cron/15d/crontab:    0 9 1,15 * * cd /app && python -m services.forecaster_15d.cli run >> /var/log/cron.log 2>&1

# 30-day: Day 1 at 9:30 AM
cron/30d/crontab:    30 9 1 * * cd /app && python -m services.forecaster_30d.cli run >> /var/log/cron.log 2>&1

# 90-day: Day 1 at 10:00 AM
cron/90d/crontab:    0 10 1 * * cd /app && python -m services.forecaster_90d.cli run >> /var/log/cron.log 2>&1
```

---

### Phase 5: Update Docker Compose (30 mins)

**File:** `docker-compose.prod.yml`

Add these three service blocks after the existing `forecaster-7d` service:

```yaml
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

### Phase 6: Local Testing (1 hour)

**6a. Test individual services locally:**

```bash
# Test 15d
docker build -f Dockerfile.15d -t forecaster-15d .
docker run -it --env-file .env forecaster-15d python -m services.forecaster_15d.cli info
docker run -it --env-file .env forecaster-15d python -m services.forecaster_15d.cli validate

# Test 30d
docker build -f Dockerfile.30d -t forecaster-30d .
docker run -it --env-file .env forecaster-30d python -m services.forecaster_30d.cli info

# Test 90d
docker build -f Dockerfile.90d -t forecaster-90d .
docker run -it --env-file .env forecaster-90d python -m services.forecaster_90d.cli info
```

**6b. Test full pipeline (without email):**

```bash
docker run -it --env-file .env -v $(pwd)/reports:/app/reports forecaster-15d \
  python -m services.forecaster_15d.cli run --skip-email

# Check if PDF was generated
ls -lh reports/ | grep -i 15d
```

**6c. Build all with compose:**

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Verify all running
docker ps | grep forecaster
```

---

### Phase 7: Production Deployment (2 hours)

**7a. Push changes to repository:**

```bash
cd /Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system
git add src/services/forecaster_*
git add Dockerfile.*
git add cron/
git add docker-compose.prod.yml
git add src/forex_core/config/constants.py

git commit -m "feat: Add 15-day, 30-day, and 90-day forecasters

- Add Forecaster15DConfig, Forecaster30DConfig, Forecaster90DConfig
- Create service modules for each horizon
- Add Dockerfiles for production deployment
- Add cron configurations with specific schedules
- Update docker-compose.prod.yml with 3 new services
- 15d: days 1,15 at 9:00 AM CLT
- 30d: day 1 at 9:30 AM CLT
- 90d: day 1 at 10:00 AM CLT"

git push origin develop
```

**7b. Deploy to Vultr:**

```bash
# SSH to server
ssh reporting

# Navigate to project
cd /home/deployer/forex-forecast-system

# Pull latest
git pull origin develop

# Build new images
docker compose -f docker-compose.prod.yml build

# Start all services
docker compose -f docker-compose.prod.yml up -d

# Verify status
docker ps | grep forecaster
```

**7c. Verify deployment:**

```bash
# Check all containers running
docker ps

# Test manual execution
docker exec usdclp-forecaster-15d python -m services.forecaster_15d.cli run --skip-email
docker exec usdclp-forecaster-30d python -m services.forecaster_30d.cli run --skip-email
docker exec usdclp-forecaster-90d python -m services.forecaster_90d.cli run --skip-email

# Check reports generated
ls -lth /home/deployer/forex-forecast-system/reports/ | head -10

# Verify crontab installation
docker exec usdclp-forecaster-15d crontab -l
docker exec usdclp-forecaster-30d crontab -l
docker exec usdclp-forecaster-90d crontab -l

# Check logs for any errors
docker exec usdclp-forecaster-15d tail -20 /var/log/cron.log
```

---

## Verification Checklist

### Before Going Live

- [ ] All 3 services build successfully
- [ ] `docker ps` shows 4 containers (7d, 15d, 30d, 90d)
- [ ] Manual execution works for each: `docker exec usdclp-forecaster-XD python -m services.forecaster_XD.cli run --skip-email`
- [ ] PDF reports generated: `ls -lth reports/`
- [ ] Crontabs installed: `docker exec usdclp-forecaster-XD crontab -l`
- [ ] Healthchecks passing: `docker inspect usdclp-forecaster-XD | grep Health`
- [ ] No errors in logs: `docker exec usdclp-forecaster-XD tail -20 /var/log/cron.log`

### After Going Live (Monitor)

- [ ] Day 0: Manual verification of all services
- [ ] Day 1: Verify 15d executes on day 1 (or 15th if testing later in month)
- [ ] Day 1: Verify 30d and 90d execute on day 1
- [ ] Email delivery: Confirm all recipients receive reports
- [ ] Logs: No exceptions or warnings
- [ ] Week 1: All services running without issues
- [ ] Week 2: Verify next execution cycle works correctly

---

## Troubleshooting Quick Reference

| Problem | Solution |
|---------|----------|
| Container won't start | Check Docker logs: `docker logs usdclp-forecaster-XD` |
| Crontab not running | Verify in container: `docker exec usdclp-forecaster-XD ps aux \| grep cron` |
| PDF not generating | Run manually with debug: `docker exec ... python -m services.forecaster_XD.cli run -l DEBUG` |
| Email not sent | Check GMAIL credentials and 2FA is enabled |
| Wrong execution time | Verify cron expression at crontab.guru |
| Memory/CPU high | Check: `docker stats usdclp-forecaster-XD` |

---

## Files to Create/Modify

**Files Created:**
- `src/services/forecaster_15d/__init__.py`
- `src/services/forecaster_15d/cli.py`
- `src/services/forecaster_15d/config.py`
- `src/services/forecaster_15d/pipeline.py`
- `src/services/forecaster_30d/` (4 files)
- `src/services/forecaster_90d/` (4 files)
- `Dockerfile.15d`
- `Dockerfile.15d.prod`
- `Dockerfile.30d`
- `Dockerfile.30d.prod`
- `Dockerfile.90d`
- `Dockerfile.90d.prod`
- `cron/15d/crontab`
- `cron/15d/entrypoint.sh`
- `cron/30d/crontab`
- `cron/30d/entrypoint.sh`
- `cron/90d/crontab`
- `cron/90d/entrypoint.sh`

**Files Modified:**
- `src/forex_core/config/constants.py` (add constants)
- `docker-compose.prod.yml` (add 3 service blocks)

**Total Files:** 22 files (18 created, 2 modified)

---

## Key Files for Reference

While implementing, keep these open for reference:

1. **Template for services:** `src/services/forecaster_7d/`
2. **Template for Dockerfile:** `Dockerfile.7d.prod`
3. **Template for cron:** `cron/7d/`
4. **Constants to extend:** `src/forex_core/config/constants.py`
5. **Compose template:** `docker-compose.prod.yml`

---

## Estimated Time Breakdown

| Phase | Time | Effort |
|-------|------|--------|
| Phase 1: Constants | 30 min | Minimal |
| Phase 2: Services | 1 hour | Copy + edit |
| Phase 3: Dockerfiles | 20 min | Copy + 2-line edits |
| Phase 4: Cron | 30 min | Create 6 files |
| Phase 5: Compose | 30 min | Paste 3 blocks |
| Phase 6: Local test | 1 hour | Build & test |
| Phase 7: Deploy | 2 hours | Push & verify |
| **Total** | **5-6 hours** | **Low complexity** |

---

**Document Version:** 1.0
**Last Updated:** 2025-11-13
**Status:** Ready to implement
