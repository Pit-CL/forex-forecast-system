# Implementation Guide: New Forecast Horizons (15d, 30d, 90d)

**Date:** 2025-11-13
**Version:** 1.0
**Status:** Planning & Reference Document
**Target Audience:** Development Team

---

## Executive Summary

This document provides a comprehensive overview of the current production implementation patterns and serves as a reference guide for implementing three new forecast horizons with specific scheduling requirements:

- **15d** (15-day): Runs on day 1 and 15 of each month at 9:00 AM CLT
- **30d** (30-day): Runs on day 1 of each month at 9:30 AM CLT
- **90d** (90-day): Runs on day 1 of each month at 10:00 AM CLT

All times are in Chile time zone (America/Santiago, UTC-4 during winter, UTC-3 during daylight saving).

---

## Part 1: Current Implementation Architecture

### 1.1 Production Deployment Setup

#### Overview
The system runs on **Vultr VPS** using Docker containers with cron-based scheduling and automated recovery.

#### Current Deployed Service: 7-Day Forecaster

**Configuration:**
- **Container Name:** `usdclp-forecaster-7d`
- **Schedule:** Daily at 08:00 AM Chile time
- **Execution Method:** Cron within Docker container
- **Image:** `Dockerfile.7d.prod` (Python 3.12-slim + cron)
- **Compose File:** `docker-compose.prod.yml`
- **Restart Policy:** `always` (auto-recovery on crash)

**Key Features:**
- Auto-restart on failure (8-second recovery time)
- Systemd integration for server reboot resilience
- Health checks every hour
- Cron logs to `/var/log/cron.log` (persistent)
- Email notifications on successful completion

---

### 1.2 Cron Configuration Pattern

**File Structure:**
```
cron/
├── 7d/
│   ├── crontab          # Cron schedule definition
│   └── entrypoint.sh    # Container startup script
```

**Crontab Format (7d example):**
```cron
# USD/CLP 7-Day Forecast - Daily at 8:00 AM Chile time
0 8 * * * cd /app && python -m services.forecaster_7d.cli run >> /var/log/cron.log 2>&1

# Health check - write timestamp every hour
0 * * * * date > /tmp/healthcheck
```

**Cron Scheduling Reference:**
```
Minute (0-59) | Hour (0-23) | Day of Month (1-31) | Month (1-12) | Day of Week (0-6)
```

**Examples for New Horizons:**
```cron
# 15-day: Day 1 and 15 of each month at 9:00 AM
0 9 1,15 * * cd /app && python -m services.forecaster_15d.cli run >> /var/log/cron.log 2>&1

# 30-day: Day 1 of each month at 9:30 AM
30 9 1 * * cd /app && python -m services.forecaster_30d.cli run >> /var/log/cron.log 2>&1

# 90-day: Day 1 of each month at 10:00 AM
0 10 1 * * cd /app && python -m services.forecaster_90d.cli run >> /var/log/cron.log 2>&1
```

---

### 1.3 Service Structure Pattern

Each forecaster service follows this directory structure:

```
src/services/forecaster_XD/
├── __init__.py           # Service initialization
├── cli.py               # Typer CLI with commands: run, validate, backtest, info
├── config.py            # Service-specific configuration (horizon, days, lookback)
└── pipeline.py          # Forecast execution pipeline
```

**Key Files:**

#### cli.py
- Provides Typer CLI interface
- Main commands:
  - `run`: Execute full pipeline (data → forecast → charts → PDF → email)
  - `validate`: Test forecast generation without reports
  - `backtest`: Historical accuracy evaluation (not yet implemented)
  - `info`: Display configuration and API status
- Options:
  - `--skip-email`: Run without sending emails
  - `--output-dir`: Custom output directory
  - `--log-level`: DEBUG, INFO, WARNING, ERROR
  - `--log-file`: Custom log file path

#### config.py
- Defines `Forecaster{XD}Config` dataclass (frozen)
- Configurable parameters:
  - `horizon`: "daily" or "monthly"
  - `projection_days`: Number of days to forecast (7, 30, 90)
  - `projection_months`: For monthly horizons (12)
  - `frequency`: Pandas frequency string ("D" for daily, "ME" for month-end)
  - `historical_lookback_days`: Days of historical data
  - `tech_lookback_days`: Technical indicator lookback period
  - `vol_lookback_days`: Volatility calculation lookback
  - `report_title`: Spanish title for PDF report
  - `report_filename_prefix`: Output filename prefix
  - `chart_title_suffix`: Chart subtitle (e.g., "(7 días)")
- Provides `get_service_config()` function to retrieve configuration

#### pipeline.py
- Implements `run_forecast_pipeline()` function
- Executes workflow:
  1. Load data from multiple sources
  2. Generate ensemble forecast
  3. Create visualization charts
  4. Build PDF report
  5. Send email notification
- Also provides `validate_forecast()` for data validation

---

### 1.4 Docker Deployment Pattern

