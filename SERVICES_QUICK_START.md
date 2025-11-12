# Services Quick Start Guide

Fast setup and testing guide for the three forecast services.

## 1. Installation (2 minutes)

```bash
# Navigate to project root
cd /Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system

# Install dependencies (if not already installed)
pip install typer rich loguru pydantic pandas numpy statsmodels scikit-learn

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Or add to .bashrc/.zshrc permanently
echo 'export PYTHONPATH="${PYTHONPATH}:/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/src"' >> ~/.bashrc
```

## 2. Configuration (1 minute)

```bash
# Copy environment template
cp .env.example .env

# Edit with your API keys
nano .env
# Or
vim .env
```

Required API keys:
- FRED_API_KEY (get from https://fred.stlouisfed.org/docs/api/api_key.html)
- NEWS_API_KEY (get from https://newsapi.org/register)
- ALPHAVANTAGE_API_KEY (get from https://www.alphavantage.co/support/#api-key)

Optional (for email):
- GMAIL_USER
- GMAIL_APP_PASSWORD

## 3. Test Each Service (1 minute each)

### Service 1: Forecaster 7D
```bash
# Show configuration
python -m services.forecaster_7d.cli info

# Validate (test without full report)
python -m services.forecaster_7d.cli validate

# Full run (skip email)
python -m services.forecaster_7d.cli run --skip-email
```

### Service 2: Forecaster 12M
```bash
# Show configuration
python -m services.forecaster_12m.cli info

# Validate (test without full report)
python -m services.forecaster_12m.cli validate

# Full run (skip email)
python -m services.forecaster_12m.cli run --skip-email
```

### Service 3: Importer Report
```bash
# Show configuration
python -m services.importer_report.cli info

# Preview sections
python -m services.importer_report.cli preview

# Full run (skip email)
python -m services.importer_report.cli run --skip-email
```

## 4. Common Issues & Solutions

### Problem: ModuleNotFoundError
```bash
# Solution: Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Problem: Missing pydantic/typer/etc
```bash
# Solution: Install dependencies
pip install -r requirements.txt
# Or individually
pip install typer rich loguru pydantic
```

### Problem: API Key errors
```bash
# Solution: Check .env file
cat .env | grep API_KEY

# Verify keys are loaded
python -m services.forecaster_7d.cli info
# Look for "✓ Configured" next to each API
```

### Problem: Permission errors on directories
```bash
# Solution: Create and set permissions
mkdir -p ./reports ./logs ./charts ./data
chmod 755 ./reports ./logs ./charts ./data
```

## 5. Production Deployment (TODO)

```bash
# Docker build (once Docker files are created)
docker build -t forecaster-7d -f services/forecaster_7d/Dockerfile .
docker build -t forecaster-12m -f services/forecaster_12m/Dockerfile .
docker build -t importer-report -f services/importer_report/Dockerfile .

# Run containers
docker run -v $(pwd)/reports:/app/reports forecaster-7d
```

## 6. Scheduling (Cron)

```bash
# Edit crontab
crontab -e

# Daily 7-day forecast at 8:00 AM
0 8 * * * cd /path/to/forex-forecast-system && export PYTHONPATH="$PYTHONPATH:$(pwd)/src" && python -m services.forecaster_7d.cli run >> /var/log/forecaster_7d.log 2>&1

# Monthly 12m forecast (1st of month at 9:00 AM)
0 9 1 * * cd /path/to/forex-forecast-system && export PYTHONPATH="$PYTHONPATH:$(pwd)/src" && python -m services.forecaster_12m.cli run >> /var/log/forecaster_12m.log 2>&1

# Monthly importer report (1st of month at 10:00 AM)
0 10 1 * * cd /path/to/forex-forecast-system && export PYTHONPATH="$PYTHONPATH:$(pwd)/src" && python -m services.importer_report.cli run >> /var/log/importer_report.log 2>&1
```

## 7. Next Steps

1. Complete forex_core.reporting module (ChartGenerator, ReportBuilder)
2. Complete forex_core.notifications module (EmailSender)
3. Add pytest test suite
4. Create Docker deployment
5. Set up CI/CD pipeline

## Files Location Reference

```
/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/
├── src/
│   ├── forex_core/           # Core library (data, forecasting, config)
│   └── services/             # Service wrappers
│       ├── forecaster_7d/    # 7-day forecast service
│       ├── forecaster_12m/   # 12-month forecast service
│       └── importer_report/  # Comprehensive report service
├── .env                      # Environment variables (create from .env.example)
├── reports/                  # Generated PDF reports (created automatically)
├── logs/                     # Log files (created automatically)
├── charts/                   # Chart images (created automatically)
└── data/                     # Data storage (created automatically)
```

## Help Commands

```bash
# General help
python -m services.forecaster_7d.cli --help
python -m services.forecaster_12m.cli --help
python -m services.importer_report.cli --help

# Command-specific help
python -m services.forecaster_7d.cli run --help
python -m services.forecaster_7d.cli validate --help
```

---

All services are ready for testing! 🚀

For detailed documentation, see:
- `/src/services/README.md` - Service architecture and design
- `/CLI_USAGE_GUIDE.md` - Comprehensive CLI reference
- `/SERVICE_IMPLEMENTATION_SUMMARY.md` - Implementation details
