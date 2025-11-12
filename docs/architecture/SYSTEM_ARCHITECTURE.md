# USD/CLP Forex Forecasting System - Architecture Documentation

**Version:** 1.0.0
**Last Updated:** 2025-11-12
**Status:** Production

---

## Table of Contents

1. [System Overview](#system-overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Component Diagram](#component-diagram)
4. [Data Flow](#data-flow)
5. [Module Responsibilities](#module-responsibilities)
6. [Technology Stack](#technology-stack)
7. [Deployment Architecture](#deployment-architecture)
8. [Integration Points](#integration-points)
9. [Security Architecture](#security-architecture)
10. [Scalability and Performance](#scalability-and-performance)

---

## System Overview

### Purpose
The USD/CLP Forex Forecasting System is an automated financial analytics platform that generates daily 7-day USD/CLP exchange rate forecasts using ensemble statistical models, combining technical analysis, fundamental analysis, and macro regime assessment.

### Key Capabilities
- **Automated Data Collection:** Fetches data from 6+ external sources (FRED, Yahoo Finance, web scraping)
- **Multi-Model Forecasting:** Ensemble of ARIMA+GARCH, VAR, and Random Forest models
- **Comprehensive Analysis:** Technical indicators, fundamental factors, macro risk regime
- **Institutional Reporting:** Professional PDF reports with 6+ charts and 11 analysis sections
- **Production Automation:** Scheduled daily execution via cron, automated cleanup

### Design Principles
1. **Separation of Concerns:** Clear boundaries between data, analysis, forecasting, and reporting
2. **Modularity:** Reusable core library (`forex_core`) shared across services
3. **Type Safety:** Extensive use of Pydantic models and type hints
4. **Testability:** Pure functions, dependency injection, comprehensive test coverage
5. **Observability:** Structured logging, error handling, execution tracking
6. **Configuration Management:** Environment-based settings with validation

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     External Data Sources                       │
├─────────────────────────────────────────────────────────────────┤
│  FRED  │  Yahoo Finance  │  Xe.com  │  Mindicador.cl  │  News  │
└────┬──────────┬──────────────┬───────────────┬─────────────┬────┘
     │          │              │               │             │
     └──────────┴──────────────┴───────────────┴─────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Data Layer      │
                    │  (Providers)      │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │   Core Library    │
                    │  (forex_core)     │
                    ├───────────────────┤
                    │ • Data Models     │
                    │ • Configuration   │
                    │ • Analysis        │
                    │ • Forecasting     │
                    │ • Reporting       │
                    │ • Notifications   │
                    └─────────┬─────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
    ┌───────▼───────┐ ┌──────▼──────┐ ┌───────▼────────┐
    │  Forecaster   │ │ Forecaster  │ │   Importer     │
    │   7-Day       │ │  12-Month   │ │    Report      │
    │   Service     │ │   Service   │ │    Service     │
    └───────┬───────┘ └──────┬──────┘ └───────┬────────┘
            │                │                │
    ┌───────▼────────────────▼────────────────▼────────┐
    │            Output Layer                          │
    ├──────────────────────────────────────────────────┤
    │  PDF Reports  │  Email Notifications  │  Logs   │
    └──────────────────────────────────────────────────┘
```

### Architecture Layers

1. **Data Layer:** External API clients, web scrapers, data providers
2. **Core Layer:** Shared business logic, models, utilities
3. **Service Layer:** Independent microservices for different forecasting horizons
4. **Output Layer:** Report generation, notification, logging

---

## Component Diagram

### Core Library (`forex_core`)

```
forex_core/
├── analysis/
│   ├── technical.py        # Technical indicators (RSI, MACD, Bollinger)
│   ├── fundamental.py      # Fundamental factors (TPM, inflation, copper)
│   └── macro.py            # Macro regime (risk-on/risk-off)
│
├── config/
│   └── base.py             # Pydantic Settings (environment config)
│
├── data/
│   ├── models.py           # Data models (DataBundle, TimeSeriesData)
│   ├── providers/
│   │   ├── base.py         # Abstract base provider
│   │   ├── fred.py         # FRED API client
│   │   ├── yahoo.py        # Yahoo Finance client
│   │   ├── xe.py           # Xe.com scraper
│   │   ├── mindicador.py   # Mindicador.cl API client
│   │   └── macro_events.py # Economic calendar
│   └── registry.py         # Data source registry
│
├── forecasting/
│   ├── models.py           # ForecastResult, ForecastPoint models
│   ├── arima_garch.py      # ARIMA + GARCH model
│   ├── var_model.py        # Vector Autoregression model
│   ├── random_forest.py    # Random Forest model
│   └── ensemble.py         # Ensemble combiner
│
├── reporting/
│   ├── builder.py          # PDF report builder (11 sections)
│   ├── charting.py         # Chart generator (6+ charts)
│   └── templates/
│       └── report.html.j2  # HTML template with CSS
│
├── notifications/
│   └── email_sender.py     # Gmail SMTP email sender
│
└── utils/
    ├── logging.py          # Structured logging setup
    └── helpers.py          # Utility functions
```

### Services

```
services/
├── forecaster_7d/
│   ├── cli.py              # Typer CLI interface
│   ├── pipeline.py         # Orchestration pipeline
│   └── __main__.py         # Entry point
│
├── forecaster_12m/
│   ├── cli.py              # 12-month forecast CLI
│   └── pipeline.py         # 12-month pipeline
│
└── importer_report/
    ├── cli.py              # Importer-specific report CLI
    └── pipeline.py         # Importer pipeline
```

---

## Data Flow

### 7-Day Forecast Pipeline

```
1. INITIALIZATION
   ├─ Load Settings (from .env)
   ├─ Setup Logging
   └─ Initialize Components

2. DATA COLLECTION
   ├─ Fetch USD/CLP spot (Xe.com)
   ├─ Fetch USD/CLP historical (FRED, Yahoo)
   ├─ Fetch Copper prices (Yahoo)
   ├─ Fetch DXY Index (Yahoo)
   ├─ Fetch VIX, EEM (Yahoo)
   ├─ Fetch TPM, IPC (Mindicador.cl)
   ├─ Fetch Fed Funds Rate (FRED)
   └─ Assemble DataBundle

3. ANALYSIS
   ├─ Compute Technical Indicators
   │  ├─ RSI (14)
   │  ├─ MACD
   │  ├─ Bollinger Bands
   │  ├─ Moving Averages (5, 20, 50)
   │  ├─ Support/Resistance
   │  └─ Historical Volatility
   │
   ├─ Compute Fundamental Factors
   │  ├─ TPM vs Fed Funds differential
   │  ├─ Copper correlation
   │  ├─ Inflation trends
   │  └─ Trade balance impact
   │
   └─ Compute Risk Regime
      ├─ DXY 5-day change
      ├─ VIX 5-day change
      ├─ EEM 5-day change
      └─ Regime classification (Risk-on/Risk-off/Neutral)

4. FORECASTING
   ├─ Model 1: ARIMA + GARCH
   │  ├─ Fit ARIMA to log returns
   │  ├─ Fit GARCH to volatility
   │  ├─ Generate 7-step forecast
   │  └─ Calculate confidence intervals
   │
   ├─ Model 2: VAR (Vector Autoregression)
   │  ├─ Construct multivariate series (USD/CLP, Copper, DXY)
   │  ├─ Fit VAR model
   │  ├─ Generate forecast
   │  └─ Calculate CIs
   │
   ├─ Model 3: Random Forest
   │  ├─ Engineer features (lags, MA, volatility)
   │  ├─ Train RF regressor
   │  ├─ Generate forecast
   │  └─ Bootstrap CIs
   │
   └─ Ensemble Combination
      ├─ Compute weights (inverse RMSE)
      ├─ Weighted average of forecasts
      └─ Aggregate confidence intervals

5. VISUALIZATION
   ├─ Chart 1: Historical + Forecast
   ├─ Chart 2: Confidence Bands (fan chart)
   ├─ Chart 3: Technical Indicators Panel
   ├─ Chart 4: Correlation Matrix
   ├─ Chart 5: Macro Drivers Dashboard
   └─ Chart 6: Risk Regime Visualization

6. REPORT GENERATION
   ├─ Section 1: Executive Summary
   ├─ Section 2: Forecast Table
   ├─ Section 3: Technical Analysis
   ├─ Section 4: Risk Regime Assessment
   ├─ Section 5: Fundamental Factors
   ├─ Section 6: Interpretation
   ├─ Section 7: Drivers
   ├─ Section 8: Trading Recommendations
   ├─ Section 9: Risk Factors
   ├─ Section 10: Methodology
   ├─ Section 11: Conclusion + Disclaimer
   ├─ Render HTML from Jinja2 template
   └─ Generate PDF via WeasyPrint

7. OUTPUT
   ├─ Save PDF to reports/
   ├─ Log execution summary
   └─ (Optional) Send email notification
```

### Data Flow Diagram (Detailed)

```
┌──────────────┐
│  External    │
│  Data APIs   │
└──────┬───────┘
       │
       │ HTTP Requests
       ▼
┌──────────────┐
│   Provider   │──────┐
│   Clients    │      │ Cache Hit
└──────┬───────┘      ▼
       │         ┌──────────┐
       │ Raw     │  Local   │
       │ Data    │  Cache   │
       ▼         └──────────┘
┌──────────────┐
│  Data Bundle │
│  Assembly    │
└──────┬───────┘
       │
       │ DataBundle
       │
    ┌──┴──┐
    │     │
    ▼     ▼
┌─────┐ ┌─────────┐
│Anal-│ │Forecast-│
│ysis │ │  ing    │
└──┬──┘ └────┬────┘
   │         │
   │    ForecastResult
   │         │
   └────┬────┘
        │
   AnalysisArtifacts
        │
        ▼
   ┌─────────┐
   │ Chart   │
   │Generator│
   └────┬────┘
        │
   Chart Paths
        │
        ▼
   ┌─────────┐
   │ Report  │
   │ Builder │
   └────┬────┘
        │
    PDF File
        │
        ▼
   ┌─────────┐
   │ Storage │
   │ & Email │
   └─────────┘
```

---

## Module Responsibilities

### Data Layer

#### `forex_core.data.providers`

**Responsibility:** Fetch and cache data from external sources

**Key Classes:**
- `BaseDataProvider`: Abstract base with caching, error handling
- `FREDClient`: Federal Reserve Economic Data API
- `YahooFinanceClient`: Stock and commodity data
- `XeClient`: Real-time USD/CLP spot rate
- `MindicadorClient`: Chilean economic indicators
- `FederalReserveClient`: Fed Funds Rate scraper

**Interface:**
```python
class BaseDataProvider:
    def fetch(self, series_id: str, start_date: date, end_date: date) -> pd.Series
    def fetch_cached(self, key: str, ttl_hours: int) -> Optional[pd.Series]
```

#### `forex_core.data.models`

**Responsibility:** Define data structures

**Key Models:**
- `TimeSeriesData`: Pydantic model for time series with metadata
- `DataBundle`: Container for all data required for forecasting
- `Indicator`: Single indicator value with source and timestamp

**Example:**
```python
@dataclass
class DataBundle:
    usdclp_series: pd.Series
    copper_series: pd.Series
    dxy_series: pd.Series
    tpm_series: pd.Series
    inflation_series: pd.Series
    vix_series: pd.Series
    eem_series: pd.Series
    indicators: Dict[str, Indicator]
    sources: SourceRegistry
    timestamp: datetime
```

---

### Analysis Layer

#### `forex_core.analysis.technical`

**Responsibility:** Technical analysis indicators

**Functions:**
- `compute_technicals(series: pd.Series) -> Dict`: All-in-one technical analysis
- `calculate_rsi(series: pd.Series, period: int) -> pd.Series`
- `calculate_macd(series: pd.Series) -> Dict[str, pd.Series]`
- `calculate_bollinger_bands(series: pd.Series, window: int, num_std: float)`
- `find_support_resistance(series: pd.Series) -> Tuple[float, float]`

**Output:**
```python
{
    'rsi_14': 65.3,
    'macd': 2.5,
    'macd_signal': 2.1,
    'macd_hist': 0.4,
    'bb_upper': 950,
    'bb_lower': 930,
    'ma_5': 942,
    'ma_20': 938,
    'ma_50': 935,
    'support': 925,
    'resistance': 955,
    'hist_vol_30': 0.15,  # annualized
    'frame': pd.DataFrame  # full history with indicators
}
```

#### `forex_core.analysis.fundamental`

**Responsibility:** Fundamental factor extraction and organization

**Functions:**
- `extract_quant_factors(bundle: DataBundle) -> QuantFactors`: Extract raw factors
- `build_quant_factors(factors: QuantFactors) -> pd.DataFrame`: Format as table
- `interpret_fundamental_bias(factors: QuantFactors) -> str`: Narrative interpretation

**Output:**
```python
QuantFactors(
    tpm_current=7.25,
    tpm_trend='rising',
    fed_funds_rate=5.50,
    rate_differential=1.75,
    copper_price=4.25,
    copper_trend='stable',
    dxy_level=103.5,
    inflation_yoy=4.2,
    gdp_growth=2.5
)
```

#### `forex_core.analysis.macro`

**Responsibility:** Macro risk regime classification

**Functions:**
- `compute_risk_gauge(bundle: DataBundle) -> RiskGauge`: Classify risk regime

**Logic:**
```python
# Score calculation
score = 0
if dxy_change_5d < -0.5: score += 1  # Weak USD = risk-on
if vix_change_5d < -5: score += 1    # Lower vol = risk-on
if eem_change_5d > 1: score += 1     # EM strength = risk-on

# Classification
if score >= 2: regime = "Risk-on"
elif score <= -2: regime = "Risk-off"
else: regime = "Neutral"
```

**Output:**
```python
RiskGauge(
    regime='Risk-on',
    dxy_change=-1.2,  # 5-day %
    vix_change=-8.5,
    eem_change=2.3,
    score=3
)
```

---

### Forecasting Layer

#### `forex_core.forecasting.arima_garch`

**Responsibility:** ARIMA + GARCH model for time series forecasting

**Algorithm:**
```
1. Transform to log returns: r_t = log(P_t / P_{t-1})
2. Fit ARIMA(p,d,q) to returns
   - Auto-select (p,d,q) using AIC via pmdarima
3. Extract residuals: ε_t = r_t - r̂_t
4. Fit GARCH(1,1) to residuals for volatility
   σ²_t = ω + α·ε²_{t-1} + β·σ²_{t-1}
5. Forecast returns: r̂_{t+h} = ARIMA forecast
6. Forecast volatility: σ̂_{t+h} = GARCH forecast
7. Transform back to price levels
8. Compute confidence intervals using σ̂_{t+h}
```

**Implementation:**
```python
def run_arima_garch(
    series: pd.Series,
    steps: int = 7,
    mc_simulations: int = 1000
) -> ForecastResult:
    # Fit ARIMA
    model_fit = auto_arima(log_returns, ...)

    # Fit GARCH on residuals
    garch_model = arch_model(residuals, vol='Garch', p=1, q=1)
    garch_fit = garch_model.fit()

    # Monte Carlo simulation for confidence intervals
    simulations = []
    for _ in range(mc_simulations):
        sim = model_fit.simulate(steps, ...)
        simulations.append(sim)

    # Aggregate percentiles
    mean_forecast = np.mean(simulations, axis=0)
    ci_80 = np.percentile(simulations, [10, 90], axis=0)
    ci_95 = np.percentile(simulations, [2.5, 97.5], axis=0)

    return ForecastResult(...)
```

#### `forex_core.forecasting.var_model`

**Responsibility:** Vector Autoregression for multivariate forecasting

**Algorithm:**
```
1. Construct multivariate series:
   Y_t = [USD/CLP_t, Copper_t, DXY_t]
2. Difference to stationarity
3. Fit VAR model:
   Y_t = c + Φ₁·Y_{t-1} + ... + Φ_p·Y_{t-p} + ε_t
4. Select lag order p using AIC/BIC
5. Forecast: Ŷ_{t+h} = c + Σ Φᵢ·Ŷ_{t+h-i}
6. Compute forecast error covariance
7. Extract USD/CLP component
```

#### `forex_core.forecasting.random_forest`

**Responsibility:** Machine learning baseline

**Features Engineered:**
```python
features = [
    'usdclp_lag_1', 'usdclp_lag_2', ..., 'usdclp_lag_7',
    'copper_lag_1', 'dxy_lag_1',
    'ma_5', 'ma_20',
    'rsi_14',
    'volatility_30d',
    'day_of_week',
    'month'
]
```

**Implementation:**
```python
from sklearn.ensemble import RandomForestRegressor

def train_random_forest(bundle: DataBundle) -> RandomForestRegressor:
    X, y = engineer_features(bundle)
    rf = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
    rf.fit(X, y)
    return rf

def forecast_random_forest(model, bundle, steps) -> ForecastResult:
    # Recursive forecasting
    for step in range(steps):
        X_next = create_features(bundle, last_predictions)
        y_pred = model.predict([X_next])
        last_predictions.append(y_pred)

    # Bootstrap for confidence intervals
    ci = bootstrap_ci(model, X, n_boot=1000)

    return ForecastResult(...)
```

#### `forex_core.forecasting.ensemble`

**Responsibility:** Combine multiple model forecasts

**Weighting Strategy:**
```python
def compute_ensemble_weights(
    models: Dict[str, ForecastResult],
    window: int = 30
) -> Dict[str, float]:
    """Inverse RMSE weighting"""
    rmse_scores = {
        name: result.error_metrics['RMSE']
        for name, result in models.items()
    }

    # Inverse weighting
    inv_rmse = {name: 1/rmse for name, rmse in rmse_scores.items()}
    total = sum(inv_rmse.values())
    weights = {name: w/total for name, w in inv_rmse.items()}

    return weights

def ensemble_forecast(
    forecasts: Dict[str, ForecastResult],
    weights: Dict[str, float]
) -> ForecastResult:
    """Weighted average of forecasts"""
    combined_series = []
    for date in forecast_dates:
        weighted_mean = sum(
            weights[name] * forecasts[name].get_point(date).mean
            for name in forecasts.keys()
        )
        combined_series.append(ForecastPoint(date=date, mean=weighted_mean, ...))

    return ForecastResult(series=combined_series, ...)
```

---

### Reporting Layer

#### `forex_core.reporting.charting`

**Responsibility:** Generate professional charts using matplotlib/seaborn

**Charts:**

1. **Historical + Forecast Chart** (`_generate_hist_forecast_chart`)
   - Last 30 days historical
   - 7-day forecast line
   - 80% and 95% confidence bands

2. **Confidence Bands Chart** (`_generate_confidence_bands_chart`)
   - Fan chart style
   - Multiple percentile bands
   - Color-coded uncertainty

3. **Technical Indicators Panel** (`_generate_technical_panel`)
   - 3 subplots: Price+Bollinger, RSI, MACD
   - Overbought/oversold zones
   - Signal lines and histograms

4. **Correlation Matrix** (`_generate_correlation_matrix`)
   - Heatmap of USD/CLP vs DXY, Copper, VIX, EEM
   - Daily return correlations
   - Seaborn styling

5. **Macro Dashboard** (`_generate_macro_dashboard`)
   - 4-panel layout
   - Dual-axis charts for comparisons
   - Last value annotations

6. **Risk Regime Chart** (`_generate_regime_chart`)
   - 4 panels: DXY, VIX, EEM trends
   - Color-coded backgrounds
   - Regime classification overlay

**Styling Standards:**
```python
DPI = 200
FIGSIZE_STANDARD = (12, 6)
FIGSIZE_PANEL = (12, 9)
COLOR_PALETTE = 'Set2'
FONT_SIZE_TITLE = 14
FONT_SIZE_LABEL = 11
```

#### `forex_core.reporting.builder`

**Responsibility:** Assemble PDF report from sections

**Sections:**

1. `_build_executive_summary()`: High-level summary with directional bias
2. `_build_forecast_table()`: Table with dates, forecast, CIs
3. `_build_technical_analysis()`: RSI, MACD, Bollinger interpretation
4. `_build_risk_regime()`: Macro regime classification
5. `_build_fundamental_factors()`: Table of drivers (TPM, copper, etc.)
6. `_build_interpretation()`: Narrative explanation of forecast
7. `_build_drivers()`: Key drivers list
8. `_build_trading_recommendations()`: Entry/exit levels for traders
9. `_build_risk_factors()`: Upside/downside risks
10. `_build_methodology()`: Model description
11. `_build_conclusion()`: Final thoughts + disclaimer

**Workflow:**
```python
def build(
    self,
    bundle: DataBundle,
    forecast: ForecastResult,
    charts: Dict[str, Path],
    artifacts: Dict,
    horizon: str = "7d"
) -> Path:
    # 1. Generate markdown sections
    markdown_body = self._build_markdown_sections(bundle, forecast, artifacts, horizon)

    # 2. Convert markdown to HTML
    html_content = markdown(markdown_body, extensions=['tables', 'fenced_code'])

    # 3. Embed charts as base64
    chart_imgs = [ChartGenerator.image_to_base64(p) for p in charts.values()]

    # 4. Render Jinja2 template
    html_body = self.template.render(
        title=title,
        content=html_content,
        charts=chart_imgs,
        timestamp=timestamp
    )

    # 5. Generate PDF with WeasyPrint
    pdf_path = self._write_pdf(html_body, filename)

    return pdf_path
```

---

## Technology Stack

### Core Technologies

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Language** | Python | 3.12.3 | Core language |
| **Config** | Pydantic Settings | 2.x | Type-safe configuration |
| **CLI** | Typer | 0.x | Command-line interface |
| **Logging** | Loguru | 0.x | Structured logging |

### Data & Analysis

| Component | Library | Purpose |
|-----------|---------|---------|
| **Data Manipulation** | pandas 2.3.3 | Time series operations |
| **Numerical** | numpy 2.3.4 | Array operations |
| **Statistical** | statsmodels 0.14.5 | ARIMA, VAR models |
| **Auto ARIMA** | pmdarima 2.0.4 | Automatic ARIMA selection |
| **Volatility** | arch 8.0.0 | GARCH models |
| **Machine Learning** | scikit-learn 1.7.2 | Random Forest |

### Visualization

| Component | Library | Purpose |
|-----------|---------|---------|
| **Plotting** | matplotlib 3.10.7 | Chart generation |
| **Statistical Viz** | seaborn 0.13.2 | Heatmaps, styling |
| **PDF Generation** | WeasyPrint 66.0 | HTML to PDF |
| **Templates** | Jinja2 | HTML templating |
| **Markdown** | markdown | Markdown parsing |

### Data Providers

| Component | Library | Purpose |
|-----------|---------|---------|
| **HTTP Client** | httpx | Async API requests |
| **Scraping** | beautifulsoup4 | HTML parsing |
| **Requests** | requests | Synchronous HTTP |

### Testing

| Component | Library | Purpose |
|-----------|---------|---------|
| **Framework** | pytest 9.0.1 | Test runner |
| **Coverage** | pytest-cov 7.0.0 | Code coverage |

### Deployment

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Containerization** | Docker | Isolated environments |
| **Orchestration** | Docker Compose | Multi-service deployment |
| **Scheduling** | cron | Automated execution |
| **Server** | Ubuntu 22.04 | Production OS |
| **Hosting** | Vultr VPS | Cloud infrastructure |

---

## Deployment Architecture

### Production Environment

```
┌───────────────────────────────────────────────────────────┐
│                      Vultr VPS                            │
│                   Ubuntu 22.04 LTS                        │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │   Cron Scheduler                                 │    │
│  │   - Daily 8 AM: 7-day forecast                   │    │
│  │   - Monthly: 12-month forecast (future)          │    │
│  │   - Cleanup: Logs (30d), PDFs (90d)              │    │
│  └────────────┬────────────────────────────────────┘    │
│               │                                           │
│               ▼                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │   Python Virtual Environment                     │    │
│  │   /home/deployer/forex-forecast-system/venv     │    │
│  │   - Python 3.11+                                 │    │
│  │   - All dependencies installed                   │    │
│  └────────────┬────────────────────────────────────┘    │
│               │                                           │
│               ▼                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │   Application Code                               │    │
│  │   /home/deployer/forex-forecast-system          │    │
│  │   ├── src/                                       │    │
│  │   ├── venv/                                      │    │
│  │   ├── data/       (cached data)                  │    │
│  │   ├── reports/    (output PDFs)                  │    │
│  │   ├── logs/       (execution logs)               │    │
│  │   └── .env        (secrets)                      │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
└───────────────────────────────────────────────────────────┘
              │
              │ HTTPS
              ▼
┌───────────────────────────────────────┐
│      External APIs                    │
│  • FRED (fred.stlouisfed.org)        │
│  • Yahoo Finance (finance.yahoo.com)  │
│  • Xe.com                             │
│  • Mindicador.cl                      │
│  • NewsAPI                            │
└───────────────────────────────────────┘
```

### File System Layout

```
/home/deployer/forex-forecast-system/
├── src/
│   ├── forex_core/              # Shared core library (2,547 lines)
│   │   ├── analysis/
│   │   ├── config/
│   │   ├── data/
│   │   ├── forecasting/
│   │   ├── reporting/
│   │   ├── notifications/
│   │   └── utils/
│   └── services/
│       ├── forecaster_7d/       # 7-day service (~400 lines)
│       ├── forecaster_12m/      # 12-month service
│       └── importer_report/     # Importer report service
├── venv/                        # Python virtual environment
│   ├── bin/
│   ├── lib/
│   └── include/
├── data/                        # Data warehouse (cached API responses)
│   └── warehouse/
│       ├── fred_*.json
│       ├── yahoo_*.json
│       └── ...
├── reports/                     # Generated PDFs
│   ├── usdclp_report_7d_20251112_0800.pdf
│   ├── usdclp_report_7d_20251113_0800.pdf
│   └── ...
├── logs/                        # Execution logs
│   ├── cron_7d.log              # Consolidated cron log
│   ├── forecast_7d_20251112_080015.log
│   └── ...
├── tests/                       # Test suite (~800 lines)
├── docs/                        # Documentation
├── run_7d_forecast.sh           # Cron execution script
├── .env                         # Environment variables (secrets)
├── requirements.txt             # Python dependencies
└── docker-compose.yml           # Docker configuration (alternative)
```

### Execution Flow (Cron)

```
08:00:00 - Cron triggers run_7d_forecast.sh
08:00:01 - Script activates virtual environment
08:00:02 - Python loads configuration from .env
08:00:03 - CLI initialized (Typer)
08:00:04 - Pipeline starts
08:00:05 - Data collection begins (parallel requests)
           ├─ FRED API: USD/CLP historical
           ├─ Yahoo Finance: Copper, DXY, VIX, EEM
           ├─ Mindicador: TPM, IPC
           └─ Xe.com: USD/CLP spot
08:00:15 - Data collection complete (10s)
08:00:16 - Analysis phase starts
           ├─ Technical indicators computed
           ├─ Fundamental factors extracted
           └─ Risk regime classified
08:00:18 - Analysis complete (2s)
08:00:19 - Forecasting phase starts
           ├─ ARIMA+GARCH fit
           ├─ VAR fit
           ├─ Random Forest train
           └─ Ensemble combination
08:00:30 - Forecasting complete (11s)
08:00:31 - Chart generation starts (6 charts)
08:00:34 - Charts complete (3s)
08:00:35 - Report building starts
           ├─ Markdown sections generated
           ├─ HTML rendered
           └─ PDF generated (WeasyPrint)
08:00:39 - Report complete (4s)
08:00:40 - PDF saved to reports/
08:00:41 - Logs written
08:00:42 - Execution complete (42 seconds total)
```

---

## Integration Points

### External APIs

#### 1. FRED (Federal Reserve Economic Data)
```
Endpoint: https://api.stlouisfed.org/fred/
Authentication: API Key (URL parameter)
Rate Limit: 120 requests/minute
Data Fetched:
  - DEXCHUS (USD/CLP historical)
  - DFF (Fed Funds Rate)
  - WPU101 (Copper prices - alternative source)
```

#### 2. Yahoo Finance
```
Endpoint: https://query1.finance.yahoo.com/v8/finance/chart/
Authentication: None (public)
Rate Limit: ~2000 requests/hour (unofficial)
Data Fetched:
  - CLP=X (USD/CLP)
  - HG=F (Copper futures)
  - DX-Y.NYB (DXY Index)
  - ^VIX (VIX volatility)
  - EEM (Emerging Markets ETF)
```

#### 3. Xe.com
```
Method: Web scraping (BeautifulSoup)
URL: https://www.xe.com/currencyconverter/convert/?Amount=1&From=USD&To=CLP
Rate Limit: None specified (polite scraping with delays)
Data Fetched:
  - Real-time USD/CLP spot rate
```

#### 4. Mindicador.cl
```
Endpoint: https://mindicador.cl/api/
Authentication: None (public)
Rate Limit: None specified
Data Fetched:
  - dolar (USD/CLP official rate)
  - tpm (Tasa Política Monetaria)
  - ipc (Índice de Precios al Consumidor)
```

#### 5. News API
```
Endpoint: https://newsapi.org/v2/everything
Authentication: API Key (header)
Rate Limit: 100 requests/day (free tier)
Data Fetched:
  - News headlines about Chile, USD, economy
  - Used for optional narrative context
```

### Data Caching Strategy

```python
# Cache location
CACHE_DIR = data/warehouse/

# Cache keys format
{provider}_{series_id}_{start_date}_{end_date}.json

# Cache TTL (Time To Live)
- Historical data: 24 hours
- Real-time data: 5 minutes
- Economic indicators: 6 hours

# Cache invalidation
- Automatic on TTL expiry
- Manual via data/ directory cleanup
- No cache for real-time spot prices
```

---

## Security Architecture

### Secrets Management

```
Environment Variables (.env file):
  - FRED_API_KEY         # Encrypted at rest
  - NEWS_API_KEY         # Encrypted at rest
  - GMAIL_APP_PASSWORD   # Encrypted at rest
  - EMAIL_RECIPIENTS     # Not secret but sensitive

File Permissions:
  .env → 600 (read/write owner only)
  logs/ → 755 (readable by group for monitoring)
  reports/ → 755 (readable by group for access)

Never Logged:
  - API keys (redacted in logs)
  - Email passwords
  - Personal data
```

### Network Security

```
Firewall (ufw):
  - Allow: SSH (22/tcp)
  - Deny: All other inbound

HTTPS Only:
  - All external API calls use HTTPS
  - Certificate validation enabled
  - No HTTP fallback

Rate Limiting:
  - Respects API rate limits
  - Exponential backoff on failures
  - Polite scraping (1-2 second delays)
```

### Input Validation

```python
# All external data validated with Pydantic
class TimeSeriesData(BaseModel):
    series: pd.Series
    source: str
    frequency: str  # Must be 'D', 'W', 'M'
    last_updated: datetime

    @validator('series')
    def validate_series(cls, v):
        if v.empty:
            raise ValueError("Series cannot be empty")
        if v.isnull().sum() > len(v) * 0.3:
            raise ValueError("Too many missing values")
        return v
```

### Error Handling

```python
# No sensitive data in error messages
try:
    data = fetch_fred_data(api_key=settings.fred_api_key)
except requests.HTTPError as e:
    logger.error(f"FRED API request failed: {e.response.status_code}")
    # api_key is NEVER logged
```

---

## Scalability and Performance

### Current Performance

```
Single Execution:
  - Data Collection: ~10 seconds (parallel requests)
  - Analysis: ~2 seconds
  - Forecasting: ~11 seconds (model fitting)
  - Chart Generation: ~3 seconds (6 charts)
  - PDF Generation: ~4 seconds (WeasyPrint)
  - Total: ~30 seconds

Resource Usage:
  - CPU: ~60% of 1 core (peak during model fitting)
  - Memory: ~500 MB (peak with all data loaded)
  - Disk: ~2 MB per execution (PDF + logs)
  - Network: ~5 MB download (API data)

Throughput:
  - 1 forecast per 30 seconds
  - 120 forecasts per hour (theoretical)
  - 2,880 forecasts per day (theoretical)
  - Current: 1 forecast per day (actual)
```

### Scalability Considerations

#### Vertical Scaling (Current Approach)
```
Current Server: 2 vCPU, 4 GB RAM
Can scale to: 8 vCPU, 16 GB RAM

Benefits:
  ✓ Simple deployment
  ✓ No distributed systems complexity
  ✓ Sufficient for daily batch job

Limitations:
  ✗ Single point of failure
  ✗ Manual scaling required
  ✗ Limited to single server capacity
```

#### Horizontal Scaling (Future)
```
Architecture: Kubernetes with CronJobs

Components:
  - API Gateway (Ingress)
  - Forecast Service (Deployment, N replicas)
  - Data Cache (Redis cluster)
  - Report Storage (S3/MinIO)
  - Job Scheduler (Kubernetes CronJob)

Benefits:
  ✓ High availability
  ✓ Auto-scaling
  ✓ Zero-downtime deployments
  ✓ Better resource utilization

Considerations:
  • Overkill for current load (1 job/day)
  • Recommended if: >100 forecasts/day or real-time API
```

### Performance Optimization Opportunities

#### 1. Parallel Chart Generation
```python
# Current: Sequential (3 seconds)
charts = {}
for chart_name, chart_func in chart_generators.items():
    charts[chart_name] = chart_func()

# Optimized: Parallel (1 second)
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(func): name for name, func in chart_generators.items()}
    charts = {name: future.result() for future, name in futures.items()}

# Estimated Speedup: 2-3x (3s → 1s)
```

#### 2. Data Provider Connection Pooling
```python
# Use httpx with connection pooling
import httpx

class BaseDataProvider:
    def __init__(self):
        self.client = httpx.Client(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )

    def fetch(self, url):
        return self.client.get(url)  # Reuses connections

# Estimated Speedup: 1.5x (10s → 7s for data collection)
```

#### 3. Model Pretraining / Warm Start
```python
# Cache fitted model parameters
import joblib

# After fitting
joblib.dump(arima_model, 'cache/arima_params.pkl')

# Next execution (warm start)
try:
    arima_model = joblib.load('cache/arima_params.pkl')
    # Use previous parameters as starting point
except FileNotFoundError:
    # Cold start: fit from scratch

# Estimated Speedup: 1.3x (11s → 8s for forecasting)
```

#### 4. Incremental Data Updates
```python
# Current: Fetch full history every time
series = fetch_data(start='2020-01-01', end='today')

# Optimized: Fetch only new data
last_date = load_cached_last_date()
new_data = fetch_data(start=last_date + 1, end='today')
series = concat_cached_data(new_data)

# Estimated Speedup: 2x (10s → 5s for data collection)
```

### Total Optimization Potential
```
Current Total: 30 seconds
Optimized Total:
  - Data Collection: 10s → 5s (incremental updates)
  - Analysis: 2s → 2s (already fast)
  - Forecasting: 11s → 8s (warm start)
  - Charts: 3s → 1s (parallel generation)
  - PDF: 4s → 4s (already fast)

Optimized Total: ~20 seconds (33% faster)

ROI: Low priority (30s vs 20s negligible for daily batch job)
```

---

## Monitoring and Observability

### Logging Strategy

```python
# Structured logging with Loguru
from loguru import logger

# Log levels
logger.debug("Detailed diagnostic information")
logger.info("General informational messages")
logger.warning("Warning messages (e.g., missing data)")
logger.error("Error messages (e.g., API failure)")
logger.critical("Critical errors (e.g., forecast failure)")

# Log format
"{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"

# Log rotation
logs/
  ├── cron_7d.log             # Consolidated cron log (no rotation)
  ├── forecast_7d_*.log        # Timestamped execution logs (30-day cleanup)
  └── error.log               # Error-only log (manual review)
```

### Metrics Tracked

```
Execution Metrics:
  - Start time, end time, duration
  - Success/failure status
  - Exit code

Data Metrics:
  - Number of data points fetched
  - Data sources used
  - Cache hit rate

Model Metrics:
  - RMSE, MAE, MAPE for each model
  - Ensemble weights
  - Forecast mean, std dev

Output Metrics:
  - PDF file size
  - Number of charts generated
  - Report generation time
```

### Health Checks

```bash
# Automated health check script
#!/bin/bash

# 1. Check if PDF was generated today
TODAY=$(date +%Y%m%d)
if ls reports/usdclp_report_7d_${TODAY}*.pdf 1> /dev/null 2>&1; then
    echo "✓ PDF generated today"
else
    echo "✗ PDF missing for today"
    exit 1
fi

# 2. Check for recent errors
ERROR_COUNT=$(grep -i "error\|exception" logs/cron_7d.log | grep "$(date +%Y-%m-%d)" | wc -l)
if [ $ERROR_COUNT -eq 0 ]; then
    echo "✓ No errors today"
else
    echo "✗ Found $ERROR_COUNT errors today"
    exit 1
fi

# 3. Check disk space
DISK_USAGE=$(df -h /home/deployer/forex-forecast-system | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    echo "✓ Disk usage OK ($DISK_USAGE%)"
else
    echo "✗ Disk usage high ($DISK_USAGE%)"
    exit 1
fi
```

### Future: Observability Stack (Optional)

```
Components:
  - Prometheus: Metrics collection
  - Grafana: Visualization dashboards
  - Loki: Log aggregation
  - Alertmanager: Alert routing (email, Slack)

Metrics Exposed:
  - forecast_execution_duration_seconds
  - forecast_success_total
  - forecast_failure_total
  - model_rmse{model="arima_garch"}
  - pdf_generation_time_seconds
  - api_request_duration_seconds{provider="fred"}

Alerts:
  - No PDF generated in 25 hours → Email
  - Forecast RMSE > 10 CLP → Warning
  - API failure rate > 20% → Critical
```

---

## Disaster Recovery

### Backup Strategy

```
What to Backup:
  1. Configuration (.env file) - CRITICAL
  2. Source code (already in GitHub) - Redundant
  3. Generated PDFs (reports/) - OPTIONAL (can regenerate)
  4. Cached data (data/warehouse/) - OPTIONAL (can re-fetch)
  5. Logs (logs/) - OPTIONAL (for audit trail)

Backup Frequency:
  - .env: Manual backup to secure storage (1Password, etc.)
  - Code: Continuous (GitHub)
  - PDFs: Weekly backup to S3/Cloud Storage (future)
  - Data cache: No backup (regenerable)
  - Logs: No backup (not critical)

Backup Script:
  /home/deployer/backup_forex.sh
  Runs weekly via cron
  Backs up .env, PDFs, important logs
```

### Recovery Procedures

#### Scenario 1: Server Failure (Complete Loss)
```
1. Provision new Vultr VPS (same specs)
2. Run initial server setup (system dependencies)
3. Clone repository from GitHub
4. Restore .env from secure backup
5. Setup virtual environment
6. Configure cron
7. Verify execution
8. (Optional) Restore historical PDFs from backup

Estimated Recovery Time: 1-2 hours
```

#### Scenario 2: Data Corruption
```
1. Clear corrupted cache: rm -rf data/warehouse/*
2. Run manual execution: ./run_7d_forecast.sh
3. Data will re-download automatically
4. Verify PDF generated correctly

Estimated Recovery Time: 5 minutes
```

#### Scenario 3: Code Regression (Bad Deploy)
```
1. SSH to server
2. Git rollback: git reset --hard <previous-commit>
3. Reinstall dependencies: pip install -r requirements.txt --force-reinstall
4. Verify: python -m services.forecaster_7d.cli validate
5. Test: ./run_7d_forecast.sh

Estimated Recovery Time: 10 minutes
```

---

## Future Enhancements

### Planned (Next 3-6 Months)

1. **12-Month Forecaster Service**
   - Longer horizon forecasting
   - Different model configuration (lower frequency)
   - Monthly execution

2. **Importer Report Service**
   - Specialized analysis for importers
   - Forward curve analysis
   - Hedging recommendations

3. **Forecast Accuracy Tracking**
   - Compare forecasts to actual values
   - Generate monthly backtest reports
   - Model performance dashboard

4. **Email Notifications**
   - Automated email delivery on completion
   - Email alerts on failure
   - Customizable recipient lists

### Under Consideration (6-12 Months)

1. **Web Dashboard**
   - Interactive charts (Plotly)
   - Historical forecast visualization
   - Streamlit or Dash interface

2. **REST API**
   - On-demand forecast generation
   - FastAPI backend
   - Authentication and rate limiting

3. **Kubernetes Deployment**
   - Migrate from VM to Kubernetes
   - Auto-scaling
   - Better resource utilization

4. **Real-Time Updates**
   - WebSocket streaming of spot prices
   - Intraday forecast updates
   - Live dashboard

---

**Document Version:** 1.0.0
**Last Updated:** 2025-11-12
**Maintained By:** Development Team
**Status:** Living Document (updated with major changes)
