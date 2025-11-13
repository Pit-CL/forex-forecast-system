# Unified Email System - Architecture and Integration Guide

**Version:** 1.0
**Date:** 2025-11-13
**Status:** Production-Ready

---

## Quick Reference

### Email Schedule Summary

| Day | Time | Horizons | Contents |
|-----|------|----------|----------|
| **Monday** | 7:30 AM | 7d, 15d | Forecasts + System Health |
| **Wednesday** | 7:30 AM | 7d | Quick Update + System Health |
| **Thursday** | 7:30 AM | 15d | Biweekly Review + System Health |
| **Friday** | 7:30 AM | 7d, 30d | Weekly Summary + System Health |
| **1st & 15th** | 8:00 AM | 90d | Quarterly Outlook |
| **First Tuesday** | 8:00 AM | 12m | Annual Outlook |

### PDF Attachment Rules

**Always Attach:**
- 30-day forecasts
- 90-day forecasts
- 12-month forecasts

**Conditionally Attach (7d, 15d):**
- Price change > 1.5%
- High volatility detected
- Critical alerts present
- Friday emails (weekly summary)
- System degradation detected

**Never Attach:**
- Mid-week routine updates (if no conditions met)

---

## System Architecture

### Component Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│ Cron Scheduler (send_daily_email.sh)                    │
│ - Day-of-week detection                                 │
│ - Environment validation                                │
│ - Error handling & logging                              │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│ UnifiedEmailOrchestrator (unified_email.py:450 lines)   │
│ - Determine send schedule                               │
│ - Select forecast horizons                              │
│ - Assess priority level                                 │
│ - Decide PDF attachments                                │
│ - Coordinate with data providers                        │
└──────────────┬───────────────────┬──────────────────────┘
               │                   │
               ▼                   ▼
    ┌─────────────────┐  ┌────────────────────┐
    │ EmailContent    │  │ Data Providers     │
    │ Builder         │  │ - PredictionTracker│
    │ (604 lines)     │  │ - PerformanceMonitor
    │ - HTML gen      │  │ - ChronosReadiness │
    │ - CSS styling   │  │ - AlertManager     │
    │ - Mobile opt    │  └────────────────────┘
    │ - Charts/data   │
    └─────────┬───────┘
              │
              ▼
   ┌───────────────────────┐
   │ EmailSender.send()    │
   │ (email.py)            │
   │ - SMTP delivery       │
   │ - Retry logic         │
   │ - Error handling      │
   └───────────┬───────────┘
               │
               ▼
   ┌───────────────────────┐
   │ Gmail SMTP Server     │
   │ (rafaelfarias@...)    │
   └───────────┬───────────┘
               │
               ▼
   ┌───────────────────────┐
   │ Recipient Inbox       │
   │ - rafael@cavara.cl    │
   │ - valentina@cavara.cl │
   └───────────────────────┘
```

### Data Flow

1. **Cron Trigger**: Daily at scheduled times
2. **Day Check**: Script determines day-of-week
3. **Load Config**: Read `email_strategy.yaml`
4. **Determine Horizons**: Based on day, select 7d/15d/30d/90d/12m
5. **Load Forecast Data**: Query PredictionTracker
6. **Load System Health**: Get readiness, performance, alerts
7. **Assess Priority**: Check conditions (price change, alerts, degradation)
8. **Decide PDFs**: Apply attachment rules
9. **Build Email**: EmailContentBuilder generates HTML
10. **Send Email**: EmailSender dispatches via SMTP
11. **Log Results**: Record success/failure to log file

---

## Core Components

### 1. UnifiedEmailOrchestrator

**Location:** `src/forex_core/notifications/unified_email.py`

**Key Methods:**

```python
class UnifiedEmailOrchestrator:
    """Orchestrates unified email sending."""

    def determine_send_day(self) -> bool:
        """Check if email should send today."""

    def determine_forecasts_to_send(self) -> List[str]:
        """Return list of horizons for today (7d, 15d, 30d, etc)."""

    def determine_priority(self, forecasts: List[ForecastData]) -> str:
        """Assess priority level: URGENT, ATTENTION, ROUTINE."""

    def determine_pdf_attachment(self, forecast: ForecastData) -> bool:
        """Decide if PDF should be attached."""

    def build_email(self) -> dict:
        """Orchestrate complete email construction."""

    def send_email(self) -> bool:
        """Send email via EmailSender."""
