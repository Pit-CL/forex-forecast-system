# Changelog

All notable changes to the USD/CLP Forex Forecasting System are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.3.0] - 2025-11-13

### Added
- Production deployment infrastructure on Vultr VPS
  - `Dockerfile.7d.prod` - Production Docker image with cron scheduler
  - `docker-compose.prod.yml` - Production compose configuration
  - `cron/7d/crontab` - Cron schedule for 8:00 AM daily execution
  - `cron/7d/entrypoint.sh` - Container entrypoint script
  - `/etc/systemd/system/usdclp-forecaster.service` - Systemd service unit
  - `PRODUCTION_DEPLOYMENT.md` - 500+ line comprehensive deployment guide
- Auto-recovery mechanism: Container restarts automatically on crash (8-second recovery)
- Systemd integration: Forecaster survives server reboots automatically
- Comprehensive session documentation: `docs/sessions/2025-11-13-1100-correlation-matrix-bug-fix-production-deployment.md`

### Fixed
- **Critical Bug:** Correlation matrix heatmap displaying empty values
  - Root cause: Timezone mismatch between data sources (Chile timezone vs UTC)
  - Solution: Implemented date normalization to convert all series to date-only format
  - Files: `src/forex_core/reporting/charting.py` (lines 468-530)
  - Files: `src/forex_core/reporting/chart_interpretations.py` (lines 313-357)
  - Result: 1,175 common dates found across all 5 series
  - Correlation matrix now displays with actual statistical values

### Improved
- Production scheduling: Cron-based daily execution at 8:00 AM Chile time
- Email management: Eliminated infinite restart loops causing email spam
- System reliability: Zero manual intervention required for daily operations
- Deployment documentation: Complete guide for setup, monitoring, and troubleshooting

### Changed
- Docker restart policy: Now serves as crash recovery, not execution trigger
- Error handling: Added minimum observation check (5 rows) for correlation calculation
- Logging: Added informative warnings when insufficient data for analysis

---

## [2.2.0] - 2025-11-12

### Added
- Chart explanations paired directly below chart images in PDF reports
- Professional CSS styling with `page-break-inside: avoid` for layout preservation
- Dynamic statistical insights in chart explanations
  - Technical Analysis: RSI and MACD values from latest data
  - Macro Drivers: TPM rate and risk regime status
  - Risk Regime: Current market regime classification
- Structured chart blocks with title + image + interpretation layout

### Fixed
- Confidence interval colors rendering correctly in forecast charts
  - Orange (#FF8C00) for 80% confidence interval
  - Violet (#8B00FF) for 95% confidence interval

### Improved
- Chart readability: Date labels no longer overlapping (45° rotation, 6-8 ticks)
- Professional presentation: Academic source attribution on all charts
- Methodology section: Expanded from 1 paragraph to 2-3 pages of justification

---

## [2.1.0] - 2025-11-12

### Added
- Professional chart formatting across all 6 visualizations
- Comprehensive methodology section (186 lines of detailed explanation)
- Chart explanation sections with didactic content (80 lines)
- Academic source attribution for all data

### Fixed
- Date label overlapping issue in 6 charts (9 axes affected)
  - Implemented 45° rotation for readability
  - Reduced number of date ticks to prevent crowding
  - Format changed to "15-Nov" for clarity

### Changed
- Methodology section: Now includes detailed justification for model selection
- Source attribution: All charts now display "Fuente: Elaboracion propia con datos de [sources]"

---

## [2.0.0] - 2025-11-12

### Added
- Institutional-grade PDF reports (8-12 pages, 6 professional charts)
- 870+ lines of professional reporting code
- Integration of all existing analysis modules into PDF output
- Production deployment to Vultr VPS
- Automated cron execution configuration
- Comprehensive deployment documentation

### Charts Added
1. Historical + Forecast (30d historical + 7d forecast)
2. Confidence Bands (fan chart with 80% and 95% intervals)
3. Technical Indicators Panel (RSI, MACD, Bollinger Bands)
4. Correlation Matrix (5-series heatmap)
5. Macro Drivers Dashboard (DXY, VIX, EEM, TPM 5-day changes)
6. Risk Regime Visualization (4-panel assessment)

### Sections Added
1. Executive Summary
2. Forecast Table (7 days with confidence intervals)
3. Technical Analysis
4. Risk Regime Assessment
5. Fundamental Factors
6. Interpretation
7. Key Drivers
8. Trading Recommendations
9. Risk Factors
10. Methodology
11. Conclusion + Disclaimer

---

## [1.0.0] - 2025-11-11

### Added
- Initial production release
- Core forecasting system with 3 models:
  - ARIMA + GARCH (time series with volatility)
  - VAR (multivariate relationships)
  - Random Forest (machine learning)
  - Ensemble (weighted combination)
- Data collection from multiple sources:
  - USD/CLP (FRED, Yahoo, Xe.com)
  - Copper prices (Yahoo Finance)
  - DXY, VIX, EEM indices (Yahoo Finance)
  - Chile indicators: TPM, IPC (Mindicador.cl)
  - US indicators: Fed Funds Rate (FRED)
- Basic technical analysis (RSI, MACD, Bollinger Bands, moving averages)
- Fundamental analysis (correlation, macro indicators)
- Risk regime classification system
- Docker configuration and deployment structure
- Test suite with 32+ passing tests (31% coverage)

### Features
- 7-day USD/CLP forecast with confidence intervals
- Daily automated execution via cron
- Email notifications with PDF attachment
- Comprehensive logging and error handling
- Data caching (24-hour TTL)
- Professional system architecture

---

## [0.1.0] - Pre-Migration

### Status
- Prototype in separate repositories
- Duplicated code across projects
- No comprehensive tests
- Basic functionality only
- Not production-ready

### Migration Completed
- Code consolidated into single repository
- Professional project structure established
- Shared core library created (`forex_core`)
- Test suite implemented
- Production deployment configured

---

## Version Numbering

- **Major (X.0.0):** Significant architectural changes or new major features
- **Minor (0.Y.0):** New features that don't break backward compatibility
- **Patch (0.0.Z):** Bug fixes and improvements

---

## How to Use This Changelog

- **For Users:** Check "Added" and "Fixed" sections for latest improvements
- **For Developers:** Review all sections for context on architectural decisions
- **For Deployments:** Cross-reference version numbers with deployment guides

---

## Previous Session Documentation

For detailed information about specific sessions and their accomplishments:

- **2025-11-13:** `docs/sessions/2025-11-13-1100-correlation-matrix-bug-fix-production-deployment.md`
- **2025-11-12:** `docs/sessions/SESSION_2025-11-12_VULTR_SYNC_CHART_EXPLANATIONS.md`
- **2025-11-12:** `docs/sessions/SESSION_2025-11-12_INSTITUTIONAL_UPGRADE.md`
- And more in `docs/sessions/`

---

**Last Updated:** 2025-11-13
**Maintained By:** Development Team
**Next Review:** After next major feature or fix