#### Dockerfile Structure

**Base File: `Dockerfile.7d.prod`**
```dockerfile
FROM python:3.12-slim

# Install system dependencies (cairo, pango for WeasyPrint)
RUN apt-get update && apt-get install -y \
    build-essential libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info cron \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Copy cron configuration
COPY cron/7d/crontab /etc/cron.d/usdclp-7d
RUN chmod 0644 /etc/cron.d/usdclp-7d

# Copy and make entrypoint executable
COPY cron/7d/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set environment
ENV PYTHONPATH=/app/src
ENV ENVIRONMENT=production

# Create required directories
RUN mkdir -p /app/data /app/output /app/logs /app/reports

# Healthcheck (2-hour window)
HEALTHCHECK --interval=1h --timeout=10s --start-period=30s --retries=3 \
    CMD test -f /tmp/healthcheck && [ $(( $(date +%s) - $(stat -c %Y /tmp/healthcheck) )) -lt 7200 ] || exit 1

ENTRYPOINT ["/entrypoint.sh"]
```

**Dockerfile Naming Convention:**
- `Dockerfile.7d` - Development/local testing
- `Dockerfile.7d.prod` - Production Vultr deployment
- `Dockerfile.12m` - 12-month forecaster
- Suggested names for new horizons:
  - `Dockerfile.15d`, `Dockerfile.15d.prod`
  - `Dockerfile.30d`, `Dockerfile.30d.prod`
  - `Dockerfile.90d`, `Dockerfile.90d.prod`

---

#### Docker Compose Configuration

**File: `docker-compose.prod.yml`**

```yaml
version: "3.8"

services:
  forecaster-7d:
    build:
      context: .
      dockerfile: Dockerfile.7d.prod
    container_name: usdclp-forecaster-7d
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

volumes:
  data:
    driver: local
  output:
    driver: local
  logs:
    driver: local

networks:
  default:
    name: forex-forecast-network
```

**Key Configuration Options:**
- `restart: always` - Auto-recovery on crash
- `volumes` - Persistent storage for data, reports, logs
- `.env:ro` - Read-only environment file mounting
- `logging` - Max 10MB per file, keep 3 files (30MB total)

**Pattern for New Horizons:**
Add additional service blocks for each new forecaster (15d, 30d, 90d) with unique:
- `container_name`: `usdclp-forecaster-15d`, `usdclp-forecaster-30d`, etc.
- `dockerfile`: `Dockerfile.15d.prod`, `Dockerfile.30d.prod`, etc.
- `crontab path`: `cron/15d/crontab`, `cron/30d/crontab`, etc.

---

### 1.5 Entrypoint Script Pattern

**File: `cron/7d/entrypoint.sh`**

```bash
#!/usr/bin/env bash
set -e

echo "🚀 Starting USD/CLP 7-Day Forecaster Service"
echo "=============================================="

# Load environment variables from .env file
if [ -f "/app/.env" ]; then
    set -o allexport
    source /app/.env || echo "Warning: Failed to source .env"
    set +o allexport
    echo "✓ Environment variables loaded"
fi

# Create log file
touch /var/log/cron.log
echo "✓ Log file created at /var/log/cron.log"

# Export all environment variables for cron
printenv | grep -v "^_" | grep -v "^HOME=" | grep -v "^PWD=" > /etc/environment
echo "✓ Environment exported to /etc/environment"

# Install crontab
crontab /etc/cron.d/usdclp-7d
echo "✓ Crontab installed"

# Verify crontab
echo ""
echo "Loaded crontab:"
crontab -l
echo ""

# Start cron in foreground
echo "✓ Starting cron daemon..."
echo "✓ Logs available at /var/log/cron.log"
echo "=============================================="

cron && tail -f /var/log/cron.log
```

**Purpose:**
1. Loads `.env` file variables
2. Exports variables to `/etc/environment` (accessible to cron)
3. Installs crontab from `/etc/cron.d/usdclp-{horizon}`
4. Starts cron daemon in foreground (keeps container running)
5. Tails cron logs for Docker visibility

**For New Horizons:**
Create similar entrypoint scripts with service-specific references:
- `cron/15d/entrypoint.sh` → references `/etc/cron.d/usdclp-15d`
- `cron/30d/entrypoint.sh` → references `/etc/cron.d/usdclp-30d`
- `cron/90d/entrypoint.sh` → references `/etc/cron.d/usdclp-90d`

---

### 1.6 Configuration Constants

**File: `src/forex_core/config/constants.py`**

Current constants:
```python
# Timezone
LOCAL_TZ = ZoneInfo("America/Santiago")

# Forecast horizons
PROJECTION_DAYS = 7                              # 7-day
PROJECTION_MONTHS = 12                           # 12-month

# Historical lookback periods
HISTORICAL_LOOKBACK_DAYS_7D = 120                # ~4 months
HISTORICAL_LOOKBACK_DAYS_12M = 365 * 3           # 3 years

# Technical analysis lookback
TECH_LOOKBACK_DAYS_7D = 60                       # ~2 months
TECH_LOOKBACK_DAYS_12M = 120                     # ~4 months

# Volatility lookback
VOL_LOOKBACK_DAYS_7D = 30                        # 1 month
VOL_LOOKBACK_DAYS_12M = 120                      # ~4 months
```