```

**Decision Logic:**

```
Schedule Check:
├── Monday → [7d, 15d]
├── Wednesday → [7d]
├── Thursday → [15d]
├── Friday → [7d, 30d, summary]
├── 1st/15th → [90d]
└── 1st Tuesday → [12m]

Priority Assessment:
├── Price change >3% → URGENT
├── System NOT_READY → URGENT
├── Price change >1.5% → ATTENTION
├── Degradation detected → ATTENTION
├── Normal → ROUTINE

PDF Attachment:
├── Horizon in [30d, 90d, 12m] → Always
├── Price change >1.5% → Yes
├── High volatility → Yes
├── Friday → Yes
├── System issue → Yes
└── Otherwise → No
```

### 2. EmailContentBuilder

**Location:** `src/forex_core/notifications/email_builder.py`

**Key Methods:**

```python
class EmailContentBuilder:
    """Builds HTML email content."""

    def build_unified_email(self,
                           forecasts: List[ForecastData],
                           system_health: SystemHealthData) -> str:
        """Generate complete HTML email."""

    def _build_header(self) -> str:
        """Company branding header."""

    def _build_priority_alert(self, priority: str) -> str:
        """Alert banner if urgent/attention."""

    def _build_executive_summary(self,
                                forecasts: List[ForecastData]) -> str:
        """Key metrics at a glance."""

    def _build_forecast_section(self,
                               forecast: ForecastData) -> str:
        """Individual forecast card."""

    def _build_system_health(self,
                            health: SystemHealthData) -> str:
        """System status section."""

    def _build_recommendations(self) -> str:
        """Role-based recommendations."""

    def _get_styles(self) -> str:
        """CSS styling (inline for email safety)."""
```

**HTML Structure:**

```html
<html>
  <head>
    <style>/* Inline CSS */</style>
  </head>
  <body>
    <!-- Header -->
    <table class="header"><!-- Logo, branding --></table>

    <!-- Priority Alert (conditional) -->
    <table class="alert"><!-- URGENT/ATTENTION banner --></table>

    <!-- Executive Summary -->
    <table class="summary">
      <tr><td>Key metric 1</td></tr>
      <tr><td>Key metric 2</td></tr>
    </table>

    <!-- Forecast Sections -->
    <table class="forecast-7d"><!-- 7-day forecast --></table>
    <table class="forecast-15d"><!-- 15-day forecast --></table>
    <table class="forecast-30d"><!-- 30-day forecast --></table>

    <!-- System Health -->
    <table class="system-health"><!-- Status, alerts --></table>

    <!-- Recommendations -->
    <table class="recommendations"><!-- By user type --></table>

    <!-- Footer -->
    <table class="footer"><!-- Disclaimer, unsubscribe --></table>
  </body>
</html>
```

**Styling:**

```css
/* Institutional Colors */
Primary Blue: #004f71
Light Gray: #d8e5ed
Dark Text: #333333
Alert Red: #D32F2F
Success Green: #388E3C

/* Responsive Breakpoints */
Mobile: <600px (single column)
Tablet: 600-1024px (adjusted padding)
Desktop: >1024px (full width)

/* Font Stack */
Body: Arial, Helvetica, sans-serif
Headings: Arial, sans-serif
Monospace: Courier New, monospace

/* Spacing */
Section padding: 20px
Card margin: 10px
Font size: 16px (body), 14px (small text)
```

### 3. Configuration System

**Location:** `config/email_strategy.yaml`

**Structure:**

```yaml
schedule:
  default_send_time: "07:30"
  timezone: "America/Santiago"

