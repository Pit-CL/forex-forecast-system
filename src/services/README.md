# Services Layer

This directory contains thin service wrappers around the `forex_core` library. Each service provides specific configuration, orchestration, and CLI interfaces for different forecast horizons and report types.

## Architecture Overview

```
services/
├── forecaster_7d/         # 7-day daily forecast service
├── forecaster_12m/        # 12-month monthly forecast service
└── importer_report/       # Comprehensive monthly report service
```

All services follow the same pattern:
1. **config.py** - Service-specific configuration overrides
2. **pipeline.py** - Orchestration logic (data → forecast → report → email)
3. **cli.py** - Command-line interface using Typer
4. **Additional modules** - Service-specific analysis (importer_report only)

## Services

### 1. Forecaster 7D (forecaster_7d)

**Purpose:** Short-term daily forex forecasting (7-day horizon)

**Configuration:**
- Horizon: `daily`
- Steps: 7 days
- Frequency: Daily (`D`)
- Lookback: 180 days historical data

**Usage:**
```bash
# Run full pipeline with email
python -m services.forecaster_7d.cli run

# Run without email
python -m services.forecaster_7d.cli run --skip-email

# Validate forecast generation
python -m services.forecaster_7d.cli validate

# Show configuration
python -m services.forecaster_7d.cli info

# Debug mode
python -m services.forecaster_7d.cli run --log-level DEBUG
```

**Files:**
- `__init__.py` - Package marker (10 lines)
- `config.py` - Service configuration (85 lines)
- `pipeline.py` - Pipeline orchestration (280 lines)
- `cli.py` - Command-line interface (330 lines)

**Total:** 705 lines

---

### 2. Forecaster 12M (forecaster_12m)

**Purpose:** Long-term monthly forex forecasting (12-month horizon)

**Configuration:**
- Horizon: `monthly`
- Steps: 12 months
- Frequency: Month-end (`ME`)
- Lookback: 730 days (2 years) historical data

**Key Features:**
- Automatic resampling to monthly frequency (`.resample("ME").last()`)
- Month-end date handling with `pd.offsets.MonthEnd(1)`
- Long-term trend analysis

**Usage:**
```bash
# Run full pipeline with email
python -m services.forecaster_12m.cli run

# Run without email
python -m services.forecaster_12m.cli run --skip-email

# Validate forecast generation
python -m services.forecaster_12m.cli validate

# Show configuration
python -m services.forecaster_12m.cli info

# Custom output directory
python -m services.forecaster_12m.cli run -o ./my_reports
```

**Files:**
- `__init__.py` - Package marker (10 lines)
- `config.py` - Service configuration (92 lines)
- `pipeline.py` - Pipeline with monthly resampling (350 lines)
- `cli.py` - Command-line interface (335 lines)

**Total:** 787 lines

---

### 3. Importer Report (importer_report)

**Purpose:** Comprehensive monthly macro-economic report for Chilean importers

**Configuration:**
- Includes both 7-day and 12-month forecasts
- PESTEL analysis (Political, Economic, Social, Technological, Environmental, Legal)
- Porter's Five Forces analysis
- Sector-specific analysis (Restaurants, Retail, Manufacturing, Technology)
- Target: 10-20 page PDF report

**Key Features:**
- Dual forecast horizons (short-term + long-term)
- Strategic analysis frameworks
- Risk matrix and mitigation strategies
- Sector-specific recommendations
- Comprehensive data sources citation

**Usage:**
```bash
# Generate monthly report with email
python -m services.importer_report.cli run

# Generate without email
python -m services.importer_report.cli run --skip-email

# Preview report sections
python -m services.importer_report.cli preview

# Show configuration
python -m services.importer_report.cli info

# Custom output and debug
python -m services.importer_report.cli run -o ./reports -l DEBUG
```

**Files:**
- `__init__.py` - Package marker (11 lines)
- `config.py` - Service configuration (82 lines)
- `analysis.py` - Strategic analysis frameworks (360 lines)
- `sections.py` - Report section generators (280 lines)
- `pipeline.py` - Dual-forecast orchestration (260 lines)
- `cli.py` - Command-line interface (380 lines)

**Total:** 1,373 lines

---

## Common Patterns

### Pipeline Flow

All services follow this orchestration pattern:

