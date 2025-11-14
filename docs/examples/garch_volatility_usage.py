"""
GARCH/EGARCH Volatility Model - Usage Examples

This script demonstrates how to use the volatility models in the
USD/CLP forecasting system for generating confidence intervals.

Examples:
1. Basic usage with residuals from a forecaster
2. Horizon-specific model selection
3. Volatility regime detection
4. Integration with ensemble system
5. Model persistence
"""

import sys
from pathlib import Path
import numpy as np
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from forex_core.models.garch_volatility import (
    GARCHVolatility,
    GARCHConfig,
    VolatilityRegime
)

print("=" * 70)
print("GARCH/EGARCH Volatility Model - Usage Examples")
print("=" * 70)

# =============================================================================
# Example 1: Basic Usage with 7-day Forecast
# =============================================================================
print("\n" + "=" * 70)
print("Example 1: Basic 7-day Volatility Forecast")
print("=" * 70)

# Simulate residuals from XGBoost/SARIMAX forecaster
# In production, these come from: actual_values - predicted_values
np.random.seed(42)
n_days = 252  # 1 year of historical data

# Generate realistic residuals with volatility clustering
residuals = []
vol = 0.5  # Initial volatility
for _ in range(n_days):
    # GARCH effect: volatility clusters
    vol = np.sqrt(0.05 + 0.1 * (residuals[-1]**2 if residuals else 0.25) + 0.85 * vol**2)
    residuals.append(vol * np.random.randn())

residuals = np.array(residuals)

print(f"\nHistorical residuals (last 252 days):")
print(f"  Mean: {np.mean(residuals):.4f}")
print(f"  Std Dev: {np.std(residuals):.4f}")
print(f"  Min: {np.min(residuals):.4f}")
print(f"  Max: {np.max(residuals):.4f}")

# Create 7-day volatility model (automatically uses EGARCH)
vol_model_7d = GARCHVolatility(horizon_days=7)

print(f"\n7-day model configuration:")
print(f"  Model type: {vol_model_7d.config.model_type}")
print(f"  Order: GARCH({vol_model_7d.config.p}, {vol_model_7d.config.q})")

# Fit the model on residuals
print("\nFitting EGARCH model...")
vol_model_7d.fit(residuals, show_warning=False)

# Generate volatility forecast
point_forecast = 950.0  # USD/CLP point forecast from ensemble
print(f"\nPoint forecast: {point_forecast:.2f} CLP")

vol_forecast = vol_model_7d.forecast_volatility(
    point_forecast=point_forecast,
    steps=7
)

print(f"\nVolatility forecast:")
print(f"  Volatility (σ): {vol_forecast.volatility:.4f} CLP")
print(f"  Regime: {vol_forecast.regime.value.upper()}")
print(f"  Historical mean: {vol_forecast.historical_mean_vol:.4f}")

print(f"\nConfidence intervals:")
print(f"  68% CI (±1σ): [{vol_forecast.confidence_intervals['1sigma'][0]:.2f}, "
      f"{vol_forecast.confidence_intervals['1sigma'][1]:.2f}]")
print(f"  95% CI (±2σ): [{vol_forecast.confidence_intervals['2sigma'][0]:.2f}, "
      f"{vol_forecast.confidence_intervals['2sigma'][1]:.2f}]")
print(f"  99.7% CI (±3σ): [{vol_forecast.confidence_intervals['3sigma'][0]:.2f}, "
      f"{vol_forecast.confidence_intervals['3sigma'][1]:.2f}]")

# =============================================================================
# Example 2: Horizon-Specific Models
# =============================================================================
print("\n" + "=" * 70)
print("Example 2: All Horizons (7d, 15d, 30d, 90d)")
print("=" * 70)

horizons = [7, 15, 30, 90]
point_forecast = 950.0

print(f"\nPoint forecast: {point_forecast:.2f} CLP")
print("\nVolatility by horizon:")

for horizon in horizons:
    # Create and fit model
    vol_model = GARCHVolatility(horizon_days=horizon)
    vol_model.fit(residuals, show_warning=False)

    # Forecast
    forecast = vol_model.forecast_volatility(
        point_forecast=point_forecast,
        steps=horizon
    )

    ci_95 = forecast.confidence_intervals['2sigma']

    print(f"\n{horizon:2d}-day ({vol_model.config.model_type}):")
    print(f"  Volatility: {forecast.volatility:.4f} CLP")
    print(f"  Regime: {forecast.regime.value}")
    print(f"  95% CI: [{ci_95[0]:.2f}, {ci_95[1]:.2f}]")
    print(f"  Width: {ci_95[1] - ci_95[0]:.2f} CLP")

# =============================================================================
# Example 3: Volatility Regime Detection
# =============================================================================
print("\n" + "=" * 70)
print("Example 3: Volatility Regime Detection")
print("=" * 70)

vol_model = GARCHVolatility(horizon_days=30)
vol_model.fit(residuals, show_warning=False)

# Test different volatility scenarios
scenarios = [
    (0.3, "Calm market (low volatility)"),
    (1.0, "Normal market conditions"),
    (2.0, "Elevated uncertainty"),
    (3.5, "Market crisis/shock")
]

print("\nRegime detection examples:")
for multiplier, description in scenarios:
    test_vol = vol_model.historical_mean_vol * multiplier
    regime = vol_model.detect_regime(test_vol)

    print(f"\n  {description}:")
    print(f"    Volatility: {test_vol:.4f} ({multiplier:.1f}x mean)")
    print(f"    Regime: {regime.value.upper()}")

    # What this means for forecasts
    forecast_with_vol = vol_model.get_confidence_intervals(
        point_forecast=950.0,
        volatility=test_vol
    )
    ci_95 = forecast_with_vol['2sigma']
    print(f"    95% CI width: {ci_95[1] - ci_95[0]:.2f} CLP")

