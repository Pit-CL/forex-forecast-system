# Alert Email Generator - Quick Start Guide

Get started with the Alert Email Generator in 5 minutes.

---

## Installation

```bash
# Optional: Install WeasyPrint for PDF generation
# macOS
brew install pango libffi
pip install weasyprint

# Ubuntu/Debian
sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0
pip install weasyprint

# Note: PDF generation works without WeasyPrint (HTML only)
```

---

## Basic Usage

### Market Shock Alerts

```python
from forex_core.alerts import MarketShockDetector, generate_market_shock_email
import pandas as pd

# 1. Load market data (last 60 days minimum)
data = pd.read_csv("data/market_data.csv")

# 2. Detect market shocks
detector = MarketShockDetector()
alerts = detector.detect_all(data)

# 3. Generate email (if alerts found)
if alerts:
    market_data = {
        "usdclp": data["usdclp"].iloc[-1],
        "copper_price": data["copper_price"].iloc[-1],
        "dxy": data["dxy"].iloc[-1],
        "vix": data["vix"].iloc[-1],
        "timestamp": "14/11/2025 18:00"
    }

    html, pdf = generate_market_shock_email(alerts, market_data)

    # Save outputs
    with open("market_alert.html", "w") as f:
        f.write(html)

    if pdf:
        with open("market_alert.pdf", "wb") as f:
            f.write(pdf)
```

### Model Performance Alerts

```python
from forex_core.alerts import (
    ModelPerformanceMonitor,
    generate_model_performance_email
)
from pathlib import Path

# 1. Initialize monitor
monitor = ModelPerformanceMonitor(baseline_dir=Path("data/baselines"))

# 2. Check performance
current_metrics = {
    "rmse": 13.8,
    "mae": 10.5,
    "mape": 1.2,
    "directional_accuracy": 0.52
}

alerts = monitor.check_degradation(
    model_name="xgboost_7d",
    current_metrics=current_metrics,
    horizon="7d"
)

# 3. Generate email (if alerts found)
if alerts:
    html, pdf = generate_model_performance_email(alerts)

    # Save outputs
    with open("model_alert.html", "w") as f:
        f.write(html)

    if pdf:
        with open("model_alert.pdf", "wb") as f:
            f.write(pdf)
```

---

## Test It Out

```bash
# Test both alert types with sample data
python scripts/test_alert_email_generator.py --type both

# Test market shock only
python scripts/test_alert_email_generator.py --type market

# Test model performance only
python scripts/test_alert_email_generator.py --type model

# Skip PDF generation (HTML only)
python scripts/test_alert_email_generator.py --no-pdf

# Output location
ls output/alerts/
```

---

## Email Integration (Future)

```python
# Placeholder for future send_alert_email.py integration

from forex_core.alerts import generate_market_shock_email
# from your_email_system import send_email  # TODO

alerts = detector.detect_all(data)

if alerts:
    market_data = {...}
    html, pdf = generate_market_shock_email(alerts, market_data)

    # Determine subject
    has_critical = any(a.severity.value.upper() == "CRITICAL" for a in alerts)
    subject = f"🚨 CRÍTICO" if has_critical else f"⚠️ ALERTA"
    subject += f": {alerts[0].alert_type.value.replace('_', ' ').title()}"

    # Send email
    send_email(
        to="alerts@company.com",
        subject=subject,
        html_body=html,
        attachments=[("alert.pdf", pdf)] if pdf else []
    )
```

---

## Required Data Format

### Market Shock Detection

```python
import pandas as pd

data = pd.DataFrame({
    'date': pd.date_range('2025-01-01', periods=60),  # Min 30 days
    'usdclp': [...],        # USD/CLP exchange rate
    'copper_price': [...],  # Copper price ($/lb)
    'dxy': [...],           # US Dollar Index
    'vix': [...],           # Volatility Index
    'tpm': [...]            # Chilean policy rate (%)
})
```

### Model Performance Monitoring

