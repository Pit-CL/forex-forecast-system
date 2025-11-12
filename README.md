# Forex Forecast System - USD/CLP Projections

**Professional forecasting system for USD/CLP exchange rate using statistical models and economic indicators.**

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 📊 Overview

This system provides automated USD/CLP exchange rate forecasts using an ensemble of statistical models:

- **ARIMA + GARCH**: Time series modeling with volatility clustering
- **VAR**: Vector Autoregression for multivariate forecasting
- **Random Forest**: Machine learning ensemble member
- **Inverse RMSE Weighting**: Optimal model combination

**Key Features:**
- ✅ 7-day daily forecasts
- ✅ 12-month projections
- ✅ Comprehensive importer environment reports
- ✅ Professional PDF generation with charts
- ✅ Automated email delivery
- ✅ Docker deployment ready

## 🏗️ Architecture

```
forex-forecast-system/
├── src/
│   ├── forex_core/          # Shared core library (95% code deduplication)
│   │   ├── config/          # Configuration management
│   │   ├── data/            # 11 data providers (BCCh, Fed, Yahoo, etc.)
│   │   ├── forecasting/     # Statistical models (ARIMA, VAR, RF)
│   │   ├── reporting/       # PDF generation and charting
│   │   └── notifications/   # Email delivery
│   └── services/
│       ├── forecaster_7d/   # 7-day forecast service
│       ├── forecaster_12m/  # 12-month forecast service
│       └── importer_report/ # Strategic import environment report
├── tests/                   # Comprehensive test suite (80%+ coverage target)
├── deployment/              # Docker and infrastructure
└── docs/                    # Documentation and migration guides
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- System dependencies for PDF generation:
  - **macOS**: `brew install cairo pango gdk-pixbuf libffi`
  - **Ubuntu/Debian**: `sudo apt-get install libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev`

### Installation

```bash
# 1. Clone repository
git clone <repository-url>
cd forex-forecast-system

# 2. Setup environment
make setup

# 3. Configure credentials
cp .env.example .env
# Edit .env with your API keys and email credentials

# 4. Install dependencies
make install
```

### Run Your First Forecast

```bash
# Run 7-day forecast
make run-7d

# Run 12-month forecast
make run-12m

# Run importer report
make run-importer
```

## 📖 Usage

### Command Line Interface

Each service provides a Typer-based CLI:

```bash
# 7-day forecast service
python -m services.forecaster_7d.cli run --skip-email
python -m services.forecaster_7d.cli validate
python -m services.forecaster_7d.cli backtest --days 30

# 12-month forecast service
python -m services.forecaster_12m.cli run --output-dir ./custom-output
python -m services.forecaster_12m.cli info

# Importer report service
python -m services.importer_report.cli run
python -m services.importer_report.cli preview
```

### Configuration

Configure via `.env` file or environment variables:

```bash
# Required: API Keys
FRED_API_KEY=your_fred_api_key
NEWS_API_KEY=your_newsapi_key

# Required: Email (for report delivery)
GMAIL_USER=your.email@gmail.com
GMAIL_APP_PASSWORD=your_app_specific_password
EMAIL_RECIPIENTS=recipient1@example.com,recipient2@example.com

# Optional: Directories
DATA_DIR=./data
OUTPUT_DIR=./output
```

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific test categories
make test-unit          # Fast unit tests
make test-integration   # Integration tests (may use APIs)
make test-e2e          # End-to-end tests
make test-pdf          # PDF generation tests (CRITICAL)

# Generate coverage report
make test-coverage
```

**Coverage Target**: 80%+ for core modules

## 🐳 Docker Deployment

```bash
# Build images
make docker-build

# Start all services
make docker-up

# View logs
make docker-logs

# Stop services
make docker-down
```

Services run on schedules:
- **7d forecaster**: Daily at 08:00 Santiago time
- **12m forecaster**: Monthly on 1st at 09:00
- **Importer report**: Monthly on 5th at 10:00

## 📊 Data Sources

| Source | Provider | Data | Update Frequency |
|--------|----------|------|------------------|
| Banco Central de Chile | mindicador.cl | USD/CLP, copper, TPM, IPC | Daily |
| Federal Reserve | FRED API | Fed funds rate, DXY, yields | Daily |
| Yahoo Finance | yfinance | Market data | Real-time |
| XE.com | Web scraping | FX rates | Real-time |
| NewsAPI | newsapi.org | Financial news | Real-time |
| Federal Reserve | Fed dot plot | Rate projections | Quarterly |

## 🔧 Development

```bash
# Install development dependencies
make install-dev

# Code formatting
make format

# Linting
make lint

# Run all validation checks
make validate
```

## 📁 Project Structure

```
src/forex_core/
├── config/              # Pydantic Settings configuration
│   ├── base.py
│   └── constants.py
├── data/
│   ├── providers/       # 11 unified data providers
│   ├── warehouse.py     # Data storage and retrieval
│   └── models.py        # Pydantic data models
├── forecasting/
│   ├── arima.py         # ARIMA + GARCH implementation
│   ├── var.py           # Vector Autoregression
│   ├── random_forest.py # RF ensemble member
│   ├── ensemble.py      # Model combination
│   └── engine.py        # Unified forecasting engine
├── reporting/
│   ├── charting.py      # Matplotlib chart generation
│   ├── builder.py       # PDF report assembly
│   └── templates/       # Jinja2 HTML templates
└── notifications/
    └── email.py         # SMTP email delivery
```

## 🎯 Migration from Legacy System

This project represents a complete migration from a duplicated codebase:

**Before:**
- 95% code duplication between 7d and 12m forecasters
- 0% test coverage
- Scattered configuration
- Manual deployment

**After:**
- Single shared core library (`forex_core`)
- 80%+ test coverage target
- Unified configuration (Pydantic Settings)
- Docker-first deployment
- Professional CI/CD

See `docs/migration/` for detailed migration documentation.

## 📝 Documentation

- **[Architecture Decisions](docs/migration/ARCHITECTURE_DECISIONS.md)**: 7 ADRs documenting key design choices
- **[PDF Reporting Guide](docs/migration/PDF_REPORTING_MIGRATION.md)**: Complete technical guide (13,000+ words)
- **[Migration Checklist](docs/migration/MIGRATION_CHECKLIST.md)**: 200+ task tracking
- **[Session Log](docs/migration/SESSION_LOG.md)**: Chronological migration log

## 🛡️ Security

- ✅ Secrets protected by comprehensive `.gitignore` (committed FIRST)
- ✅ Environment variables for all credentials
- ✅ Gmail app-specific passwords (not account passwords)
- ✅ No hardcoded API keys
- ✅ Docker secrets management

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and add tests
4. Run validation: `make validate`
5. Commit with descriptive message
6. Push and create pull request

## 📧 Support

For issues or questions:
- **Issues**: Open an issue on GitHub
- **Email**: Contact repository maintainer
- **Documentation**: Check `docs/` directory

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Data Providers**: Banco Central de Chile, Federal Reserve, Yahoo Finance
- **Statistical Methods**: Hyndman & Athanasopoulos (Forecasting Principles)
- **PDF Generation**: WeasyPrint team
- **Python Ecosystem**: NumPy, pandas, scikit-learn, statsmodels

---

**Built with ❤️ for professional USD/CLP forecasting**

**Generated**: 2025-11-12
**Python**: 3.11+
**Deployment**: Docker-first
