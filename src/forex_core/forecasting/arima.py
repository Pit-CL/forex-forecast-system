"""
ARIMA (AutoRegressive Integrated Moving Average) forecasting models.

ARIMA models are widely used for univariate time series forecasting. They
combine three components:
- AR (AutoRegressive): Uses past values to predict future
- I (Integrated): Differencing to achieve stationarity
- MA (Moving Average): Uses past forecast errors

This implementation includes:
- Automatic order selection via AIC (Akaike Information Criterion)
- Log-return transformation for price series
- Integration with GARCH for volatility forecasting

Statistical properties:
- Assumes linear relationships and Gaussian errors
- Requires stationary series (or differencing to achieve it)
- Performance degrades for longer horizons (forecast uncertainty grows)
"""

from __future__ import annotations

import math
from typing import Tuple

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA, ARIMAResults


def auto_select_arima_order(
    series: pd.Series,
    max_p: int = 2,
    max_q: int = 2,
    d: int = 0
) -> Tuple[int, int, int]:
    """
    Automatically select ARIMA order (p, d, q) via grid search and AIC.

    This function tests all combinations of p and q up to specified maxima,
    fits each model, and selects the order with the lowest AIC (Akaike
    Information Criterion). AIC balances goodness-of-fit and model complexity.

    AIC formula:
        AIC = 2k - 2ln(L)
        where k = number of parameters, L = likelihood

    Args:
        series: Time series to model (typically log returns).
        max_p: Maximum AR order to test (default 2).
        max_q: Maximum MA order to test (default 2).
        d: Differencing order (default 0, typically 0 for log returns).

    Returns:
        Tuple of (p, d, q) representing the best ARIMA order.

    Example:
        >>> log_returns = np.log(prices).diff().dropna()
        >>> order = auto_select_arima_order(log_returns)
        >>> print(f"Selected ARIMA{order}")

    Notes:
        - Default max_p=2, max_q=2 balances complexity and overfitting
        - Fallback to (1, 0, 1) if all models fail to fit
        - Uses try-except to handle convergence failures gracefully
        - AIC penalizes complexity: simpler models preferred given similar fit
        - Consider using BIC for stronger penalty on complexity

    Performance considerations:
        - Grid search is O(max_p * max_q) - keep limits low for speed
        - Each model fit can take 0.1-1s depending on series length
        - For production, consider caching or using pre-selected orders
        - Parallel grid search could improve performance

    Statistical warnings:
        - AIC minimization doesn't guarantee good out-of-sample performance
        - Always validate with backtesting and cross-validation
        - Check residuals for autocorrelation and heteroskedasticity
        - Consider using auto_arima from pmdarima for more robust selection
    """
    best_aic = math.inf
    best_order = (1, d, 1)  # Fallback

    for p in range(0, max_p + 1):
        for q in range(0, max_q + 1):
            order = (p, d, q)
            try:
                model = ARIMA(series, order=order).fit()
                if model.aic < best_aic:
                    best_aic = model.aic
                    best_order = order
            except Exception:
                # Skip orders that fail to converge
                continue

    return best_order


def fit_arima(series: pd.Series, order: Tuple[int, int, int]) -> ARIMAResults:
    """
    Fit an ARIMA model to a time series.

    Args:
        series: Time series to model.
        order: ARIMA order as (p, d, q).

    Returns:
        Fitted ARIMAResults object.

    Example:
        >>> order = (1, 0, 1)
        >>> model = fit_arima(log_returns, order)
        >>> print(model.summary())

    Notes:
        - Uses maximum likelihood estimation (MLE)
        - Raises exception if model fails to converge
        - Check model.aic, model.bic for information criteria
        - Inspect model.resid for residual diagnostics
    """
    model = ARIMA(series, order=order).fit()
    return model


def forecast_arima(
    model: ARIMAResults,
    steps: int,
    last_price: float
) -> Tuple[np.ndarray, pd.Series]:
    """
    Generate price forecasts from fitted ARIMA model on log returns.

    This function:
    1. Forecasts log returns for `steps` periods ahead
    2. Converts log returns back to price levels
    3. Returns both price forecasts and predicted log returns

    Price reconstruction:
        log_price(t+h) = log_price(t) + sum(log_return(t+1:t+h))
        price(t+h) = exp(log_price(t+h))

    Args:
        model: Fitted ARIMA model (on log returns).
        steps: Number of steps to forecast ahead.
        last_price: Last observed price level (for reconstruction).

    Returns:
        Tuple of:
            - price_path: Array of forecast prices (length = steps)
            - mean_returns: Series of forecast log returns (length = steps)

    Example:
        >>> model = fit_arima(log_returns, order=(1,0,1))
        >>> prices, returns = forecast_arima(model, steps=7, last_price=950.0)
        >>> print(f"7-day forecast: {prices[-1]:.2f}")

    Notes:
        - Forecast uncertainty grows with horizon (wider confidence intervals)
        - Point forecasts (mean) may revert to long-run mean for stationary series
        - Use GARCH for time-varying volatility in confidence intervals
        - Cumulative return path assumes no drift adjustment beyond ARIMA forecast

    Statistical properties:
        - Assumes log returns are stationary (check ACF/PACF)
        - Multi-step forecasts use recursive h-step ahead prediction
        - Forecast errors compound over horizon
        - Consider using bootstrap or simulation for non-normal distributions
    """
    forecast_result = model.get_forecast(steps=steps)
    mean_returns = forecast_result.predicted_mean

    # Convert log returns to price levels
    last_log_price = np.log(last_price)
    price_path = []
    cumulative = 0.0

    for idx in range(steps):
        cumulative += mean_returns.iloc[idx]
        price = np.exp(last_log_price + cumulative)
        price_path.append(float(price))

    return np.array(price_path), mean_returns


__all__ = [
    "auto_select_arima_order",
    "fit_arima",
    "forecast_arima",
]
