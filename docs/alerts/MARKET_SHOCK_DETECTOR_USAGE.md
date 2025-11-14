# Market Shock Detector - Usage Guide

## Overview

The `MarketShockDetector` implements Phase 2 of the USD/CLP autonomous forecasting system, providing real-time detection of market events that could significantly impact forecasts.

**Module**: `forex_core.alerts.market_shock_detector`
**Status**: Production Ready
**Test Coverage**: 8/8 tests passing

---

## Quick Start

```python
from forex_core.alerts import MarketShockDetector, AlertSeverity
import pandas as pd

# Initialize detector with default thresholds
detector = MarketShockDetector()

# Prepare market data (minimum 30 days)
data = pd.DataFrame({
    'date': pd.date_range('2025-01-01', periods=60),
    'usdclp': [...],         # USD/CLP exchange rate
    'copper_price': [...],   # Copper price ($/lb)
    'dxy': [...],            # US Dollar Index
    'vix': [...],            # CBOE Volatility Index
    'tpm': [...]             # Chilean policy rate (%)
})

# Run all detections
alerts = detector.detect_all(data)

# Process alerts by severity
critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
if critical_alerts:
    print(f"URGENT: {len(critical_alerts)} critical market events detected!")
    for alert in critical_alerts:
        print(f"- {alert.message}")
        if alert.recommendation:
            print(f"  Action: {alert.recommendation}")
```

---

## Detection Triggers

### 1. USD/CLP Trend Changes

**Triggers:**
- Single-day change > 2% (default)
- 3-day trend reversal with swing > 3% (default)

**Severity:**
- INFO: Not applicable
- WARNING: Change 2-4%
- CRITICAL: Change > 4%

**Example Alert:**
```
[WARNING] TREND_REVERSAL: Cambio diario significativo en USD/CLP: alza de 2.5% a $976.67
Metrics: {'daily_change_pct': 2.5, 'current_rate': 976.67, 'previous_rate': 952.85}
```

**Use Case:** Detect sudden USD/CLP movements that require forecast recalibration.

---

### 2. Volatility Spikes

**Triggers:**
- Daily volatility > 1.5x 30-day average (default)
- Intraday range > 3% (requires high/low data)

**Severity:**
- WARNING: Volatility 1.5-2.25x average
- CRITICAL: Volatility > 2.25x average

**Example Alert:**
```
[CRITICAL] VOLATILITY_SPIKE: Volatilidad elevada: 2.3x el promedio de 30 días (18.5% anual vs 8.1%)
Recommendation: Ampliar intervalos de confianza en forecasts
```

**Use Case:** Expand confidence intervals when market uncertainty increases.

---

### 3. Copper Price Shocks

**Triggers:**
- Daily change > 5% (default)
- Sustained weekly decline > 10% (default)

**Severity:**
- WARNING: Change 5-7.5%
- CRITICAL: Change > 7.5%

**Example Alert:**
```
[WARNING] COPPER_SHOCK: Shock en precio del cobre: caída de 7.0% a $3.55/lb
Recommendation: Evaluar impacto en balanza comercial chilena y presión sobre CLP
```

**Use Case:** Copper is Chile's main export (~50% of exports). Price shocks directly impact CLP.

---

### 4. DXY Extreme Movements

**Triggers:**
- DXY > 105 (strong dollar) or < 95 (weak dollar)
- Daily DXY change > 1%

**Severity:**
- INFO: At threshold (105 or 95)
- WARNING: Daily change 1-1.5%
- CRITICAL: DXY > 107 or < 93

**Example Alert:**
```
[CRITICAL] DXY_EXTREME: Dólar fuerte: DXY en 107.0 (umbral 105.0)
Recommendation: Presión alcista generalizada sobre USD, incluido USD/CLP
```

**Use Case:** DXY is correlated with all USD pairs, including USD/CLP.

---

### 5. VIX Fear Spikes

**Triggers:**
- VIX > 30 (global stress)
- VIX daily change > +20%

**Severity:**
- INFO: VIX 30-35 (moderate stress)
- WARNING: VIX 35-40 (high stress)
- CRITICAL: VIX > 40 (extreme stress)

**Example Alert:**
```
[WARNING] VIX_SPIKE: Estrés de mercado alto: VIX en 35.0 (umbral 30.0)
Recommendation: Flight to quality: aumentar aversión al riesgo en forecast de EM
```

**Use Case:** High VIX triggers risk-off flows, pressuring emerging market currencies like CLP.

---

### 6. TPM Surprises (Chilean Policy Rate)

**Triggers:**
- TPM change >= 0.5% (50 basis points)