# =============================================================================
# Example 4: Integration with Ensemble System
# =============================================================================
print("\n" + "=" * 70)
print("Example 4: Integration with Ensemble System")
print("=" * 70)

print("\nSimulated ensemble workflow:")

# Step 1: Train base forecasters (simulated)
print("\n1. Train base forecasters (XGBoost, SARIMAX)")
xgboost_predictions = np.random.randn(252) * 2 + 950
sarimax_predictions = np.random.randn(252) * 1.5 + 950
actuals = np.random.randn(252) * 2 + 950

# Step 2: Calculate residuals
xgb_residuals = actuals - xgboost_predictions
sarimax_residuals = actuals - sarimax_predictions

print(f"   XGBoost RMSE: {np.sqrt(np.mean(xgb_residuals**2)):.2f}")
print(f"   SARIMAX RMSE: {np.sqrt(np.mean(sarimax_residuals**2)):.2f}")

# Step 3: Ensemble point forecast
ensemble_weights = {'xgboost': 0.6, 'sarimax': 0.4}  # 7-day weights
xgb_forecast = 951.5
sarimax_forecast = 949.2

ensemble_forecast = (
    ensemble_weights['xgboost'] * xgb_forecast +
    ensemble_weights['sarimax'] * sarimax_forecast
)

print(f"\n2. Generate ensemble forecast")
print(f"   XGBoost: {xgb_forecast:.2f} (weight: {ensemble_weights['xgboost']})")
print(f"   SARIMAX: {sarimax_forecast:.2f} (weight: {ensemble_weights['sarimax']})")
print(f"   Ensemble: {ensemble_forecast:.2f}")

# Step 4: Fit GARCH on ensemble residuals
ensemble_predictions = (
    ensemble_weights['xgboost'] * xgboost_predictions +
    ensemble_weights['sarimax'] * sarimax_predictions
)
ensemble_residuals = actuals - ensemble_predictions

print(f"\n3. Fit GARCH on ensemble residuals")
vol_model_ensemble = GARCHVolatility(horizon_days=7)
vol_model_ensemble.fit(ensemble_residuals, show_warning=False)

# Step 5: Generate final forecast with confidence intervals
final_forecast = vol_model_ensemble.forecast_volatility(
    point_forecast=ensemble_forecast,
    steps=7
)

print(f"\n4. Final forecast with uncertainty:")
print(f"   Point forecast: {ensemble_forecast:.2f} CLP")
print(f"   Volatility: {final_forecast.volatility:.4f}")
print(f"   Regime: {final_forecast.regime.value}")
print(f"   95% CI: [{final_forecast.confidence_intervals['2sigma'][0]:.2f}, "
      f"{final_forecast.confidence_intervals['2sigma'][1]:.2f}]")

# =============================================================================
# Example 5: Model Persistence
# =============================================================================
print("\n" + "=" * 70)
print("Example 5: Model Save/Load (Persistence)")
print("=" * 70)

import tempfile

# Train a model
print("\nTraining 30-day GARCH model...")
vol_model_save = GARCHVolatility(horizon_days=30)
vol_model_save.fit(residuals, show_warning=False)

# Get diagnostics
diagnostics = vol_model_save.get_diagnostics()
print(f"\nModel diagnostics:")
print(f"  Model: {diagnostics['model_type']}{diagnostics['order']}")
print(f"  Observations: {diagnostics['n_observations']}")
print(f"  AIC: {diagnostics['fit_statistics']['aic']:.2f}")
print(f"  BIC: {diagnostics['fit_statistics']['bic']:.2f}")
print(f"  Log-likelihood: {diagnostics['fit_statistics']['loglikelihood']:.2f}")

# Save model
with tempfile.TemporaryDirectory() as tmpdir:
    save_path = Path(tmpdir) / "garch_30d"

    print(f"\nSaving model to: {save_path}")
    vol_model_save.save_model(save_path)

    # Check files created
    pkl_file = save_path.with_suffix('.pkl')
    json_file = save_path.with_suffix('.json')
    print(f"  Created: {pkl_file.name}")
    print(f"  Created: {json_file.name}")

    # Load model
    print(f"\nLoading model...")
    vol_model_load = GARCHVolatility(horizon_days=30)
    vol_model_load.load_model(save_path)

    # Verify loaded model works
    loaded_forecast = vol_model_load.forecast_volatility(
        point_forecast=950.0,
        steps=30
    )

    print(f"  Loaded model forecast: {loaded_forecast.volatility:.4f}")
    print(f"  95% CI: [{loaded_forecast.confidence_intervals['2sigma'][0]:.2f}, "
          f"{loaded_forecast.confidence_intervals['2sigma'][1]:.2f}]")

print("\n" + "=" * 70)
print("Examples Complete!")
print("=" * 70)

print("\nKey Takeaways:")
print("  1. EGARCH for short horizons (7d, 15d) - captures leverage effects")
print("  2. GARCH for long horizons (30d, 90d) - smoother volatility")
print("  3. Regime detection helps identify market conditions")
print("  4. Integrates seamlessly with ensemble forecasts")
print("  5. Models persist for reproducibility")

print("\nNext Steps:")
print("  - Integrate with XGBoost/SARIMAX forecasters")
print("  - Add to ensemble_forecaster.py")
print("  - Use volatility regime for alert system")
print("  - Generate confidence bands in forecast charts")