**For New Horizons:**
Add constants (suggested values):
```python
PROJECTION_DAYS_15D = 15
PROJECTION_DAYS_30D = 30
PROJECTION_DAYS_90D = 90

HISTORICAL_LOOKBACK_DAYS_15D = 150               # ~5 months
HISTORICAL_LOOKBACK_DAYS_30D = 180               # ~6 months
HISTORICAL_LOOKBACK_DAYS_90D = 365               # 1 year

TECH_LOOKBACK_DAYS_15D = 60                      # ~2 months
TECH_LOOKBACK_DAYS_30D = 60                      # ~2 months
TECH_LOOKBACK_DAYS_90D = 90                      # ~3 months

VOL_LOOKBACK_DAYS_15D = 30                       # 1 month
VOL_LOOKBACK_DAYS_30D = 30                       # 1 month
VOL_LOOKBACK_DAYS_90D = 60                       # 2 months
```

---

## Part 2: Chart and Reporting System

### 2.1 Chart System Overview

The system generates 6 professional charts per forecast:

1. **Historical + Forecast** (30d history + forecast period)
   - Blue line: Historical USD/CLP data
   - Red line: Forecast mean
   - Orange band: 80% confidence interval
   - Violet band: 95% confidence interval

2. **Confidence Bands (Fan Chart)** (forecast period only)
   - Green line: Forecast mean
   - Orange band: 80% confidence interval
   - Violet band: 95% confidence interval

3. **Technical Indicators Panel** (30d history)
   - RSI (Relative Strength Index)
   - MACD (Moving Average Convergence Divergence)
   - Bollinger Bands

4. **Correlation Matrix** (heatmap)
   - 5-series correlation: USD/CLP, DXY, Copper, VIX, TPM

5. **Macro Drivers Dashboard** (5-day changes)
   - DXY index change
   - VIX index change
   - EEM index change
   - TPM rate change

6. **Risk Regime Visualization** (4-panel assessment)
   - Volatility regime
   - Trend regime
   - Mean reversion regime
   - Market confidence assessment

---

### 2.2 Color Scheme (Official Standard)

**Documentation:** `docs/CHARTING_COLOR_SCHEME.md`

#### Confidence Interval Colors
- **80% CI (More Probable):** DarkOrange `#FF8C00` (alpha: 0.35)
- **95% CI (Extended Range):** DarkViolet `#8B00FF` (alpha: 0.25)

#### Line Colors
- **Historical Data:** Steel Blue `#1f77b4` (width: 2px)
- **Forecast Mean (Chart 1):** Crimson Red `#d62728` (width: 2px)
- **Forecast Mean (Chart 2):** Green `#2ca02c` (width: 2px)

**Key Implementation Detail:**
Date label formatting has been standardized to prevent overlapping:
- Format: "15-Nov" (short format)
- Rotation: 45°
- Ticks: 6-8 maximum on x-axis
- Function: `_format_date_axis()` helper in `charting.py`

---

### 2.3 PDF Report Structure

**Current Report Layout (7-day):**

Pages 1-2: Executive Summary
- Forecast table with confidence intervals
- Key statistics and brief interpretation

Pages 3-4: Technical Analysis
- Chart 1: Historical + Forecast
- Chart 2: Confidence Bands (fan chart)
- Chart 3: Technical Indicators Panel
- Statistical insights (RSI, MACD values)

Pages 5-6: Fundamental Analysis
- Chart 4: Correlation Matrix
- Chart 5: Macro Drivers Dashboard
- Fundamental market factors

Pages 7-8: Risk Assessment
- Chart 6: Risk Regime Visualization
- Risk factor analysis

Pages 9-11: Methodology & Background
- Detailed model justification (2-3 pages)
- Model selection rationale
- Weight determination formula
- Model limitations

Pages 12-14: Interpretation & Recommendations
- Chart explanations (didactic content)
- Trading implications
- Key drivers analysis
- Conclusion and disclaimer

**Report Generation Code:**
- Main builder: `src/forex_core/reporting/builder.py`
- Charting: `src/forex_core/reporting/charting.py` (870+ lines)
- Explanations: `src/forex_core/reporting/chart_interpretations.py`

---

## Part 3: Implementation Roadmap

### Phase 1: Configuration Setup (Lowest Effort, High Value)

**3.1 Add Constants**

File: `src/forex_core/config/constants.py`

