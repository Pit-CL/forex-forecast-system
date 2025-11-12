# Forecasting Module - Quick Start Guide

## Overview

The `forex_core.forecasting` module provides a unified forecasting engine supporting multiple statistical models and forecast horizons.

## Basic Usage

### 7-Day Forecast

```python
from forex_core.data.loader import load_data
from forex_core.config.base import ForecastConfig
from forex_core.forecasting.models import ForecastEngine

# Load data
bundle = load_data()

# Configure models
config = ForecastConfig(
    enable_arima=True,
    enable_var=True,
    enable_rf=False,
    ensemble_window=30
)

# Create engine for 7-day forecast
engine = ForecastEngine(config, horizon="daily", steps=7)

# Generate forecast
forecast, artifacts = engine.forecast(bundle)

# Access results
print(f"7-day forecast: {forecast.series[-1].mean:.2f} CLP/USD")
print(f"95% CI: [{forecast.series[-1].ci95_low:.2f}, {forecast.series[-1].ci95_high:.2f}]")
print(f"Ensemble weights: {artifacts.weights}")
```

### 12-Month Forecast

```python
# Same setup, different horizon
engine_12m = ForecastEngine(config, horizon="monthly", steps=12)
forecast_12m, artifacts_12m = engine_12m.forecast(bundle)

print(f"12-month forecast: {forecast_12m.series[-1].mean:.2f} CLP/USD")
```

## Individual Models

### ARIMA + GARCH

```python
from forex_core.forecasting.arima import auto_select_arima_order, fit_arima, forecast_arima
from forex_core.forecasting.garch import fit_garch, forecast_garch_volatility
import numpy as np

# Prepare data
prices = bundle.usdclp_series
log_returns = np.log(prices).diff().dropna()

# Fit ARIMA
order = auto_select_arima_order(log_returns, max_p=2, max_q=2)
arima_model = fit_arima(log_returns, order)

# Forecast prices
price_forecast, return_forecast = forecast_arima(
    arima_model,
    steps=7,
    last_price=prices.iloc[-1]
)

# Fit GARCH for volatility
garch_model = fit_garch(log_returns, p=1, q=1)
volatility = forecast_garch_volatility(garch_model, horizon=7)

print(f"ARIMA order: {order}")
print(f"7-day price forecast: {price_forecast[-1]:.2f}")
print(f"7-day volatility: {volatility[-1]:.4f}")
```

### VAR (Multivariate)

```python
from forex_core.forecasting.var import fit_var, forecast_var, var_price_reconstruction
import pandas as pd

# Prepare multivariate data
data = pd.DataFrame({
    'usdclp': bundle.usdclp_series.pct_change(),
    'copper': bundle.copper_series.pct_change(),
    'dxy': bundle.dxy_series.pct_change(),
    'tpm': bundle.tpm_series.diff()
}).dropna()

# Fit VAR
var_model = fit_var(data, maxlags=5, ic='aic')
print(f"Selected lag order: {var_model.k_ar}")

# Forecast
forecast_df = forecast_var(var_model, steps=7)

# Reconstruct prices
usdclp_prices = var_price_reconstruction(
    forecast_df,
    target_col='usdclp',
    last_price=bundle.usdclp_series.iloc[-1]
)

print(f"VAR 7-day forecast: {usdclp_prices[-1]:.2f}")
```

## Technical Analysis

```python
from forex_core.analysis.technical import compute_technicals, calculate_rsi, calculate_macd

# Compute all indicators
technicals = compute_technicals(bundle.usdclp_series)

print(f"Current price: {technicals['latest_close']:.2f}")
print(f"RSI(14): {technicals['rsi_14']:.2f}")
print(f"MACD: {technicals['macd']:.4f}")
print(f"Support: {technicals['support']:.2f}")
print(f"Resistance: {technicals['resistance']:.2f}")
print(f"30-day volatility: {technicals['hist_vol_30']:.2%}")

# Individual indicators
rsi = calculate_rsi(bundle.usdclp_series, period=14)
macd, signal = calculate_macd(bundle.usdclp_series)

print(f"Latest RSI: {rsi.iloc[-1]:.2f}")
print(f"MACD histogram: {(macd - signal).iloc[-1]:.4f}")
```

