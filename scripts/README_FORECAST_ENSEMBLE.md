# Forecast with Ensemble - Usage Guide

## Overview

`forecast_with_ensemble.py` is the **main forecasting script** for the USD/CLP autonomous system. It orchestrates the complete workflow using the ensemble system (XGBoost + SARIMAX + GARCH).

## Quick Start

### Basic Usage

```bash
# Generate 7-day forecast (most common)
python scripts/forecast_with_ensemble.py --horizon 7

# Generate 30-day forecast
python scripts/forecast_with_ensemble.py --horizon 30

# Generate forecast without sending email
python scripts/forecast_with_ensemble.py --horizon 15 --no-email

# Verbose logging for debugging
python scripts/forecast_with_ensemble.py --horizon 7 -v
```

### First Time Setup (Training)

If no trained models exist, you must train them first:

```bash
# Train 7-day ensemble (takes 5-10 minutes)
python scripts/forecast_with_ensemble.py --horizon 7 --train -v

# Train all horizons (run each separately)
python scripts/forecast_with_ensemble.py --horizon 7 --train
python scripts/forecast_with_ensemble.py --horizon 15 --train
python scripts/forecast_with_ensemble.py --horizon 30 --train
python scripts/forecast_with_ensemble.py --horizon 90 --train
```

## Complete Workflow

The script executes 6 steps:

1. **Load and Prepare Data**
   - Loads last 180+ days of USD/CLP, copper, macro data
   - Engineers 50+ features (lags, technical indicators, macro)
   - Validates data quality

2. **Generate Forecast**
   - Loads trained ensemble from `/app/models/ensemble_Xd/`
   - Or trains new model if `--train` flag set
   - Generates predictions with confidence intervals

3. **Detect Market Shocks**
   - Runs MarketShockDetector on latest data
   - Detects 6 types of shocks:
     - USD/CLP sudden moves (>2%)
     - Volatility spikes
     - Copper shocks (>5%)
     - DXY extremes (>105 or <95)
     - VIX fear spikes (>30)
     - TPM surprises (±50bp)

4. **Save Results**
   - Saves to `/app/output/forecast_Xd.json`
   - Includes forecast, CIs, metadata, model health

5. **Send Alert Emails** (if shocks detected)
   - Generates market shock alert email
   - Saves HTML/PDF
   - Sends via email system (if configured)

6. **Send Forecast Email**
   - Calls `test_email_and_pdf.py` to generate email
   - Creates 5-page PDF report
   - Sends via unified email system

## Command-Line Arguments

### Required

- `--horizon {7,15,30,90}` - Forecast horizon in days

### Optional

- `--train` - Train new ensemble model (default: load existing)
- `--no-email` - Skip sending forecast email
- `-v, --verbose` - Enable verbose logging (DEBUG level)

## Output Files

### Forecast Results

- **JSON**: `/app/output/forecast_7d.json`
- **Charts**: `/app/output/charts/forecast_7d.png`
- **PDF Report**: `/app/reports/forecast_report_7d.pdf` (via test_email_and_pdf.py)

### Alerts (if triggered)

- **HTML**: `/app/output/alert_YYYYMMDD_HHMMSS.html`
- **PDF**: Embedded in email

## Environment Detection

The script automatically detects Docker vs Local:

- **Docker**: Uses `/app/data`, `/app/models`, `/app/output`
- **Local**: Uses project subdirectories

## Integration with Cron

### Docker Containers (Production)

Add to crontab for daily forecasts:

```cron
# Data collection (18:00 Chile = 21:00 UTC in summer)
30 20 * * 1-5 cd /app && PYTHONPATH=/app/src python scripts/collect_data.py

# 7-day forecast (18:45 Chile)
45 21 * * 1-5 cd /app && PYTHONPATH=/app/src python scripts/forecast_with_ensemble.py --horizon 7

# 15-day forecast (18:50 Chile)
50 21 * * 1-5 cd /app && PYTHONPATH=/app/src python scripts/forecast_with_ensemble.py --horizon 15

# 30-day forecast (18:55 Chile)
55 21 * * 1-5 cd /app && PYTHONPATH=/app/src python scripts/forecast_with_ensemble.py --horizon 30

# 90-day forecast (19:00 Chile)
0 22 * * 1-5 cd /app && PYTHONPATH=/app/src python scripts/forecast_with_ensemble.py --horizon 90
```