Add constants for each new horizon:
```python
# 15-day forecast
PROJECTION_DAYS_15D = 15
HISTORICAL_LOOKBACK_DAYS_15D = 150
TECH_LOOKBACK_DAYS_15D = 60
VOL_LOOKBACK_DAYS_15D = 30
BASE_PROMPT_15D = "..."  # Spanish prompt

# 30-day forecast
PROJECTION_DAYS_30D = 30
HISTORICAL_LOOKBACK_DAYS_30D = 180
TECH_LOOKBACK_DAYS_30D = 60
VOL_LOOKBACK_DAYS_30D = 30
BASE_PROMPT_30D = "..."

# 90-day forecast
PROJECTION_DAYS_90D = 90
HISTORICAL_LOOKBACK_DAYS_90D = 365
TECH_LOOKBACK_DAYS_90D = 90
VOL_LOOKBACK_DAYS_90D = 60
BASE_PROMPT_90D = "..."
```

**Effort:** ~30 minutes
**Files Modified:** 1
**Risk:** None (additive only)

---

### Phase 2: Service Structure Creation

**3.2 Create Forecaster Service Directories**

Replicate structure for each horizon:

```bash
# Create directory structure
mkdir -p src/services/forecaster_15d
mkdir -p src/services/forecaster_30d
mkdir -p src/services/forecaster_90d

# Copy files from 7d as template
cp src/services/forecaster_7d/__init__.py src/services/forecaster_15d/
cp src/services/forecaster_7d/cli.py src/services/forecaster_15d/
cp src/services/forecaster_7d/config.py src/services/forecaster_15d/
cp src/services/forecaster_7d/pipeline.py src/services/forecaster_15d/

# Repeat for 30d and 90d
```

**Files to Create:**

For each horizon (15d, 30d, 90d):

1. `src/services/forecaster_XD/__init__.py`
   - Simple module initialization
   - Can copy directly from forecaster_7d

2. `src/services/forecaster_XD/config.py`
   - Modify `horizon` type: "15-day" or "30-day" (or keep "daily")
   - Update `projection_days`: 15, 30, or 90
   - Update `frequency`: "D" (all remain daily)
   - Update `historical_lookback_days`: Use new constants
   - Update `tech_lookback_days`: Use new constants
   - Update `vol_lookback_days`: Use new constants
   - Update `report_title`: "Proyección USD/CLP - Próximos 15 Días", etc.
   - Update `report_filename_prefix`: "Forecast_15D_USDCLP", etc.
   - Update `chart_title_suffix`: "(15 días)", etc.
   - Update class name: `Forecaster15DConfig`, `Forecaster30DConfig`, `Forecaster90DConfig`
   - Update function: `get_service_config()` returns correct type

3. `src/services/forecaster_XD/cli.py`
   - Find & replace all "7d" → "15d", "30d", "90d"
   - Update app name: `name="forecaster-15d"`, etc.
   - Update help text
   - Update log file paths: "logs/forecaster_15d.log", etc.
   - Update console messages to reflect horizon

4. `src/services/forecaster_XD/pipeline.py`
   - Find & replace service-specific imports
   - No business logic changes required (uses generic ForecastEngine)
   - Update log messages if present

**Effort:** ~1 hour (mostly copy-paste and find-replace)
**Files Created:** 12 (4 per horizon)
**Risk:** Low (copy pattern from working service)

---

### Phase 3: Docker Configuration

**3.3 Create Dockerfiles**

For each horizon, create two versions:

**Dockerfile.15d** (development)
```dockerfile
FROM python:3.12-slim
# ... same as Dockerfile.7d but different forecast logic
# References: cron/15d/crontab, cron/15d/entrypoint.sh
# Service calls: python -m services.forecaster_15d.cli run
```

**Dockerfile.15d.prod** (production)
```dockerfile
# ... same as Dockerfile.7d.prod but with 15d references
# COPY cron/15d/crontab /etc/cron.d/usdclp-15d
# COPY cron/15d/entrypoint.sh /entrypoint.sh
```

**Key Differences to Update in Dockerfile:**
- `COPY cron/XD/crontab` → reference correct horizon
- `COPY cron/XD/entrypoint.sh` → reference correct horizon
- HEALTHCHECK interval/timing can be adjusted per horizon

**Effort:** ~20 minutes (copy + edit)
**Files Created:** 6 (2 per horizon)
**Risk:** Low

---

### Phase 4: Cron Configuration

**3.4 Create Cron Scripts**

For each horizon, create cron directory with crontab and entrypoint:

**cron/15d/crontab**
```cron
# USD/CLP 15-Day Forecast - Day 1 and 15 of each month at 9:00 AM Chile time
0 9 1,15 * * cd /app && python -m services.forecaster_15d.cli run >> /var/log/cron.log 2>&1

# Health check - write timestamp every hour
0 * * * * date > /tmp/healthcheck
```

**cron/15d/entrypoint.sh**
```bash
#!/usr/bin/env bash
set -e

echo "🚀 Starting USD/CLP 15-Day Forecaster Service"
# ... (copy from 7d/entrypoint.sh and update references)
# Change: crontab /etc/cron.d/usdclp-15d
```

