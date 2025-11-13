# Documentation Index

**USD/CLP Forex Forecasting System - Complete Documentation Guide**

Last Updated: 2025-11-13
Maintained By: Development Team

---

## Quick Navigation

### For Project Managers & Stakeholders
1. **Current Status:** `/PROJECT_STATUS.md` - Executive overview, version, health
2. **Recent Changes:** `/CHANGELOG.md` - What's new in each version
3. **Session Summary:** `/SESSION_SUMMARY_2025-11-13.md` - Latest work session overview

### For Development Team
1. **System Architecture:** `/docs/architecture/SYSTEM_ARCHITECTURE.md` - Technical architecture
2. **API Documentation:** `/docs/CHART_INTERPRETATIONS_API.md` - Chart interpretation interface
3. **Session Documentation:** `/docs/sessions/` - Detailed work logs (see below)

### For DevOps/Infrastructure
1. **Deployment Guide:** `/PRODUCTION_DEPLOYMENT.md` - Complete production setup
2. **Docker Guide:** `/docs/DOCKER.md` - Docker usage and configuration
3. **Vultr Setup:** `/docs/deployment/VULTR_DEPLOYMENT_GUIDE.md` - VPS-specific guide

### For Testing
1. **Testing Checklist:** `/TESTING_CHECKLIST_CHART_EXPLANATIONS.md` - QA procedures
2. **Examples:** `/examples/` - Working examples and templates

---

## File Structure and Contents

```
/Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system/

ROOT DOCUMENTATION
├── README.md                          # Project overview and getting started
├── PROJECT_STATUS.md                  # Current system status (v2.3.0)
├── CHANGELOG.md                       # Version history and releases
├── SESSION_SUMMARY_2025-11-13.md     # Latest session documentation summary
├── PRODUCTION_DEPLOYMENT.md           # Production deployment guide (500+ lines)
├── Makefile                           # 30+ convenience commands
├── requirements.txt                   # Python dependencies
├── docker-compose.yml                 # Docker configuration (dev/local)
├── docker-compose.prod.yml            # Docker configuration (production)
├── Dockerfile.7d.prod                 # Production image definition
├── .env.example                       # Environment variables template

SOURCE CODE
├── src/
│   ├── forex_core/                   # Shared core library
│   │   ├── analysis/                 # Technical, fundamental, macro analysis
│   │   ├── config/                   # Pydantic settings and configuration
│   │   ├── data/                     # Data providers, models, registry
│   │   ├── forecasting/              # ARIMA, VAR, RF, ensemble models
│   │   ├── reporting/                # Charts, PDF builder (1,542 lines)
│   │   ├── notifications/            # Email notifications
│   │   └── utils/                    # Logging and utility functions
│   └── services/
│       ├── forecaster_7d/            # 7-day forecasting service
│       ├── forecaster_12m/           # 12-month forecasting service (planned)
│       └── importer_report/          # Importer reporting (planned)

TESTS
├── tests/
│   ├── e2e/                          # End-to-end tests
│   └── unit/                         # Unit tests
│       ├── test_pipeline.py
│       └── [other tests]

DOCUMENTATION
├── docs/
│   ├── sessions/                     # Session documentation and work logs
│   │   ├── 2025-11-13-1100-correlation-matrix-bug-fix-production-deployment.md
│   │   ├── SESSION_2025-11-12_VULTR_SYNC_CHART_EXPLANATIONS.md
│   │   ├── SESSION_2025-11-12_INSTITUTIONAL_UPGRADE.md
│   │   ├── SESSION_2025-11-12_REFINEMENT.md
│   │   └── SESSION_2025-11-12_CHART_EXPLANATIONS.md
│   │
│   ├── deployment/                   # Deployment guides
│   │   └── VULTR_DEPLOYMENT_GUIDE.md
│   │
│   ├── architecture/                 # Architecture documentation
│   │   └── SYSTEM_ARCHITECTURE.md
│   │
│   ├── reviews/                      # Code reviews
│   │   └── 2025-11-12-comprehensive-system-review.md
│   │
│   ├── CHART_INTERPRETATIONS_API.md  # Chart interpretation API docs
│   ├── DYNAMIC_CHART_INTERPRETATIONS.md
│   ├── DOCUMENTATION_INDEX.md        # This file
│   └── PDF_ENHANCEMENT_CHANGELOG.md

DATA & OUTPUT
├── data/                             # Historical data cache (24-hour TTL)
├── reports/                          # Generated PDF reports
├── logs/                             # Execution logs
├── examples/                         # Working examples and templates

CRON & SCHEDULING
├── cron/
│   └── 7d/
│       ├── crontab                   # Cron schedule
│       └── entrypoint.sh             # Container startup script

DEPLOYMENT (on Vultr server)
/home/deployer/forex-forecast-system/
├── src/                              # Same structure as local
├── venv/                             # Python virtual environment
├── data/                             # Data cache
├── reports/                          # Generated PDFs
├── logs/                             # Execution logs
├── run_7d_forecast.sh                # Cron execution script
├── docker-compose.prod.yml           # Production compose
└── .env                              # Production secrets (not in git)
```