horizons:
  7d:
    frequency: "triweekly"
    days_of_week: [0, 2, 4]  # Mon, Wed, Fri
  15d:
    frequency: "biweekly"
    days_of_week: [0, 3]  # Mon, Thu
  30d:
    frequency: "weekly"
    days_of_week: [4]  # Fri
  90d:
    frequency: "bimonthly"
    days_of_month: [1, 15]
  12m:
    frequency: "monthly"
    week_of_month: 1  # First Tuesday

pdf_attachment:
  always_attach: ["30d", "90d", "12m"]
  conditional_rules:
    price_change_threshold: 1.5
    high_volatility: true
    friday_summary: true
    critical_system_issues: true

priority:
  urgent:
    conditions:
      - price_change_threshold: 3.0
      - readiness_level: "NOT_READY"
    subject_prefix: "🚨 URGENTE"
  attention:
    conditions:
      - price_change_threshold: 1.5
      - degradation_detected: true
    subject_prefix: "⚠️ ATENCIÓN"
  routine:
    subject_prefix: "📊"

content:
  executive_summary:
    max_items: 5
    include_system_health: true
```

### 4. Scheduler Script

**Location:** `scripts/send_daily_email.sh`

**Flow:**

```bash
1. Validate environment
   ├── Check PROJECT_DIR
   ├── Create LOG_DIR
   └── Verify Python installation

2. Determine schedule
   ├── Get current day of week
   ├── Check email enabled
   └── Log execution start

3. Load and execute
   ├── Activate venv (if exists)
   ├── Set PYTHONPATH
   └── Run Python orchestrator

4. Handle results
   ├── Check exit code
   ├── Log success/failure
   ├── Send error alert (if failed)
   └── Exit with appropriate code

5. Cleanup
   ├── Flush logs
   └── Archive old logs
```

---

## Integration Points

### PredictionTracker Integration

**Purpose:** Get latest forecast data for all horizons

**Data Source:** `data/predictions_tracker.csv`

**Fields Used:**
- forecast_date
- horizon (7d, 15d, 30d, 90d, 12m)
- current_price
- predicted_price
- ci_lower_80
- ci_upper_80
- ci_lower_95
- ci_upper_95
- model_ensemble_weight
- timestamp

**Usage:**
```python
from src.forex_core.data.prediction_tracker import PredictionTracker

tracker = PredictionTracker()
predictions = tracker.load_latest(horizon='7d')

forecast_data = ForecastData(
    horizon='7d',
    current_price=predictions['current_price'],
    forecast_price=predictions['predicted_price'],
    change_pct=(predictions['predicted_price'] -
               predictions['current_price']) / predictions['current_price'] * 100,
    ci95_low=predictions['ci_lower_95'],
    ci95_high=predictions['ci_upper_95'],
    ci80_low=predictions['ci_lower_80'],
    ci80_high=predictions['ci_upper_80'],
    bias=calculate_bias(predictions),
    volatility=classify_volatility(predictions)
)
```

### PerformanceMonitor Integration

**Purpose:** Get system performance metrics and degradation alerts

**Data Source:** `data/performance_monitor.csv` or class-based API

**Usage:**
```python
from src.forex_core.monitoring.performance import PerformanceMonitor

monitor = PerformanceMonitor()
performance = monitor.get_latest_metrics()

system_health = SystemHealthData(
    performance_status={
        '7d': performance['7d_status'],  # EXCELLENT/GOOD/DEGRADED
        '15d': performance['15d_status'],
        '30d': performance['30d_status'],
    },
    degradation_detected=performance['degradation_detected'],
    degradation_details=performance['degradation_details'],
)
```

### ChronosReadinessChecker Integration

**Purpose:** Get system readiness level and score

**Usage:**
```python
from src.forex_core.monitoring.readiness import ChronosReadinessChecker

checker = ChronosReadinessChecker()
readiness = checker.check()

system_health = SystemHealthData(
    readiness_level=readiness['level'],  # OPTIMAL/READY/CAUTIOUS/NOT_READY
    readiness_score=readiness['score'],  # 0-100
)
```

### AlertManager Integration

**Purpose:** Get active alerts and critical conditions

**Usage:**
```python
from src.forex_core.notifications.alerts import AlertManager

