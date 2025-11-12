# CLI Usage Guide - Forex Forecast Services

Quick reference guide for running the three forecast services via command-line interface.

## Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Configure environment variables (copy from .env.example)
cp .env.example .env
# Edit .env with your API keys
```

---

## Service 1: Forecaster 7D (Short-term Daily Forecast)

### Quick Start

```bash
# Run complete 7-day forecast (with email)
python -m services.forecaster_7d.cli run

# Run without email
python -m services.forecaster_7d.cli run --skip-email

# Custom output directory
python -m services.forecaster_7d.cli run --output-dir ./my_reports --skip-email
```

### Validation & Testing

```bash
# Validate forecast generation (no report/email)
python -m services.forecaster_7d.cli validate

# Debug mode with detailed logs
python -m services.forecaster_7d.cli validate --log-level DEBUG

# Save logs to custom file
python -m services.forecaster_7d.cli run --log-file ./logs/my_forecast.log
```

### Configuration Info

```bash
# Display service configuration
python -m services.forecaster_7d.cli info
```

### Help

```bash
# Show all available commands
python -m services.forecaster_7d.cli --help

# Show help for specific command
python -m services.forecaster_7d.cli run --help
```

---

## Service 2: Forecaster 12M (Long-term Monthly Forecast)

### Quick Start

```bash
# Run complete 12-month forecast (with email)
python -m services.forecaster_12m.cli run

# Run without email
python -m services.forecaster_12m.cli run --skip-email

# Custom output directory
python -m services.forecaster_12m.cli run --output-dir ./my_reports --skip-email
```

### Validation & Testing

```bash
# Validate forecast generation (no report/email)
python -m services.forecaster_12m.cli validate

# Debug mode with detailed logs
python -m services.forecaster_12m.cli validate --log-level DEBUG

# Save logs to custom file
python -m services.forecaster_12m.cli run --log-file ./logs/my_forecast.log
```

### Configuration Info

```bash
# Display service configuration
python -m services.forecaster_12m.cli info
```

### Help

```bash
# Show all available commands
python -m services.forecaster_12m.cli --help

# Show help for specific command
python -m services.forecaster_12m.cli run --help
```

---

## Service 3: Importer Report (Comprehensive Monthly Report)

### Quick Start

```bash
# Generate comprehensive monthly report (with email)
python -m services.importer_report.cli run

# Generate without email
python -m services.importer_report.cli run --skip-email

# Custom output directory
python -m services.importer_report.cli run --output-dir ./monthly_reports --skip-email
```

### Preview & Planning

```bash
# Preview report sections before generation
python -m services.importer_report.cli preview

# Preview with debug details
python -m services.importer_report.cli preview --log-level DEBUG
```

### Configuration Info

```bash
# Display service configuration
python -m services.importer_report.cli info
```

### Help

```bash
# Show all available commands
python -m services.importer_report.cli --help

# Show help for specific command
python -m services.importer_report.cli run --help
```

---

## Common Options

All services support these common command-line options:

### Output Options

```bash
--output-dir, -o PATH    # Custom output directory for reports
--skip-email             # Skip email delivery (default: False)
```

### Logging Options

```bash
--log-level, -l LEVEL    # Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
--log-file PATH          # Path to log file (default: logs/<service>.log)
```

### Example: Full Custom Run

```bash
python -m services.forecaster_7d.cli run \
    --output-dir ./custom_reports \
    --skip-email \
    --log-level DEBUG \
    --log-file ./logs/custom_run.log
```

---

## Scheduling with Cron

### Daily 7-day Forecast (every day at 8:00 AM)

```bash
# Edit crontab
crontab -e