```python
def run_forecast_pipeline(skip_email: bool = False, output_dir: Optional[Path] = None):
    # 1. Load configuration
    settings = get_settings()
    service_config = get_service_config()

    # 2. Load data
    loader = DataLoader(settings)
    bundle = loader.load()

    # 3. Generate forecast(s)
    engine = ForecastEngine(settings, horizon=..., steps=...)
    forecast, artifacts = engine.forecast(bundle)

    # 4. Generate charts (TODO: implement in forex_core)
    charts = ChartGenerator(settings).generate(bundle, forecast)

    # 5. Build report (TODO: implement in forex_core)
    report_path = ReportBuilder(settings).build(bundle, forecast, artifacts, charts)

    # 6. Send email (optional) (TODO: implement in forex_core)
    if not skip_email:
        EmailSender(settings).send(report_path)

    return report_path
```

### CLI Commands

All services provide these consistent commands:

- `run` - Execute full pipeline
- `validate` - Validate forecast without report generation
- `info` - Display configuration and environment
- `backtest` - Historical accuracy evaluation (TODO)

### Configuration Override Pattern

Services extend base `forex_core` configuration:

```python
@dataclass(frozen=True)
class ServiceConfig:
    horizon: Literal["daily", "monthly"]
    projection_days: int
    frequency: str
    report_title: str
    # ... service-specific settings
```

---

## Dependencies

All services depend on:
- `forex_core` - Core library with data, forecasting, and utilities
- `typer` - CLI framework
- `rich` - Terminal UI enhancements
- `loguru` - Logging (via forex_core)
- `pydantic` - Configuration validation (via forex_core)

### TODO: Pending forex_core Implementations

The following modules need to be implemented in `forex_core`:

1. **forex_core.reporting.ChartGenerator**
   - Generate matplotlib/plotly charts
   - Support both daily and monthly frequencies
   - Professional styling

2. **forex_core.reporting.ReportBuilder**
   - PDF generation with ReportLab or WeasyPrint
   - Template-based layout
   - Multi-section support

3. **forex_core.notifications.EmailSender**
   - Gmail SMTP integration
   - HTML email templates
   - Attachment handling

---

## Testing

Each service can be tested independently:

```bash
# Test 7-day forecaster
cd /path/to/forex-forecast-system
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
python -m services.forecaster_7d.cli validate

# Test 12-month forecaster
python -m services.forecaster_12m.cli validate

# Preview importer report
python -m services.importer_report.cli preview
```

---

## Code Statistics

Total lines of code: **3,062 lines**

Breakdown by service:
- **forecaster_7d:** 705 lines (23%)
- **forecaster_12m:** 787 lines (26%)
- **importer_report:** 1,373 lines (45%)
- **Package init:** 197 lines (6%)

File count: **15 files**
- 3 services
- 4 files per simple service (init, config, pipeline, cli)
- 6 files for complex service (+ analysis, sections)

---

## Environment Variables

Services inherit all environment variables from `forex_core`:

```bash
# Required
FRED_API_KEY=your_fred_key
NEWS_API_KEY=your_newsapi_key
ALPHAVANTAGE_API_KEY=your_alphavantage_key

# Email (optional)
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password
EMAIL_RECIPIENTS=recipient1@example.com,recipient2@example.com

# Directories
DATA_DIR=./data
OUTPUT_DIR=./reports
CHART_DIR=./charts
WAREHOUSE_DIR=./data/warehouse

# Model configuration
ENABLE_ARIMA=true
ENABLE_VAR=true
ENABLE_RF=true
ENSEMBLE_WINDOW=30

# General
ENVIRONMENT=production
REPORT_TIMEZONE=America/Santiago
```

---

## Next Steps

1. **Implement forex_core.reporting module:**
   - ChartGenerator class
   - ReportBuilder class

2. **Implement forex_core.notifications module:**
   - EmailSender class
   - Template system

3. **Testing:**
   - Unit tests for each service
   - Integration tests for full pipelines
   - Validation tests for forecasts

4. **Documentation:**
   - API documentation
   - User guides
   - Architecture diagrams

5. **Deployment:**
   - Docker containerization
   - Scheduling (cron/APScheduler)
   - Monitoring and alerts

---

## License

Part of forex-forecast-system project.

## Author

Generated with Claude Code.