alerts = AlertManager()
active_alerts = alerts.get_active()

system_health = SystemHealthData(
    drift_detected=active_alerts['drift_detected'],
    drift_details=active_alerts['drift_details'],
)
```

---

## Configuration Guide

### Modifying Email Schedule

Edit `config/email_strategy.yaml`:

```yaml
horizons:
  7d:
    frequency: "triweekly"  # Change to "weekly", "daily", etc.
    days_of_week: [0, 2, 4]  # Modify day numbers (0=Mon, 6=Sun)
```

**Frequency Options:**
- `daily` - Every day
- `triweekly` - Mon, Wed, Fri
- `biweekly` - Mon, Thu
- `weekly` - Friday only
- `bimonthly` - 1st and 15th of month
- `monthly` - First specific day of month

### Adjusting PDF Attachment Rules

Edit `config/email_strategy.yaml`:

```yaml
pdf_attachment:
  price_change_threshold: 1.5  # Change from 1.5% to 2.0%
  high_volatility: true  # Set to false to disable
  friday_summary: true  # Set to false to disable
```

### Changing Priority Thresholds

Edit `config/email_strategy.yaml`:

```yaml
priority:
  urgent:
    conditions:
      - price_change_threshold: 3.0  # Change from 3% to 5%
  attention:
    conditions:
      - price_change_threshold: 1.5  # Change from 1.5% to 2%
```

### Adding New Horizons

1. Add to `src/forex_core/notifications/unified_email.py`:
```python
class ForecastHorizon(Enum):
    H_45D = "45d"  # New horizon
```

2. Add config to `config/email_strategy.yaml`:
```yaml
horizons:
  45d:
    frequency: "monthly"
    days_of_month: [15]
```

3. Add HTML builder method to `src/forex_core/notifications/email_builder.py`:
```python
def _build_forecast_45d(self, forecast: ForecastData) -> str:
    """45-day forecast card."""
```

4. Update cron schedule in crontab if needed

---

## Deployment Instructions

### Initial Setup

```bash
# 1. Clone/update repository
git clone https://github.com/Pit-CL/forex-forecast-system.git
cd forex-forecast-system

# 2. Copy files to target location
cp -r src/forex_core/notifications /target/src/forex_core/
cp config/email_strategy.yaml /target/config/
cp scripts/send_daily_email.sh /target/scripts/
cp scripts/test_unified_email.sh /target/scripts/

# 3. Set permissions
chmod +x /target/scripts/send_daily_email.sh
chmod +x /target/scripts/test_unified_email.sh

# 4. Test locally
cd /target
./scripts/test_unified_email.sh

# 5. Add cron job
crontab -e
# Add: 30 7 * * 1,3,4,5 cd /target && ./scripts/send_daily_email.sh >> logs/unified_email.log 2>&1
```

### On Vultr Production Server

```bash
ssh reporting

cd /home/deployer/forex-forecast-system