**Cron Schedules for All Horizons:**
```cron
# 15-day: Day 1 and 15 at 9:00 AM
0 9 1,15 * * cd /app && python -m services.forecaster_15d.cli run >> /var/log/cron.log 2>&1

# 30-day: Day 1 at 9:30 AM
30 9 1 * * cd /app && python -m services.forecaster_30d.cli run >> /var/log/cron.log 2>&1

# 90-day: Day 1 at 10:00 AM
0 10 1 * * cd /app && python -m services.forecaster_90d.cli run >> /var/log/cron.log 2>&1

# Health checks (same for all)
0 * * * * date > /tmp/healthcheck
```

**Effort:** ~30 minutes (copy + customize)
**Files Created:** 6 (2 per horizon)
**Risk:** Low

---

### Phase 5: Docker Compose Update

**3.5 Update docker-compose.prod.yml**

Add service blocks for each new horizon:

```yaml
version: "3.8"

services:
  forecaster-7d:
    # ... existing 7d configuration

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
    # ... similar to 15d but with Dockerfile.30d.prod, etc.

  forecaster-90d:
    # ... similar to 15d but with Dockerfile.90d.prod, etc.
```

**Effort:** ~30 minutes
**Files Modified:** 1
**Risk:** Low (additive)

---

### Phase 6: Deployment & Testing

**3.6 Local Testing**

```bash
# Test individual forecasters locally
docker build -f Dockerfile.15d -t forecaster-15d .
docker run -it --env-file .env forecaster-15d python -m services.forecaster_15d.cli validate

# Test full pipeline
docker run -it --env-file .env forecaster-15d python -m services.forecaster_15d.cli run --skip-email
```

**3.7 Production Deployment**

```bash
# On Vultr server
cd /home/deployer/forex-forecast-system
git pull origin develop

# Build new containers
docker compose -f docker-compose.prod.yml build

# Start all forecasters
docker compose -f docker-compose.prod.yml up -d

# Verify all services running
docker ps | grep forecaster
```

**3.8 Verification Checklist**

For each new forecaster:
- [ ] Container starts without errors
- [ ] Cron job is installed and visible
- [ ] Health check passes
- [ ] Manual execution works: `docker exec usdclp-forecaster-15d python -m services.forecaster_15d.cli run --skip-email`
- [ ] PDF report generated correctly
- [ ] Email sent with report attached (if configured)
- [ ] Log file created: `/var/log/cron.log`

---

## Part 4: Code Reuse & Shared Components

### 4.1 Shared Components (No Duplication)

All forecasters share these components:

**Data Loading:**
- `forex_core.data.DataLoader` - Multi-source data fetching
- Supports FRED, Yahoo Finance, Mindicador, AlphaVantage APIs

**Forecasting Engine:**
- `forex_core.forecasting.ForecastEngine` - Ensemble forecasting
- 3 models: ARIMA+GARCH, VAR, Random Forest
- Configurable horizon and steps

**Charting:**
- `forex_core.reporting.charting` - All chart generation
- Handles 6 standard charts + legends + source attribution
- Color scheme standardization

**Report Building:**
- `forex_core.reporting.builder` - PDF assembly
- WeasyPrint-based HTML-to-PDF conversion
- Consistent layout across horizons

**Email Notifications:**
- `forex_core.notifications.email` - Gmail SMTP delivery
- Attachment handling
- Error logging

**Key Insight:**
Only configuration and CLI differ per horizon. Core logic is horizon-agnostic and parameterized by:
- `projection_days`: Number of days to forecast
- `frequency`: Data frequency ("D" for daily)
- `historical_lookback_days`: How much history to use

---

### 4.2 Configuration-Driven Architecture

All behavior changes through service config:

```python
# forecaster_15d/config.py
@dataclass(frozen=True)
class Forecaster15DConfig:
    horizon: Literal["daily"] = "daily"
    projection_days: int = 15
    frequency: str = "D"
    historical_lookback_days: int = 150
    tech_lookback_days: int = 60
    vol_lookback_days: int = 30
    report_title: str = "Proyección USD/CLP - Próximos 15 Días"
    # ... rest of config
```

Pipeline calls:
```python
# forecaster_15d/pipeline.py
def run_forecast_pipeline(...):
    config = get_service_config()  # Returns Forecaster15DConfig

    engine = ForecastEngine(
        config=settings,
        horizon=config.horizon,      # "daily"
        steps=config.projection_days  # 15 for this service
    )

    # Rest is identical for all horizons
    forecast = engine.forecast(bundle)
    chart_engine = ChartEngine(config=settings)
    charts = chart_engine.generate_all_charts(forecast, config)
    # ... etc
```

---

## Part 5: Scheduling & Timezone Considerations

### 5.1 Cron Schedule Details

**Important:** All times are interpreted as the **container's local time zone**, which should be set to America/Santiago (Chile).