## Fundamental Analysis

```python
from forex_core.analysis.fundamental import extract_quant_factors, build_quant_factors

# Extract fundamental factors
factors = extract_quant_factors(bundle)

# Access individual factors
print(f"USD/CLP: {factors['usdclp'].value:.2f} (trend: {factors['usdclp'].trend:+.2f}%)")
print(f"Copper: ${factors['cobre'].value:.2f}/lb (trend: {factors['cobre'].trend:+.2f}%)")
print(f"TPM: {factors['tpm'].value:.2f}%")

# Create DataFrame for reporting
df = build_quant_factors(factors)
print(df.to_string())
```

## Risk Regime Analysis

```python
from forex_core.analysis.macro import compute_risk_gauge

# Compute risk regime
gauge = compute_risk_gauge(bundle)

print(f"Risk regime: {gauge.regime}")
print(f"DXY change: {gauge.dxy_change:+.2f}%")
print(f"VIX change: {gauge.vix_change:+.2f}%")
print(f"EEM change: {gauge.eem_change:+.2f}%")

# Interpret
if gauge.regime == "Risk-on":
    print("Favorable for CLP (EM currencies)")
elif gauge.regime == "Risk-off":
    print("Unfavorable for CLP (safe-haven demand)")
else:
    print("Mixed signals")
```

## Ensemble Methods

```python
from forex_core.forecasting.ensemble import ModelResult, compute_weights, combine_forecasts

# Suppose you have individual model results
results = {
    "arima_garch": ModelResult(
        name="arima_garch",
        package=arima_forecast,
        rmse=3.45,
        mape=0.36,
        extras={"order_tuple": (1, 0, 1)}
    ),
    "var": ModelResult(
        name="var",
        package=var_forecast,
        rmse=4.21,
        mape=0.42,
        extras={"lag_order": 2}
    )
}

# Compute optimal weights
weights = compute_weights(results)
print(f"Weights: {weights}")

# Combine forecasts
ensemble = combine_forecasts(results, weights, steps=7)
print(f"Ensemble methodology: {ensemble.methodology}")
print(f"Final forecast: {ensemble.series[-1].mean:.2f}")
```

## Model Evaluation

```python
from forex_core.forecasting.metrics import calculate_rmse, calculate_mape, calculate_mae
import numpy as np

# Actual vs predicted
actual = np.array([950, 952, 955, 960])
predicted = np.array([951, 953, 954, 958])

# Calculate metrics
rmse = calculate_rmse(actual, predicted)
mae = calculate_mae(actual, predicted)
mape = calculate_mape(actual, predicted)

print(f"RMSE: {rmse:.2f} CLP")
print(f"MAE: {mae:.2f} CLP")
print(f"MAPE: {mape:.2f}%")

# Use window for recent performance
rmse_recent = calculate_rmse(actual, predicted, window=2)
print(f"RMSE (last 2): {rmse_recent:.2f} CLP")
```

## Confidence Intervals

```python
# Access confidence intervals from forecast
for i, point in enumerate(forecast.series, 1):
    print(f"Day {i}:")
    print(f"  Mean: {point.mean:.2f}")
    print(f"  80% CI: [{point.ci80_low:.2f}, {point.ci80_high:.2f}]")
    print(f"  95% CI: [{point.ci95_low:.2f}, {point.ci95_high:.2f}]")
    print(f"  Std Dev: {point.std_dev:.2f}")
```

## Export Forecast