```python
current_metrics = {
    "rmse": float,               # Root Mean Squared Error
    "mae": float,                # Mean Absolute Error
    "mape": float,               # Mean Absolute Percentage Error
    "directional_accuracy": float  # Ratio (0-1)
}
```

---

## Customization

### Tune Alert Thresholds

```python
# More sensitive (more alerts)
detector = MarketShockDetector(
    usdclp_daily_threshold=1.5,  # Default: 2.0%
    copper_daily_threshold=3.0,  # Default: 5.0%
    vix_fear_threshold=25.0      # Default: 30.0
)

# Less sensitive (fewer alerts)
detector = MarketShockDetector(
    usdclp_daily_threshold=3.0,
    copper_daily_threshold=7.0,
    vix_fear_threshold=35.0
)
```

### Disable PDF Generation

```python
# HTML only (faster, no WeasyPrint needed)
html, pdf = generate_market_shock_email(
    alerts,
    market_data,
    generate_pdf=False  # pdf will be None
)
```

---

## Troubleshooting

### Issue: WeasyPrint Import Fails

**Symptom**: `WeasyPrint not available - PDF generation disabled`

**Solutions**:
1. Install system dependencies (see Installation above)
2. Continue without PDF (HTML is sufficient)

### Issue: No Alerts Generated

**Check**:
- Data has at least 30 days
- Data has recent volatility/movement
- Thresholds not too high

**Debug**:
```python
# Check data
print(f"Data points: {len(data)}")
print(f"Latest USD/CLP: {data['usdclp'].iloc[-1]}")
print(f"Daily change: {data['usdclp'].pct_change().iloc[-1] * 100:.2f}%")

# Lower thresholds
detector = MarketShockDetector(usdclp_daily_threshold=1.0)
alerts = detector.detect_all(data)
```

### Issue: Empty HTML

**Check**:
- `alerts` list is not empty
- `market_data` dict has required keys

**Fix**:
```python
if not alerts:
    print("No alerts to display")
elif "usdclp" not in market_data:
    print("Missing market_data keys")
else:
    html, pdf = generate_market_shock_email(alerts, market_data)
```

---

## Output Examples

### Market Shock Alert

**Subject**: `🚨 ALERTA: Trend Reversal - USD/CLP`

**HTML Sections**:
- Header with severity badge
- Market snapshot table (USD/CLP, Copper, DXY, VIX)
- Detected alerts grouped by severity (CRITICAL, WARNING, INFO)
- Priority recommendations
- Footer with timestamp

**PDF**: 2 pages max, printable format

### Model Performance Alert

**Subject**: `🚨 CRÍTICO: Performance del Modelo - xgboost_7d`

**HTML Sections**:
- Header with model name
- Alert summary badges
- Alerts by severity with metrics comparison table
- Recommendations per alert
- Footer

**PDF**: 2 pages max, printable format

---

## Next Steps

1. **Test with your data**: Run test script with real market data
2. **Review HTML output**: Open in browser to verify formatting
3. **Integrate with email**: Implement email dispatch (future)
4. **Monitor production**: Track false positive rate, tune thresholds

---

## Documentation

- **Complete API Reference**: [ALERT_EMAIL_GENERATOR.md](./ALERT_EMAIL_GENERATOR.md)
- **Implementation Summary**: [ALERT_EMAIL_GENERATOR_SUMMARY.md](./ALERT_EMAIL_GENERATOR_SUMMARY.md)
- **Market Shock Detector**: [MARKET_SHOCK_DETECTOR_USAGE.md](./MARKET_SHOCK_DETECTOR_USAGE.md)

---

## Support

**Issues**:
- Check documentation above
- Review test script examples
- Verify data format
- Check system dependencies (WeasyPrint)

**Questions**:
- Refer to comprehensive documentation
- Check implementation plan: `docs/IMPLEMENTATION_PLAN.md`

---

**Happy Alerting!** 🚨