#### How Cron Times Work
```
Minute (0-59) | Hour (0-23) | Day of Month | Month | Day of Week
```

**24-hour format examples:**
- 08:00 (8 AM) → `0 8 * * *`
- 09:00 (9 AM) → `0 9 * * *`
- 09:30 (9:30 AM) → `30 9 * * *`
- 10:00 (10 AM) → `0 10 * * *`

#### Specific Dates
- Day 1 and 15 of month → `0 9 1,15 * *` (any month, any year)
- Day 1 only → `0 9 1 * *`
- First and third Monday → `0 9 * * 1` (combined with day logic)

**Verification on Server:**
```bash
# Check system timezone
timedatectl

# Check container timezone
docker exec usdclp-forecaster-7d date
docker exec usdclp-forecaster-7d cat /etc/timezone

# Check when cron job last ran
docker exec usdclp-forecaster-7d tail -50 /var/log/cron.log
```

---

### 5.2 Environment Variable: REPORT_TIMEZONE

**Current Setting:** `America/Santiago` (Chile standard time)

This affects:
- Report timestamp generation
- Chart date labels
- Email timestamp in subject line
- Log entries

**Verification:**
```bash
# Check in running container
docker exec usdclp-forecaster-7d env | grep REPORT_TIMEZONE

# Check in .env file on server
grep REPORT_TIMEZONE /home/deployer/forex-forecast-system/.env
```

---

## Part 6: Email Delivery Configuration

### 6.1 Gmail Configuration

**Required Environment Variables (from `.env`):**

```env
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_specific_password
EMAIL_RECIPIENTS=recipient1@email.com,recipient2@email.com
```

**Important Note:**
- Use **Gmail App Password** (not regular password)
- Enable 2-factor authentication first
- Generate app-specific password in Google Account settings

**Implementation:**
```python
# In email sending code
smtp.login(settings.gmail_user, settings.gmail_app_password)
smtp.send_message(msg, from_addr=settings.gmail_user)
```

---

### 6.2 Email Delivery by Horizon

Each forecaster can have the same or different recipients:

**Option 1: Same Recipients for All**
```env
# .env
EMAIL_RECIPIENTS=rafael@cavara.cl,valentina@cavara.cl
```
All forecasters (7d, 15d, 30d, 90d) send to same addresses.

**Option 2: Different Recipients Per Horizon**
Modify code to read `EMAIL_RECIPIENTS_15D`, `EMAIL_RECIPIENTS_30D`, etc.

**Current Implementation:** All forecasters use same recipients list.

---

## Part 7: Monitoring & Logging

### 7.1 Cron Logs

**Location in Container:** `/var/log/cron.log` (persistent volume mount)
**Location on Host:** `/home/deployer/forex-forecast-system/logs/cron.log`

**Viewing Logs:**
```bash
# Last 50 lines
docker exec usdclp-forecaster-7d tail -50 /var/log/cron.log

# Follow in real-time
docker exec usdclp-forecaster-7d tail -f /var/log/cron.log

# Search for errors
docker exec usdclp-forecaster-7d grep ERROR /var/log/cron.log

# View last execution
docker exec usdclp-forecaster-7d grep -A 5 "Forecast completed" /var/log/cron.log
```

### 7.2 Health Checks

**Healthcheck Mechanism:**
- Every cron job writes timestamp to `/tmp/healthcheck`
- Docker healthcheck verifies file exists and is less than 2 hours old
- If healthcheck fails 3 times, container restarts

**Status:**
```bash
docker inspect usdclp-forecaster-7d | grep -A 20 Health
```

**Expected Output:**
```json
"Health": {
  "Status": "healthy",
  "FailingStreak": 0,
  "Log": [
    {
      "Start": "2025-11-13T12:00:00Z",
      "End": "2025-11-13T12:00:05Z",
      "ExitCode": 0,
      "Output": ""
    }
  ]
}
```

### 7.3 Report Verification

**Check Latest Report Generated:**
```bash
# On server
ls -lth /home/deployer/forex-forecast-system/reports/ | head -5

# Expected output format
-rw-r--r-- 1 deployer staff 1.5M Nov 13 08:15 usdclp_report_7d_20251113_081500.pdf
```

**PDF Size Expectations:**
- 7-day: ~1.5 MB
- 15-day: ~1.5 MB
- 30-day: ~1.7 MB
- 90-day: ~2.0 MB

---

## Part 8: Troubleshooting Guide

### Common Issues & Solutions

#### 8.1 Cron Job Not Executing

**Symptom:** No new reports generated at scheduled time

**Diagnosis:**
```bash
# 1. Check container is running
docker ps | grep forecaster

# 2. Verify crontab is installed
docker exec usdclp-forecaster-15d crontab -l

# 3. Check cron daemon is running
docker exec usdclp-forecaster-15d ps aux | grep cron

# 4. Check for errors in log
docker exec usdclp-forecaster-15d tail -100 /var/log/cron.log
```