---

## Session Documentation

### Latest Session (2025-11-13)

**File:** `/docs/sessions/2025-11-13-1100-correlation-matrix-bug-fix-production-deployment.md`
**Size:** 728 lines
**Duration:** ~2 hours
**Type:** Critical Bug Fix + Production Deployment

**Contents:**
- Executive summary of correlation matrix bug fix
- Root cause analysis (timezone mismatch)
- Production deployment architecture
- Auto-recovery mechanism (8-second restart)
- Systemd integration for server reboot resilience
- Complete list of commands for monitoring and management
- Technical deep dives on timezone handling and production architecture
- Success metrics and verification checklist

---

### Previous Sessions

**2025-11-12 (21:45):** Vultr Sync - Chart Explanations Fix
- `/docs/sessions/SESSION_2025-11-12_VULTR_SYNC_CHART_EXPLANATIONS.md`
- Synced chart explanations to production
- Verified PDF generation and email delivery

**2025-11-12 (Evening):** Chart Explanations Enhancement
- `/docs/sessions/SESSION_2025-11-12_CHART_EXPLANATIONS.md`
- Refactored PDF to pair chart explanations below images
- Added professional styling and page-break protection

**2025-11-12 (Afternoon):** Professional Refinement
- `/docs/sessions/SESSION_2025-11-12_REFINEMENT.md`
- Fixed date label overlapping
- Expanded methodology section (186 lines)
- Added chart explanations (80 lines)

**2025-11-12 (Morning):** Institutional-Grade PDF Enhancement
- `/docs/sessions/SESSION_2025-11-12_INSTITUTIONAL_UPGRADE.md`
- Upgraded from basic (3 pages) to institutional-grade (8-12 pages)
- Added 870+ lines of professional reporting code
- Integrated all analysis modules

---

## Deployment Documentation

### Quick Start Commands

**Local Development:**
```bash
make run-7d                 # Run 7-day forecast
make test                   # Run tests
make test-cov               # Run tests with coverage
make clean                  # Clean temporary files
```

**Docker:**
```bash
./docker-run.sh build       # Build images
./docker-run.sh 7d          # Run 7-day forecast
./docker-run.sh logs 7d     # View logs
```

**Production (Vultr):**
```bash
ssh reporting                                  # SSH to server
cd /home/deployer/forex-forecast-system       # Navigate to project
./run_7d_forecast.sh                          # Manual execution
tail -f logs/cron_7d.log                      # Monitor logs
ls -lth reports/ | head -5                    # View recent PDFs
```

### Production Monitoring

**View Live Cron Logs:**
```bash
ssh reporting 'docker exec usdclp-forecaster-7d tail -f /var/log/cron.log'
```

**Check Container Health:**
```bash
ssh reporting 'docker inspect usdclp-forecaster-7d | grep -A 10 State'
```

**Restart Service:**
```bash
ssh reporting 'docker-compose -f docker-compose.prod.yml restart forecaster-7d'
```

---

## Key Documentation Files

### System Documentation

| File | Purpose | Lines | Updated |
|------|---------|-------|---------|
| PROJECT_STATUS.md | Current system status and version | 795 | 2025-11-13 |
| CHANGELOG.md | Version history and releases | 200 | 2025-11-13 |
| README.md | Project overview | ~100 | 2025-11-12 |
| PRODUCTION_DEPLOYMENT.md | Production deployment guide | 500+ | 2025-11-13 |

### Architecture Documentation

| File | Purpose | Updated |
|------|---------|---------|
| docs/architecture/SYSTEM_ARCHITECTURE.md | Technical architecture | 2025-11-12 |
| docs/deployment/VULTR_DEPLOYMENT_GUIDE.md | VPS-specific deployment | 2025-11-12 |
| docs/DOCKER.md | Docker usage guide | 2025-11-12 |

### Session Documentation