# Add entry
0 8 * * * cd /path/to/forex-forecast-system && export PYTHONPATH="$PYTHONPATH:$(pwd)/src" && python -m services.forecaster_7d.cli run >> /var/log/forecaster_7d.log 2>&1
```

### Monthly 12-month Forecast (first day of month at 9:00 AM)

```bash
0 9 1 * * cd /path/to/forex-forecast-system && export PYTHONPATH="$PYTHONPATH:$(pwd)/src" && python -m services.forecaster_12m.cli run >> /var/log/forecaster_12m.log 2>&1
```

### Monthly Importer Report (first day of month at 10:00 AM)

```bash
0 10 1 * * cd /path/to/forex-forecast-system && export PYTHONPATH="$PYTHONPATH:$(pwd)/src" && python -m services.importer_report.cli run >> /var/log/importer_report.log 2>&1
```

---

## Troubleshooting

### Import Errors

If you get `ModuleNotFoundError`:

```bash
# Ensure PYTHONPATH is set correctly
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Or use absolute path
export PYTHONPATH="${PYTHONPATH}:/full/path/to/forex-forecast-system/src"
```

### Missing Dependencies

```bash
# Install all requirements
pip install -r requirements.txt

# Or install specific packages
pip install typer rich loguru pydantic pandas numpy
```

### API Key Errors

If you get API key errors:

```bash
# Check .env file exists
ls -la .env

# Verify API keys are set
cat .env | grep API_KEY

# Test configuration
python -m services.forecaster_7d.cli info
```

### Permission Errors

If you get permission errors on output directories:

```bash
# Create directories manually
mkdir -p ./reports ./logs ./charts ./data

# Set permissions
chmod 755 ./reports ./logs ./charts ./data
```

---

## Output Files

### Forecaster 7D

```
./reports/
└── Forecast_7D_USDCLP_20250112_143022.pdf

./logs/
└── forecaster_7d.log

./charts/
├── usdclp_7d_forecast.png
├── usdclp_7d_trend.png
└── volatility_7d.png
```

### Forecaster 12M

```
./reports/
└── Forecast_12M_USDCLP_20250112_143522.pdf

./logs/
└── forecaster_12m.log

./charts/
├── usdclp_12m_forecast.png
├── usdclp_12m_trend.png
└── seasonality_12m.png
```

### Importer Report

```
./reports/
└── Informe_Entorno_Importador_20250112_144022.pdf

./logs/
└── importer_report.log

./charts/
├── usdclp_dual_forecast.png
├── pestel_radar.png
├── porter_spider.png
├── sector_comparison.png
└── risk_matrix.png
```

---

## Advanced Usage

### Running Multiple Services in Sequence

```bash
#!/bin/bash
# run_all_forecasts.sh

# Set environment
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Run 7-day forecast
echo "Running 7-day forecast..."
python -m services.forecaster_7d.cli run --skip-email

# Run 12-month forecast
echo "Running 12-month forecast..."
python -m services.forecaster_12m.cli run --skip-email

# Run comprehensive report
echo "Running importer report..."
python -m services.importer_report.cli run --skip-email

echo "All forecasts complete!"
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY .env .env

# Set PYTHONPATH
ENV PYTHONPATH="${PYTHONPATH}:/app/src"

# Run service
CMD ["python", "-m", "services.forecaster_7d.cli", "run"]
```

```bash
# Build image
docker build -t forex-forecaster-7d .

# Run container
docker run -v $(pwd)/reports:/app/reports forex-forecaster-7d
```

---

## Performance Tips

1. **Use validation mode first** to test without generating full reports
2. **Enable caching** by setting `CACHE_TTL_MINUTES` in .env
3. **Adjust ensemble window** with `ENSEMBLE_WINDOW` (smaller = faster)
4. **Disable unused models** via `ENABLE_ARIMA`, `ENABLE_VAR`, `ENABLE_RF`

---

## Support

For issues or questions:
1. Check logs in `./logs/` directory
2. Run with `--log-level DEBUG` for detailed output
3. Verify configuration with `info` command
4. Test forecasts with `validate` command

---

## Quick Reference Card

| Service | Command | Purpose |
|---------|---------|---------|
| 7D | `python -m services.forecaster_7d.cli run` | 7-day forecast |
| 12M | `python -m services.forecaster_12m.cli run` | 12-month forecast |
| Report | `python -m services.importer_report.cli run` | Comprehensive report |
| Any | `<command> --skip-email` | Skip email delivery |
| Any | `<command> --log-level DEBUG` | Debug mode |
| Any | `<command> info` | Show configuration |
| Any | `<command> validate` | Test without reports |
| Any | `<command> --help` | Show help |

---

Generated with Claude Code - December 2024