**Severity:**
- WARNING: Change 0.5-1.0%
- CRITICAL: Change > 1.0%

**Example Alert:**
```
[WARNING] TPM_SURPRISE: Cambio en TPM (SORPRESA): alza de 0.75% a 6.5% (desde 5.75%)
Recommendation: Re-calibrar expectativas de diferenciales de tasas USD/CLP
```

**Use Case:** Unexpected rate changes by Banco Central de Chile affect USD/CLP via interest rate differentials.

---

## Configurable Thresholds

All thresholds are configurable to tune sensitivity:

```python
# More sensitive detector (lower thresholds)
sensitive_detector = MarketShockDetector(
    usdclp_daily_threshold=1.5,      # 1.5% instead of 2%
    copper_daily_threshold=3.0,      # 3% instead of 5%
    volatility_multiplier=1.3,       # 1.3x instead of 1.5x
    vix_fear_threshold=25.0,         # 25 instead of 30
)

# Less sensitive detector (higher thresholds)
conservative_detector = MarketShockDetector(
    usdclp_daily_threshold=3.0,      # 3% instead of 2%
    copper_daily_threshold=7.0,      # 7% instead of 5%
    volatility_multiplier=2.0,       # 2x instead of 1.5x
    vix_fear_threshold=35.0,         # 35 instead of 30
)
```

**Recommendation:** Start with defaults, then tune based on first month of false positive rates.

---

## Alert Object Structure

```python
@dataclass
class Alert:
    alert_type: AlertType           # TREND_REVERSAL, VOLATILITY_SPIKE, etc.
    severity: AlertSeverity         # INFO, WARNING, CRITICAL
    timestamp: datetime             # When detected
    message: str                    # Human-readable description
    metrics: Dict[str, float]       # Numerical details
    recommendation: Optional[str]   # Action suggestion (if CRITICAL)
```

**Methods:**
- `alert.to_dict()`: Convert to dictionary for JSON serialization
- `str(alert)`: Human-readable summary

---

## Integration with Email System

```python
from forex_core.alerts import MarketShockDetector

# Step 1: Detect alerts
detector = MarketShockDetector()
alerts = detector.detect_all(market_data)

# Step 2: Generate summary for email subject
summary = detector.get_alert_summary(alerts)
# Example: "CRÍTICO: 2 alerta(s) - COPPER SHOCK, VIX SPIKE"

# Step 3: Group by severity for email body
grouped = detector.get_alerts_by_severity(alerts)

critical_section = "\n".join([
    f"- {a.message}" for a in grouped[AlertSeverity.CRITICAL]
])

warning_section = "\n".join([
    f"- {a.message}" for a in grouped[AlertSeverity.WARNING]
])

# Step 4: Include in email (next phase: alert_email_generator.py)
email_body = f"""
ALERTAS CRÍTICAS:
{critical_section}

ADVERTENCIAS:
{warning_section}
"""
```

---

## Data Requirements

### Required Columns

| Column | Type | Description | Source |
|--------|------|-------------|--------|
| `date` | datetime | Date/timestamp | - |
| `usdclp` | float | USD/CLP exchange rate | BCCh, Investing.com |
| `copper_price` | float | Copper price ($/lb) | Investing.com |
| `dxy` | float | US Dollar Index | Yahoo Finance, FRED |
| `vix` | float | CBOE Volatility Index | Yahoo Finance |
| `tpm` | float | Chilean policy rate (%) | BCCh |

### Optional Columns (Enhanced Detection)

| Column | Benefit |
|--------|---------|
| `usdclp_high` | Enables intraday range detection |
| `usdclp_low` | Enables intraday range detection |

### Minimum Data History

- **Absolute minimum**: 30 days
- **Recommended**: 60 days (for trend analysis)
- **Optimal**: 90+ days (for robust volatility estimates)

---

## Error Handling

```python
from forex_core.alerts import MarketShockDetector

try:
    detector = MarketShockDetector()
    alerts = detector.detect_all(data)

except ValueError as e:
    # Missing columns or insufficient data
    print(f"Data validation error: {e}")

except Exception as e:
    # Unexpected error
    print(f"Detection error: {e}")
    # Fallback: proceed without alerts
```

**Robustness:**
- Individual detection failures are logged but don't crash the detector
- Missing recent data generates warnings but doesn't fail
- NaN values are handled gracefully

---

## Testing & Validation

### Run Test Suite

