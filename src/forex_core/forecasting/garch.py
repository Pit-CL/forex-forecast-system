"""
GARCH (Generalized AutoRegressive Conditional Heteroskedasticity) models.

GARCH models are used to forecast time-varying volatility in financial
time series. Unlike ARIMA which forecasts the mean, GARCH models the
conditional variance (volatility clustering).

Key features:
- GARCH(1,1) is the industry standard (Bollerslev, 1986)
- Captures volatility clustering (high volatility follows high volatility)
- Used for confidence intervals and risk metrics (VaR, CVaR)

Model specification:
    r_t = sigma_t * epsilon_t
    sigma_t^2 = omega + alpha * r_{t-1}^2 + beta * sigma_{t-1}^2

Where:
- r_t: return at time t
- sigma_t: conditional volatility (time-varying)
- epsilon_t: i.i.d. standard normal innovations
- omega: constant term (long-run volatility)
- alpha: ARCH term (reaction to shocks)
- beta: GARCH term (persistence of volatility)
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd
from arch import arch_model
from arch.univariate.base import ARCHModelResult


def fit_garch(
    log_returns: pd.Series,
    p: int = 1,
    q: int = 1,
    mean: str = "Zero",
    dist: str = "normal"
) -> ARCHModelResult:
    """
    Fit a GARCH model to log returns.

    This function fits a GARCH(p, q) model to estimate time-varying volatility.
    The default GARCH(1,1) is widely used in practice and often sufficient.

    Args:
        log_returns: Log returns series (NOT prices).
        p: GARCH order (persistence term, default 1).
        q: ARCH order (shock term, default 1).
        mean: Mean model specification (default "Zero" for demeaned returns).
              Options: "Zero", "Constant", "AR".
        dist: Error distribution (default "normal").
              Options: "normal", "t", "skewt", "ged".

    Returns:
        Fitted ARCHModelResult object.

    Example:
        >>> log_returns = np.log(prices).diff().dropna() * 100  # Scale to %
        >>> garch_model = fit_garch(log_returns)
        >>> print(garch_model.summary())
        >>> print(f"Omega: {garch_model.params['omega']:.6f}")
        >>> print(f"Alpha: {garch_model.params['alpha[1]']:.4f}")
        >>> print(f"Beta:  {garch_model.params['beta[1]']:.4f}")

    Notes:
        - Input should be scaled (e.g., multiply by 100 for percentage returns)
        - GARCH(1,1) has 3 parameters: omega, alpha[1], beta[1]
        - Stationarity requires alpha + beta < 1
        - Use dist="t" for heavy-tailed returns (more robust)
        - Fitting uses maximum likelihood estimation (MLE)

    Interpretation:
        - alpha: Sensitivity to recent shocks (news impact)
        - beta: Persistence of volatility (memory)
        - alpha + beta: Total persistence (close to 1 = high persistence)
        - omega / (1 - alpha - beta): Long-run variance

    Common issues:
        - Convergence failures: Try different starting values or dist="t"
        - Non-stationarity: alpha + beta >= 1 (unstable forecasts)
        - Negative omega: Usually indicates model misspecification
    """
    # Scale returns to percentage (arch package convention)
    scaled_returns = log_returns * 100

    # Fit GARCH model
    model = arch_model(
        scaled_returns,
        p=p,
        q=q,
        mean=mean,
        dist=dist
    )
    result = model.fit(disp="off")

    return result


def forecast_garch_volatility(
    garch_model: ARCHModelResult,
    horizon: int
) -> np.ndarray:
    """
    Forecast conditional volatility for multiple periods ahead.

    This function generates h-step ahead volatility forecasts from a fitted
    GARCH model. Volatility forecasts are used to construct confidence
    intervals for price forecasts.

    Args:
        garch_model: Fitted GARCH model from fit_garch().
        horizon: Number of steps to forecast ahead.

    Returns:
        Array of forecast standard deviations (length = horizon).
        Values are unscaled (i.e., if input was scaled by 100, output
        is automatically divided by 100).

    Example:
        >>> garch_model = fit_garch(log_returns * 100)
        >>> volatility = forecast_garch_volatility(garch_model, horizon=7)
        >>> print(f"7-day volatility: {volatility[-1]:.4f}")
        >>> # Use for confidence intervals
        >>> ci_95_low = forecast_mean - 1.96 * volatility
        >>> ci_95_high = forecast_mean + 1.96 * volatility

    Notes:
        - Volatility forecasts converge to long-run volatility as horizon grows
        - Multi-step forecasts use recursive formula:
          sigma^2(t+h) = omega + (alpha + beta) * sigma^2(t+h-1)
        - Output is standard deviation (sqrt of variance)
        - Automatically unscales if input was scaled (e.g., / 100)

    Confidence interval construction:
        - 68% CI: mean +/- 1.0 * sigma
        - 80% CI: mean +/- 1.2816 * sigma
        - 90% CI: mean +/- 1.645 * sigma
        - 95% CI: mean +/- 1.96 * sigma
        - 99% CI: mean +/- 2.576 * sigma

    Limitations:
        - Assumes normality (use dist="t" in fit_garch for fat tails)
        - Forecast uncertainty grows with horizon
        - Does not capture volatility regime changes
        - Consider using realized volatility for very short horizons (1-3 days)
    """
    # Forecast variance
    forecast_result = garch_model.forecast(horizon=horizon)
    variance = forecast_result.variance.values[-1]  # Last row = h-step forecasts

    # Convert to standard deviation and unscale
    sigma = np.sqrt(variance) / 100

    return sigma


def calculate_garch_confidence_intervals(
    mean_forecast: np.ndarray,
    volatility: np.ndarray,
    confidence_levels: list[float] = [0.80, 0.95]
) -> dict[str, Tuple[np.ndarray, np.ndarray]]:
    """
    Calculate confidence intervals for price forecasts using GARCH volatility.

    Args:
        mean_forecast: Array of point forecasts (mean predictions).
        volatility: Array of forecast volatilities from GARCH.
        confidence_levels: List of confidence levels (e.g., [0.80, 0.95]).

    Returns:
        Dictionary mapping confidence level to (lower, upper) bound arrays.

    Example:
        >>> mean = np.array([950, 952, 955])
        >>> vol = np.array([5.0, 5.2, 5.5])
        >>> ci = calculate_garch_confidence_intervals(mean, vol)
        >>> print(f"95% CI: [{ci[0.95][0][-1]:.2f}, {ci[0.95][1][-1]:.2f}]")
    """
    from scipy.stats import norm

    cis = {}
    for level in confidence_levels:
        z_score = norm.ppf((1 + level) / 2)
        lower = mean_forecast - z_score * volatility
        upper = mean_forecast + z_score * volatility
        cis[level] = (lower, upper)

    return cis


__all__ = [
    "fit_garch",
    "forecast_garch_volatility",
    "calculate_garch_confidence_intervals",
]