```python
import pandas as pd

# Convert forecast to DataFrame
forecast_df = pd.DataFrame([
    {
        'date': point.date,
        'mean': point.mean,
        'ci80_low': point.ci80_low,
        'ci80_high': point.ci80_high,
        'ci95_low': point.ci95_low,
        'ci95_high': point.ci95_high,
        'std_dev': point.std_dev
    }
    for point in forecast.series
])

# Save to CSV
forecast_df.to_csv('forecast_7d.csv', index=False)

# Save to JSON
import json
forecast_dict = {
    'generated_at': datetime.now().isoformat(),
    'methodology': forecast.methodology,
    'horizon': 'daily',
    'steps': 7,
    'forecasts': forecast_df.to_dict('records'),
    'ensemble_weights': artifacts.weights,
    'metrics': artifacts.component_metrics
}

with open('forecast_7d.json', 'w') as f:
    json.dump(forecast_dict, f, indent=2, default=str)
```

## Error Handling

```python
try:
    forecast, artifacts = engine.forecast(bundle)
except RuntimeError as e:
    if "No models executed successfully" in str(e):
        print("All models failed. Check data quality.")
    elif "Insufficient data" in str(e):
        print("Need more historical data.")
    else:
        print(f"Forecast error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()
```

## Advanced: Custom Model Configuration

```python
from forex_core.config.base import ForecastConfig

# Custom configuration
config = ForecastConfig(
    # Model selection
    enable_arima=True,
    enable_var=True,
    enable_rf=True,

    # ARIMA parameters
    arima_max_p=3,
    arima_max_q=3,

    # GARCH parameters
    garch_p=1,
    garch_q=1,
    garch_dist='t',  # Student-t for fat tails

    # VAR parameters
    var_max_lags=5,
    var_ic='bic',  # Use BIC instead of AIC

    # Random Forest parameters
    rf_n_estimators=500,
    rf_max_depth=12,
    rf_random_state=42,

    # Ensemble parameters
    ensemble_window=30,
    ensemble_method='inverse_rmse',

    # Logging
    metrics_log_path='logs/forecast_metrics.jsonl'
)

engine = ForecastEngine(config, horizon="daily", steps=7)
forecast, artifacts = engine.forecast(bundle)
```

## Tips and Best Practices

1. **Check Data Quality**
   - Ensure sufficient history (minimum 50 data points)
   - Check for missing values
   - Verify date continuity

2. **Model Selection**
   - ARIMA: Best for univariate, short-term forecasts
   - VAR: Best when variables have clear relationships
   - Random Forest: Best with rich feature set

3. **Horizon Selection**
   - Daily: 1-30 days (optimal: 7 days)
   - Monthly: 3-24 months (optimal: 12 months)
   - Longer horizons have wider confidence intervals

4. **Ensemble Benefits**
   - Usually more robust than individual models
   - Reduces variance through diversification
   - Check if ensemble beats best individual model

5. **Validation**
   - Always backtest on held-out data
   - Use rolling window cross-validation
   - Track forecast accuracy over time

6. **Performance**
   - Disable unused models to speed up
   - Cache data loading if forecasting frequently
   - Consider parallel model fitting for production

## Common Issues and Solutions

### Issue: "Insufficient data for VAR"
**Solution:** Ensure at least 10 observations after differencing. For monthly data, need 1+ years of history.

### Issue: "ARIMA convergence failure"
**Solution:** Check for extreme outliers, try differencing the series, or reduce max_p/max_q.

### Issue: "GARCH alpha + beta >= 1"
**Solution:** Non-stationary volatility. Check for structural breaks, try different time period, or use different volatility model.

### Issue: "Ensemble weights heavily favor one model"
**Solution:** Normal if one model is clearly better. Consider equal weighting if suspicious of overfitting.

### Issue: "Wide confidence intervals"
**Solution:** Expected for longer horizons. Consider shortening forecast horizon or using more informative priors.

## Resources

- **ARIMA:** Box & Jenkins (1970) "Time Series Analysis"
- **GARCH:** Bollerslev (1986) "Generalized Autoregressive Conditional Heteroskedasticity"
- **VAR:** Sims (1980) "Macroeconomics and Reality"
- **Ensemble:** Bates & Granger (1969) "The Combination of Forecasts"

## Support

For issues or questions:
1. Check migration report: `/docs/MIGRATION_REPORT.md`
2. Review module docstrings
3. Open GitHub issue with minimal reproducible example
