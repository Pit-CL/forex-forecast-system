"""
Confidence interval adjustment for multi-horizon forecasts.

This module provides functions to adjust confidence intervals based on forecast horizon.
Statistical models tend to underestimate uncertainty for longer horizons, so we apply
empirically-derived multipliers to widen confidence intervals appropriately.

Based on recommendations from the USD/CLP forecasting expert agent.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from forex_core.config.horizon_params import get_horizon_params


def adjust_confidence_intervals(
    forecast: pd.Series,
    lower_bound: pd.Series,
    upper_bound: pd.Series,
    horizon: str,
) -> tuple[pd.Series, pd.Series]:
    """
    Adjust confidence interval bounds for a specific forecast horizon.

    Models typically underestimate forecast uncertainty for longer horizons.
    This function widens the confidence intervals using horizon-specific multipliers
    to provide more realistic uncertainty estimates.

    Args:
        forecast: Point forecast values (pandas Series with datetime index).
        lower_bound: Lower confidence bound (typically 95% CI).
        upper_bound: Upper confidence bound (typically 95% CI).
        horizon: Forecast horizon identifier ("7d", "15d", "30d", or "90d").

    Returns:
        Tuple of (adjusted_lower_bound, adjusted_upper_bound) as pandas Series.

    Example:
        >>> dates = pd.date_range("2025-01-01", periods=15)
        >>> forecast = pd.Series([950.0] * 15, index=dates)
        >>> lower = pd.Series([940.0] * 15, index=dates)
        >>> upper = pd.Series([960.0] * 15, index=dates)
        >>> adjusted_lower, adjusted_upper = adjust_confidence_intervals(
        ...     forecast, lower, upper, "15d"
        ... )
        >>> # For 15d, multiplier is 1.15, so intervals should be 15% wider
        >>> original_width = upper[0] - lower[0]  # 20.0
        >>> adjusted_width = adjusted_upper[0] - adjusted_lower[0]  # 23.0
        >>> adjusted_width / original_width
        1.15
    """
    # Get horizon-specific parameters
    params = get_horizon_params(horizon)  # type: ignore[arg-type]
    multiplier = params.confidence_multiplier

    # Calculate current interval half-width
    half_width = (upper_bound - lower_bound) / 2

    # Apply multiplier to widen intervals
    adjusted_half_width = half_width * multiplier

    # Calculate new bounds centered on forecast
    adjusted_lower = forecast - adjusted_half_width
    adjusted_upper = forecast + adjusted_half_width

    return adjusted_lower, adjusted_upper


def calculate_prediction_intervals(
    forecast: np.ndarray | pd.Series,
    residuals: np.ndarray,
    horizon: str,
    confidence_level: float = 0.95,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Calculate prediction intervals using residual-based approach with horizon adjustment.

    This function computes prediction intervals based on historical forecast residuals
    and adjusts them for the forecast horizon using the confidence multiplier.

    Args:
        forecast: Point forecast values (array or pandas Series).
        residuals: Historical forecast residuals (actual - predicted).
        horizon: Forecast horizon identifier ("7d", "15d", "30d", or "90d").
        confidence_level: Confidence level for intervals (default: 0.95 for 95% CI).

    Returns:
        Tuple of (lower_bounds, upper_bounds) as numpy arrays.

    Raises:
        ValueError: If confidence_level is not between 0 and 1.

    Example:
        >>> forecast_vals = np.array([950.0, 952.0, 955.0])
        >>> historical_residuals = np.array([1.5, -2.0, 0.5, -1.0, 2.5])
        >>> lower, upper = calculate_prediction_intervals(
        ...     forecast_vals, historical_residuals, "30d", confidence_level=0.95
        ... )
        >>> lower.shape
        (3,)
        >>> upper.shape
        (3,)
    """
    if not 0 < confidence_level < 1:
        msg = f"confidence_level must be between 0 and 1, got {confidence_level}"
        raise ValueError(msg)

    # Convert to numpy array if needed
    if isinstance(forecast, pd.Series):
        forecast_array = forecast.values
    else:
        forecast_array = np.asarray(forecast)

    # Calculate residual standard deviation
    residual_std = np.std(residuals, ddof=1)

    # Calculate z-score for the confidence level
    from scipy.stats import norm

    alpha = 1 - confidence_level
    z_score = norm.ppf(1 - alpha / 2)

    # Base interval half-width
    base_half_width = z_score * residual_std

    # Get horizon-specific multiplier
    params = get_horizon_params(horizon)  # type: ignore[arg-type]
    multiplier = params.confidence_multiplier

    # Adjusted half-width
    adjusted_half_width = base_half_width * multiplier

    # Calculate bounds
    lower_bounds = forecast_array - adjusted_half_width
    upper_bounds = forecast_array + adjusted_half_width

    return lower_bounds, upper_bounds


def get_confidence_multiplier(horizon: str) -> float:
    """
    Get the confidence interval multiplier for a specific horizon.

    This is a convenience function to retrieve just the multiplier value
    without loading all horizon parameters.

    Args:
        horizon: Forecast horizon identifier ("7d", "15d", "30d", or "90d").

    Returns:
        Confidence interval multiplier (float >= 1.0).

    Example:
        >>> get_confidence_multiplier("7d")
        1.0
        >>> get_confidence_multiplier("15d")
        1.15
        >>> get_confidence_multiplier("30d")
        1.35
        >>> get_confidence_multiplier("90d")
        1.75
    """
    params = get_horizon_params(horizon)  # type: ignore[arg-type]
    return params.confidence_multiplier


__all__ = [
    "adjust_confidence_intervals",
    "calculate_prediction_intervals",
    "get_confidence_multiplier",
]