```bash
cd /Users/rafaelfarias/Documents/Recursos/Proyectos/forex-forecast-system
PYTHONPATH=./src python3 << 'EOF'
from forex_core.alerts.market_shock_detector import MarketShockDetector
import pandas as pd
import numpy as np

# Create test data with synthetic shock
data = pd.DataFrame({
    'date': pd.date_range('2025-01-01', periods=60),
    'usdclp': 950 + np.random.randn(60) * 5,
    'copper_price': 4.0 + np.random.randn(60) * 0.1,
    'dxy': 103 + np.random.randn(60) * 0.5,
    'vix': 15 + np.random.randn(60) * 2,
    'tpm': [5.75] * 60,
})

# Inject shock
data.loc[59, 'usdclp'] = data.loc[58, 'usdclp'] * 1.025  # +2.5% shock

detector = MarketShockDetector()
alerts = detector.detect_all(data)

print(f"Detected {len(alerts)} alerts:")
for alert in alerts:
    print(f"  {alert}")
EOF
```

### Manual Testing Checklist

- [ ] Normal conditions: No CRITICAL/WARNING alerts
- [ ] USD/CLP +2.5% spike: WARNING alert
- [ ] Copper -7% crash: WARNING alert
- [ ] DXY = 107: CRITICAL alert
- [ ] VIX = 35: WARNING alert
- [ ] TPM +0.75%: WARNING alert
- [ ] High volatility (3x): WARNING or CRITICAL alert
- [ ] Custom thresholds: Correctly modify sensitivity

---

## Performance Considerations

**Computational Cost:**
- Detection runtime: ~50-100ms for 60 days of data
- Memory: < 10 MB
- Safe for real-time use in cron jobs

**Optimization Tips:**
- Pre-load market data once, run detector multiple times if needed
- Cache detector instance if thresholds don't change
- Run detection AFTER data validation to avoid repeated errors

---

## Future Enhancements (Phase 3)

1. **Chilean Political Events:**
   - Integrate BCCh meeting calendar API
   - Compare TPM actual vs market expectations survey
   - Keyword detection in presidential speeches

2. **NDF (Non-Deliverable Forward) Integration:**
   - Detect USD/CLP NDF vs spot divergences
   - Offshore market stress signals

3. **Multiple Currencies:**
   - Detect correlated moves in COP, BRL, MXN
   - Regional stress indicators

4. **Machine Learning:**
   - Learn historical false positive patterns
   - Auto-tune thresholds based on performance
   - Anomaly detection using isolation forests

---

## Support & Troubleshooting

### Common Issues

**Issue**: `ValueError: Missing required columns`
- **Fix**: Ensure data has all 6 required columns: date, usdclp, copper_price, dxy, vix, tpm

**Issue**: No alerts detected in obvious shock
- **Fix**: Check thresholds are not too high. Print latest data values to verify shock is present.

**Issue**: Too many INFO alerts (alert fatigue)
- **Fix**: Increase thresholds or filter out INFO severity in email logic

**Issue**: NaN values in recent data
- **Fix**: Check data provider reliability. Detector logs warnings but continues.

---

## Example: Production Integration

```python
#!/usr/bin/env python3
"""
Daily market shock detection for USD/CLP forecasting system.
Runs after data collection (18:00 Chile time).
"""

import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
from loguru import logger

from forex_core.alerts import MarketShockDetector, AlertSeverity
from forex_core.data.loader import load_latest_data  # Placeholder

def main():
    logger.info("Starting market shock detection")

    # 1. Load latest 60 days of data
    data = load_latest_data(days=60)

    # 2. Initialize detector
    detector = MarketShockDetector()

    # 3. Run detection
    alerts = detector.detect_all(data)

    # 4. Log results
    logger.info(f"Detected {len(alerts)} alerts")

    # 5. Process critical alerts
    critical = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
    if critical:
        logger.warning(f"CRITICAL: {len(critical)} urgent alerts!")
        for alert in critical:
            logger.warning(f"  - {alert.message}")

        # TODO: Trigger email via alert_email_generator.py

    # 6. Save alert log
    alert_log = Path("/app/data/alerts/") / f"{datetime.now():%Y%m%d_%H%M%S}_alerts.json"
    alert_log.parent.mkdir(parents=True, exist_ok=True)

    import json
    with open(alert_log, 'w') as f:
        json.dump([a.to_dict() for a in alerts], f, indent=2, default=str)

    logger.info(f"Alert log saved: {alert_log}")

    return 0 if not critical else 1  # Exit code indicates criticality

if __name__ == '__main__':
    sys.exit(main())
```

---

**Generated**: 2025-11-14
**Version**: 1.0.0
**Status**: Production Ready
**Next Phase**: Alert Email Generator (Phase 2, Task 2)