**Solutions:**
- Restart container: `docker restart usdclp-forecaster-15d`
- Rebuild container: `docker compose -f docker-compose.prod.yml up -d forecaster-15d`
- Check crontab syntax: https://crontab.guru

#### 8.2 Email Not Sent

**Symptom:** Report generated but email not received

**Diagnosis:**
```bash
# 1. Check Gmail credentials
docker exec usdclp-forecaster-15d env | grep GMAIL

# 2. Check email logs
docker exec usdclp-forecaster-15d tail -50 /var/log/cron.log | grep -i email

# 3. Run with debug logging
docker exec usdclp-forecaster-15d python -m services.forecaster_15d.cli run -l DEBUG
```

**Solutions:**
- Verify Gmail app password is correct
- Check 2FA is enabled on Gmail account
- Verify recipients list in EMAIL_RECIPIENTS
- Check email logs for SMTP errors

#### 8.3 Forecast Generation Fails

**Symptom:** Cron log shows "Pipeline failed"

**Diagnosis:**
```bash
# Run manually with debug output
docker exec usdclp-forecaster-15d python -m services.forecaster_15d.cli run --skip-email -l DEBUG

# Check API keys
docker exec usdclp-forecaster-15d python -m services.forecaster_15d.cli info
```

**Common Causes:**
- Missing API keys (FRED_API_KEY, NEWS_API_KEY)
- No internet connection / API timeout
- Insufficient data for calculations
- Disk space issue (check /app/reports)

---

## Part 9: Testing Strategy

### 9.1 Local Testing Before Deployment

**Environment Setup:**
```bash
# Create local .env file
cp .env.example .env
# Edit .env with test values

# Test without Docker
source venv/bin/activate
python -m services.forecaster_15d.cli info
python -m services.forecaster_15d.cli validate
python -m services.forecaster_15d.cli run --skip-email
```

**Docker Testing:**
```bash
# Build image
docker build -f Dockerfile.15d -t test-forecaster-15d .

# Run with volume mount for inspection
docker run -it \
  --env-file .env \
  -v $(pwd)/reports:/app/reports \
  -v $(pwd)/logs:/app/logs \
  test-forecaster-15d \
  python -m services.forecaster_15d.cli run --skip-email
```

### 9.2 Production Validation

After deploying to Vultr:

**Immediate (Day 0):**
1. Verify container status: `docker ps`
2. Verify healthcheck: `docker inspect usdclp-forecaster-15d | grep Health`
3. Manual execution: `docker exec usdclp-forecaster-15d python -m services.forecaster_15d.cli run --skip-email`
4. Check output: `ls -lth /home/deployer/forex-forecast-system/reports/`

**Daily (Next 7 Days):**
1. Check if cron job executed: `tail -20 /var/log/cron.log` (inside container)
2. Verify PDF generated: `ls -lth /home/deployer/forex-forecast-system/reports/ | grep 15d`
3. Spot-check PDF quality: Download and verify visually
4. Monitor logs for errors: Watch for exception stacktraces

**Weekly:**
1. Check email delivery logs
2. Verify all 3 new forecasters running (15d, 30d, 90d)
3. Compare report quality across horizons
4. Validate schedule accuracy (dates match cron spec)

---

## Part 10: Configuration Checklist

### Pre-Implementation

- [ ] Review constants.py updates needed
- [ ] Understand service architecture (cli, config, pipeline pattern)
- [ ] Review Dockerfile.7d.prod as template
- [ ] Understand cron scheduling syntax
- [ ] Verify America/Santiago timezone in environment

### Implementation Checklist

- [ ] Add constants for 15d, 30d, 90d in config/constants.py
- [ ] Create forecaster_15d service structure
- [ ] Create forecaster_30d service structure
- [ ] Create forecaster_90d service structure
- [ ] Create Dockerfile.15d and Dockerfile.15d.prod
- [ ] Create Dockerfile.30d and Dockerfile.30d.prod
- [ ] Create Dockerfile.90d and Dockerfile.90d.prod
- [ ] Create cron/15d/crontab and cron/15d/entrypoint.sh
- [ ] Create cron/30d/crontab and cron/30d/entrypoint.sh
- [ ] Create cron/90d/crontab and cron/90d/entrypoint.sh
- [ ] Update docker-compose.prod.yml with 3 new services
- [ ] Test locally with Docker
- [ ] Deploy to Vultr
- [ ] Verify all containers running
- [ ] Test manual execution for each forecaster
- [ ] Verify cron schedules via logs
- [ ] Monitor first scheduled execution
- [ ] Verify email delivery

### Post-Implementation

- [ ] Document in PRODUCTION_DEPLOYMENT.md
- [ ] Update CHANGELOG.md with new features
- [ ] Create training docs for operations team
- [ ] Set up monitoring/alerting for new services
- [ ] Archive this implementation guide

---

## Appendix A: File Locations Summary