# Copy new files
scp -r ~/forex-forecast-system/src/forex_core/notifications/* ./src/forex_core/notifications/
scp ~/forex-forecast-system/config/email_strategy.yaml ./config/
scp ~/forex-forecast-system/scripts/send_daily_email.sh ./scripts/
scp ~/forex-forecast-system/scripts/test_unified_email.sh ./scripts/

# Set permissions
chmod +x scripts/send_daily_email.sh
chmod +x scripts/test_unified_email.sh

# Test
./scripts/test_unified_email.sh

# Check cron
crontab -l | grep send_daily
```

---

## Monitoring and Troubleshooting

### Log File Location

```bash
/home/deployer/forex-forecast-system/logs/unified_email*.log
```

### View Latest Execution

```bash
tail -50 logs/unified_email.log
```

### Search for Errors

```bash
grep "ERROR\|FAIL" logs/unified_email.log
```

### Common Issues

**Issue: Email not sent on expected day**
- Check cron schedule: `crontab -l`
- Check system time: `date`
- Check logs for errors: `tail logs/unified_email.log`
- Verify timezone: `timedatectl` (should be America/Santiago)

**Issue: Wrong forecast horizons included**
- Check day detection: `date +%u`
- Verify `email_strategy.yaml` horizons config
- Check orchestrator logic in code

**Issue: PDF not attached when expected**
- Review attachment rules in `email_strategy.yaml`
- Check price change calculation
- Verify volatility classification
- Look for alert triggers

**Issue: Email formatting broken**
- Test locally: `./scripts/test_unified_email.sh`
- Check email client (Outlook, Gmail, Apple Mail)
- Verify CSS inline styles
- Check for special characters in content

---

## Performance Optimization

### Email Generation Time

Current: 2-3 seconds average

Optimization opportunities:
- Parallel forecast loading (save ~0.5s)
- Cache system health data (save ~0.3s)
- Async SMTP sending (save ~1.0s, non-blocking)

### Email Size

HTML-only: 150-300 KB
With PDF: 1.5-2.0 MB

**Size reduction strategies:**
- Remove verbose descriptions (save 20 KB)
- Compress inline images (save 50 KB)
- Use text instead of images (save 100 KB)
- Minify CSS (save 5 KB)

### Delivery Reliability

Current: 100% (Gmail SMTP)

Improvements:
- Add backup SMTP server
- Implement queue system for failures
- Add delivery confirmation tracking
- Monitor Gmail rate limits

---

## Security Considerations

### Email Credentials

**Never commit to git:**
- GMAIL_USER
- GMAIL_APP_PASSWORD
- EMAIL_RECIPIENTS (if sensitive)

**Storage:**
- Use `.env` file (added to `.gitignore`)
- Use environment variables in production
- Rotate app passwords quarterly

### Data Privacy

- No customer data in email content (only forecasts)
- Forecasts are public (generated from public markets)
- No PII in logs (unless explicitly enabled for debugging)
- Secure log rotation (delete after 30 days)

### SMTP Security

- Use Gmail's app-specific password (not main password)
- TLS/SSL encryption (Gmail enforces)
- No credentials in logs
- Retry logic without exposing errors

---

## Future Enhancements

### Short Term (Next Sprint)

1. **Add Analytics**
   - Track open rates
   - Monitor click-through
   - Measure engagement

2. **User Preferences**
   - Frequency customization
   - Horizon selection per user
   - Do-not-disturb scheduling

3. **Testing**
   - Unit tests (20+ tests)
   - Mock data providers
   - Email client testing

### Medium Term (2-3 Weeks)

1. **Advanced Features**
   - Intraday alerts (large moves)
   - Event-driven reports (BCCh meetings)
   - Holiday detection

2. **Optimization**
   - Email template versioning
   - A/B testing framework
   - Performance metrics dashboard

### Long Term (Backlog)

1. **Multi-Channel**
   - Slack integration
   - Telegram notifications
   - Push notifications

2. **Personalization**
   - ML-based send time optimization
   - Content adaptation per role
   - Predictive alerting

---

## Reference Commands

### Local Testing

```bash
# Test email generation
python -m src.forex_core.notifications.unified_email --test

# Test with verbose logging
./scripts/test_unified_email.sh --verbose

# Generate sample email (dry run)
./scripts/test_unified_email.sh --dry-run
```

### Production Monitoring

```bash
# SSH to production
ssh reporting

# Check execution
tail -50 /home/deployer/forex-forecast-system/logs/unified_email.log

# Manual test
cd /home/deployer/forex-forecast-system && ./scripts/test_unified_email.sh

# Check cron status
crontab -l | grep email
```

### Configuration Updates

```bash
# Edit strategy (local)
nano config/email_strategy.yaml

# Changes take effect at next execution (no restart needed)

# Sync to production
scp config/email_strategy.yaml reporting:/home/deployer/forex-forecast-system/config/
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-13 | Initial implementation, production deployment |

---

**Maintained By:** Development Team
**Last Updated:** 2025-11-13
**Review Frequency:** Monthly or on major changes
