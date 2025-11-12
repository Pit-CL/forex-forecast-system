"""
VAR (Vector AutoRegression) multivariate forecasting models.

VAR models extend univariate AR models to multiple time series, capturing
interdependencies and Granger causality between variables. For USD/CLP
forecasting, VAR models relationships between:
- USD/CLP exchange rate
- Copper prices (Chile's main export)
- DXY (US Dollar Index)
- TPM (Chilean policy rate)

Model specification:
    Y_t = c + A_1 * Y_{t-1} + ... + A_p * Y_{t-p} + e_t

Where:
- Y_t: Vector of variables at time t
- A_i: Coefficient matrices
- p: Lag order
- e_t: Vector of innovations (correlated across variables)

Key features:
- Captures lead-lag relationships between variables
- Tests for Granger causality
- Generates impulse response functions
- Provides multivariate confidence intervals
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd
from statsmodels.tsa.vector_ar.var_model import VAR, VARResults


def fit_var(
    data: pd.DataFrame,
    maxlags: int | None = None,
    ic: str = "aic"
) -> VARResults:
    """
    Fit a VAR model to multivariate time series.

    This function estimates a VAR model with automatic lag order selection
    (if maxlags is specified) or a fixed lag order. The model captures
    interdependencies between multiple time series.

    Args:
        data: DataFrame with each column as a time series variable.
              All series must have the same length and be stationary
              (or use percentage changes/log returns).
        maxlags: Maximum lag order to consider. If provided, optimal lag
                 is selected via information criterion. If None, uses
                 VAR(1) by default.
        ic: Information criterion for lag selection (default "aic").
            Options: "aic", "bic", "hqic", "fpe".

    Returns:
        Fitted VARResults object.

    Example:
        >>> # Prepare multivariate data
        >>> data = pd.DataFrame({
        ...     'usdclp': usdclp_series.pct_change(),
        ...     'copper': copper_series.pct_change(),
        ...     'dxy': dxy_series.pct_change(),
        ...     'tpm': tpm_series.diff()
        ... }).dropna()
        >>> # Fit VAR model
        >>> var_model = fit_var(data, maxlags=5)
        >>> print(var_model.summary())
        >>> print(f"Selected lag order: {var_model.k_ar}")

    Notes:
        - All series must be stationary (use ADF test to check)
        - Typically use percentage changes or log returns
        - VAR requires significant data (rule of thumb: N > 8*k*p where
          k = number of variables, p = lag order)
        - BIC tends to select smaller lag orders than AIC
        - Check residual autocorrelation with Portmanteau test

    Granger causality testing:
        >>> var_model.test_causality('usdclp', ['copper', 'dxy'])

    Impulse response functions:
        >>> irf = var_model.irf(periods=10)
        >>> irf.plot()

    Forecast error variance decomposition:
        >>> fevd = var_model.fevd(periods=10)
        >>> fevd.summary()

    Common issues:
        - Non-stationarity: Difference or use percentage changes
        - Insufficient data: Reduce maxlags or number of variables
        - High correlation: Consider PCA or variable selection
        - Structural breaks: Use rolling VAR or regime-switching models
    """
    model = VAR(data)

    if maxlags is not None:
        # Automatic lag selection
        result = model.fit(maxlags=maxlags, ic=ic)
    else:
        # Default to VAR(1)
        result = model.fit(lags=1)

    return result


def forecast_var(
    var_model: VARResults,
    steps: int,
    last_values: pd.Series | None = None
) -> pd.DataFrame:
    """
    Generate multi-step ahead forecasts from fitted VAR model.

    This function produces h-step ahead forecasts for all variables in
    the VAR system. Forecasts account for cross-variable dependencies.

    Args:
        var_model: Fitted VAR model from fit_var().
        steps: Number of steps to forecast ahead.
        last_values: Optional last observed values for each variable.
                     If None, uses the last values from model estimation.

    Returns:
        DataFrame of forecasts with shape (steps, n_variables).
        Columns match input variable names.

    Example:
        >>> var_model = fit_var(data, maxlags=2)
        >>> forecast_df = forecast_var(var_model, steps=7)
        >>> print(forecast_df['usdclp'])  # USD/CLP forecasts

    Notes:
        - Multi-step forecasts use recursive prediction
        - Forecast uncertainty grows with horizon
        - All variables are forecast simultaneously (respecting correlations)
        - Returns are in same units as input (e.g., pct changes)

    Converting VAR forecasts to price levels:
        >>> # If VAR was fit on percentage changes
        >>> last_price = usdclp_series.iloc[-1]
        >>> price_path = [last_price]
        >>> for pct_change in forecast_df['usdclp']:
        ...     price_path.append(price_path[-1] * (1 + pct_change))
    """
    if last_values is None:
        # Use last observations from model
        last_obs = var_model.endog[-var_model.k_ar:]
    else:
        # Use provided last values (must have k_ar observations)
        last_obs = last_values.values[-var_model.k_ar:]

    # Generate forecast
    forecast = var_model.forecast(last_obs, steps=steps)

    # Convert to DataFrame
    forecast_df = pd.DataFrame(
        forecast,
        columns=var_model.names
    )

    return forecast_df


def var_price_reconstruction(
    forecast_df: pd.DataFrame,
    target_col: str,
    last_price: float
) -> np.ndarray:
    """
    Reconstruct price levels from VAR percentage change forecasts.

    Args:
        forecast_df: DataFrame of VAR forecasts (percentage changes).
        target_col: Name of target variable column.
        last_price: Last observed price level.

    Returns:
        Array of forecast prices.

    Example:
        >>> forecast_df = forecast_var(var_model, steps=7)
        >>> prices = var_price_reconstruction(
        ...     forecast_df,
        ...     target_col='usdclp',
        ...     last_price=950.0
        ... )
        >>> print(f"7-day forecast: {prices[-1]:.2f}")

    Notes:
        - Assumes forecast_df contains percentage changes (returns)
        - Uses multiplicative compounding: price(t+1) = price(t) * (1 + return)
        - Alternative: use additive for log returns: price = exp(log_price + log_return)
    """
    price_path = []
    current_price = last_price

    for pct_change in forecast_df[target_col]:
        current_price = current_price * (1 + pct_change)
        price_path.append(float(current_price))

    return np.array(price_path)


__all__ = [
    "fit_var",
    "forecast_var",
    "var_price_reconstruction",
]