## Error Handling

The script handles errors gracefully:

### Data Issues

```
ERROR: Insufficient data: 120 days (need at least 180 days)
```
**Solution**: Verify data files in `/app/data/` or run data collection

### Missing Model

```
ERROR: No trained model found at /app/models/ensemble_7d
```
**Solution**: Run with `--train` flag to create model

### Feature Validation Failure

```
ERROR: Feature validation failed - check data quality
```
**Solution**: Check data for NaN values, run with `-v` for details

### Email Failure

```
WARNING: Forecast email failed (not critical)
```
**Impact**: Non-critical, forecast still succeeds

## Example Output

```
======================================================================
USD/CLP Ensemble Forecasting System - 7d Horizon
======================================================================
Environment: Docker
Data dir: /app/data
Models dir: /app/models
Output dir: /app/output

STEP 1/6: Loading and preparing data...
Raw data loaded: 203 rows
Features engineered: 67 columns
✓ Data prepared: 203 rows, 67 features

STEP 2/6: Generating forecast...
Loading trained ensemble from /app/models/ensemble_7d...
Model loaded successfully
Generating 7d forecast...
✓ Forecast generated: 965.65 CLP

STEP 3/6: Detecting market shocks...
Market shock detection complete:
  3 alerts (0 critical, 2 warning, 1 info)
✓ Market shock detection complete: 3 alerts

STEP 4/6: Saving results...
Results saved to /app/output/forecast_7d.json
✓ Results saved

STEP 5/6: Sending market shock alerts...
Alert email saved to /app/output/alert_20251114_210000.html

STEP 6/6: Sending forecast email...
Email script executed successfully
✓ Forecast email sent

======================================================================
✅ FORECAST WORKFLOW COMPLETED SUCCESSFULLY
======================================================================

Summary:
  Current:  $954.20 CLP
  Forecast: $965.65 CLP (+1.2%)
  95% CI:   $945 - $986
  Bias:     ALCISTA
  Volatility: MEDIA
  Alerts:   3 detected

Results: /app/output/forecast_7d.json
```

## Troubleshooting

### Issue: Script hangs during training

**Cause**: XGBoost/SARIMAX training on large dataset
**Solution**: Normal - training takes 5-10 minutes. Use `-v` to see progress.

### Issue: "DataLoader not found" warning

**Cause**: DataLoader class not implemented yet
**Impact**: Non-critical, uses fallback CSV loading
**Solution**: Implement DataLoader class or ignore warning

### Issue: Email script not found

**Cause**: `test_email_and_pdf.py` not in scripts/
**Solution**: Verify file exists or run with `--no-email`

### Issue: Permission denied

**Cause**: Script not executable
**Solution**: Run `chmod +x scripts/forecast_with_ensemble.py`

## Performance Metrics

Based on implementation plan targets:

| Horizon | Target RMSE | Target Direction Acc |
|---------|-------------|---------------------|
| 7d      | < 8 CLP     | > 60%              |
| 15d     | < 12 CLP    | > 60%              |
| 30d     | < 20 CLP    | > 60%              |
| 90d     | < 40 CLP    | > 60%              |

## Dependencies

Required Python packages:

- `numpy>=1.24.0`
- `pandas>=2.0.0`
- `xgboost>=2.0.0`
- `statsmodels>=0.14.0`
- `arch>=6.0.0` (for GARCH)
- `scikit-learn>=1.3.0`
- `loguru` (for logging)

## Next Steps

After successful forecast:

1. Check `/app/output/forecast_7d.json` for results
2. Review email for visual report
3. If alerts detected, investigate market shocks
4. Monitor model performance over time
5. Re-train weekly (Sundays) via auto_retrain_xgboost.py

## Related Scripts

- `test_email_and_pdf.py` - Email/PDF generation (called by this script)
- `auto_retrain_xgboost.py` - Weekly re-training (Phase 3)
- `auto_retrain_sarimax.py` - Monthly re-training (Phase 3)
- `collect_data.py` - Daily data collection

## Support

For issues or questions:

1. Run with `-v` for verbose logging
2. Check logs in `/app/logs/` (if configured)
3. Review implementation plan: `docs/IMPLEMENTATION_PLAN.md`
4. Contact: Code Simplifier Agent

---

**Version**: 1.0.0
**Phase**: 4 (Integration)
**Date**: 2025-11-14
**Author**: Code Simplifier Agent