### Source Code Structure
```
src/
├── forex_core/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── base.py           # Settings class
│   │   └── constants.py       # PROJECTION_DAYS, lookback periods, etc.
│   ├── data/
│   ├── forecasting/
│   ├── reporting/
│   │   ├── builder.py         # PDF assembly
│   │   ├── charting.py        # Chart generation (870+ lines)
│   │   └── chart_interpretations.py
│   └── notifications/
│       └── email.py           # Gmail delivery
│
└── services/
    ├── forecaster_7d/
    │   ├── __init__.py
    │   ├── cli.py             # Typer CLI
    │   ├── config.py           # Forecaster7DConfig
    │   └── pipeline.py         # run_forecast_pipeline()
    │
    ├── forecaster_12m/         # Similar structure
    │
    ├── forecaster_15d/         # TO BE CREATED
    ├── forecaster_30d/         # TO BE CREATED
    └── forecaster_90d/         # TO BE CREATED
```

### Docker/Cron Configuration
```
cron/
├── 7d/
│   ├── crontab         # 0 8 * * * ...
│   └── entrypoint.sh   # Container startup
│
└── [15d, 30d, 90d]/   # TO BE CREATED (same structure)

Dockerfile files:
├── Dockerfile.7d        # Local development
├── Dockerfile.7d.prod   # Production (with cron)
├── Dockerfile.15d       # Local development (new)
├── Dockerfile.15d.prod  # Production (new)
├── Dockerfile.30d       # (new)
├── Dockerfile.30d.prod  # (new)
├── Dockerfile.90d       # (new)
└── Dockerfile.90d.prod  # (new)

docker-compose.prod.yml  # Update with 3 new services
```

### Documentation
```
docs/
├── CHARTING_COLOR_SCHEME.md           # Color standard
├── PRODUCTION_DEPLOYMENT.md           # Current deployment guide
└── NEW_FORECAST_HORIZONS_IMPLEMENTATION_GUIDE.md  # This file
```

---

## Appendix B: Reference Links

**Current Implementation Examples:**

1. **7-Day Service Configuration:**
   - Config: `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/services/forecaster_7d/config.py`
   - CLI: `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/services/forecaster_7d/cli.py`
   - Pipeline: `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/services/forecaster_7d/pipeline.py`

2. **Docker Configuration:**
   - Dockerfile: `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/Dockerfile.7d.prod`
   - Compose: `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/docker-compose.prod.yml`
   - Cron: `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/cron/7d/`

3. **Core Configuration:**
   - Constants: `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/config/constants.py`
   - Base Settings: `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/config/base.py`

4. **Reporting:**
   - Charting: `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/charting.py`
   - Builder: `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src/forex_core/reporting/builder.py`
   - Color Scheme: `/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/docs/CHARTING_COLOR_SCHEME.md`

---

## Appendix C: Quick Commands Reference

### Local Testing
```bash
# Validate without report
python -m services.forecaster_15d.cli validate -l DEBUG

# Generate report locally
python -m services.forecaster_15d.cli run --skip-email -l DEBUG

# Check configuration
python -m services.forecaster_15d.cli info
```

### Docker Operations
```bash
# Build specific Dockerfile
docker build -f Dockerfile.15d.prod -t forecaster-15d .

# Build all services in compose
docker compose -f docker-compose.prod.yml build

# Start specific service
docker compose -f docker-compose.prod.yml up -d forecaster-15d

# View logs
docker logs -f usdclp-forecaster-15d

# Execute command in running container
docker exec usdclp-forecaster-15d python -m services.forecaster_15d.cli run

# View cron logs
docker exec usdclp-forecaster-15d tail -f /var/log/cron.log
```

### Server Operations (Vultr)
```bash
# SSH to server
ssh reporting  # configured alias

# Pull changes
cd /home/deployer/forex-forecast-system
git pull origin develop

# Rebuild containers
docker compose -f docker-compose.prod.yml build

# Restart all forecasters
docker compose -f docker-compose.prod.yml restart

# Monitor container status
watch -n 5 'docker ps | grep forecaster'
```

---

## Conclusion

This implementation follows the established patterns in the codebase and requires minimal changes to core logic. The main work involves:

1. **Configuration** (30 mins): Add constants
2. **Service Replication** (1 hour): Create 12 files by copying and find-replacing
3. **Docker Setup** (1 hour): Create Dockerfiles and cron configs
4. **Compose Update** (30 mins): Add service definitions
5. **Testing** (2 hours): Local and production validation

**Total Estimated Effort:** 5-6 hours
**Risk Level:** Low (follows existing patterns)
**Breaking Changes:** None
**Deployment Impact:** Additive only (existing services unaffected)

The key architectural advantage is that all business logic resides in `forex_core`, and new horizons are just configuration changes to the forecasting parameters.

---

**Document Version:** 1.0
**Last Updated:** 2025-11-13
**Author:** Development Team
**Status:** Ready for Implementation Planning