| File | Date | Focus | Duration |
|------|------|-------|----------|
| 2025-11-13-1100-correlation-matrix-bug-fix... | Nov 13 | Bug fix + Production | 2 hours |
| SESSION_2025-11-12_VULTR_SYNC_CHART_EXPLANATIONS.md | Nov 12 | Vultr Sync | 1 hour |
| SESSION_2025-11-12_CHART_EXPLANATIONS.md | Nov 12 | Chart Explanations | 1.5 hours |
| SESSION_2025-11-12_REFINEMENT.md | Nov 12 | Professional Refinement | 2 hours |
| SESSION_2025-11-12_INSTITUTIONAL_UPGRADE.md | Nov 12 | PDF Enhancement | 6 hours |

---

## API and Technical Documentation

### Chart Interpretation API
**File:** `/docs/CHART_INTERPRETATIONS_API.md`
- Chart interpretation interface documentation
- Method signatures and examples
- Configuration options

### Dynamic Chart Interpretations
**File:** `/docs/DYNAMIC_CHART_INTERPRETATIONS.md`
- Implementation details for dynamic insights
- RSI, MACD, TPM value extraction
- Risk regime calculation

### PDF Enhancement Details
**File:** `/docs/PDF_ENHANCEMENT_CHANGELOG.md`
- PDF feature enhancements
- Chart formatting improvements
- Styling and layout changes

---

## How to Find What You Need

### "I want to..."

**Understand the current system status**
→ Read: `PROJECT_STATUS.md`

**Know what changed in the latest version**
→ Read: `CHANGELOG.md` (v2.3.0 section)

**Learn about today's work session**
→ Read: `SESSION_SUMMARY_2025-11-13.md` or full session doc in `docs/sessions/`

**Deploy to production**
→ Read: `PRODUCTION_DEPLOYMENT.md` and `docs/deployment/VULTR_DEPLOYMENT_GUIDE.md`

**Monitor the production system**
→ See: "Production Monitoring" section in `docs/sessions/2025-11-13-*.md`

**Understand system architecture**
→ Read: `docs/architecture/SYSTEM_ARCHITECTURE.md`

**Run tests locally**
→ Use: `make test` or `make test-cov`

**Reproduce the bug fix**
→ Read: `docs/sessions/2025-11-13-*.md` → "Correlation Matrix Bug Fix" section

**Set up Docker locally**
→ Read: `docs/DOCKER.md`

**Access production server**
→ Command: `ssh reporting` (see `PROJECT_STATUS.md` for details)

**Review code changes**
→ Check: `git log --oneline` or specific commit hash in session docs

---

## Documentation Standards

### What Gets Documented

1. **Every session of work** → `docs/sessions/YYYY-MM-DD-HHMM-description.md`
2. **Every production deployment** → Updated in `PRODUCTION_DEPLOYMENT.md`
3. **Every version release** → Entry in `CHANGELOG.md`
4. **Every critical change** → Updated in `PROJECT_STATUS.md`

### Documentation Format

- **Session docs:** 700+ lines, detailed technical deep dives
- **Changelog:** Keep a Changelog format with Semantic Versioning
- **Status:** Living document, updated with major changes
- **Guides:** Step-by-step procedures with example commands

### How to Retrace Your Steps

From any session documentation:
1. Check the commit hash in the session doc
2. Run: `git show COMMIT_HASH` to see exact changes
3. Check session "Files Modified" section for code locations
4. Use session "Useful Commands" for testing/verification

---

## Maintenance and Updates

**Documentation is updated when:**
- Session completes (auto-documented by session-doc-keeper)
- New version released (CHANGELOG entry added)
- Major features added (PROJECT_STATUS.md updated)
- Production issues occur (Tracked in Known Issues)

**To add to documentation:**
1. Session work → Create `docs/sessions/YYYY-MM-DD-HHMM-description.md`
2. New feature → Add to `CHANGELOG.md` under version
3. Issue found → Update "Known Issues" in `PROJECT_STATUS.md`
4. Process change → Update relevant deployment/architecture doc

**Documentation ownership:**
- Project Status: Development team
- Architecture: Lead developer
- Deployment: DevOps engineer
- Sessions: Developer who worked on feature

---

## Contact & Support

**For Questions About:**

- **System Status:** See `PROJECT_STATUS.md`
- **Recent Changes:** See `CHANGELOG.md`
- **Production Issues:** See latest session doc + "Known Issues"
- **Code Changes:** See specific session documentation
- **Deployment:** See `PRODUCTION_DEPLOYMENT.md`

**Quick Links:**
- GitHub: https://github.com/Pit-CL/forex-forecast-system
- Production Server: `ssh reporting`
- Developer: rafael@cavara.cl
- Recipients: rafael@cavara.cl, valentina@cavara.cl

---

**Last Updated:** 2025-11-13
**Maintained By:** Development Team
**Archive Location:** `/docs/sessions/`
**Total Documentation:** 1,700+ lines across all files
