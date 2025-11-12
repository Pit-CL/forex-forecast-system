"""
Forecasting modules for forex time series.

This package provides statistical forecasting models and ensemble methods
for currency pair prediction, including:
- ARIMA: AutoRegressive Integrated Moving Average
- GARCH: Generalized AutoRegressive Conditional Heteroskedasticity (volatility)
- VAR: Vector AutoRegression (multivariate)
- Random Forest: Machine learning ensemble
- Ensemble: Weighted combination of models

Models are designed to work with both daily (7-day) and monthly (12-month)
forecast horizons through parameterized resampling.
"""

from .arima import fit_arima, forecast_arima, auto_select_arima_order
from .garch import fit_garch, forecast_garch_volatility
from .var import fit_var, forecast_var
from .ensemble import (
    ModelResult,
    EnsembleArtifacts,
    compute_weights,
    combine_forecasts,
)
from .models import ForecastEngine
from .metrics import calculate_rmse, calculate_mape, calculate_mae

__all__ = [
    # ARIMA
    "fit_arima",
    "forecast_arima",
    "auto_select_arima_order",
    # GARCH
    "fit_garch",
    "forecast_garch_volatility",
    # VAR
    "fit_var",
    "forecast_var",
    # Ensemble
    "ModelResult",
    "EnsembleArtifacts",
    "compute_weights",
    "combine_forecasts",
    # Engine
    "ForecastEngine",
    # Metrics
    "calculate_rmse",
    "calculate_mape",
    "calculate_mae",
]
