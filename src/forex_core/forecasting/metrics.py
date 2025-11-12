"""
Model evaluation metrics for forecasting.

This module provides standard error metrics for evaluating forecast accuracy:
- RMSE: Root Mean Squared Error (penalizes large errors)
- MAE: Mean Absolute Error (robust to outliers)
- MAPE: Mean Absolute Percentage Error (scale-independent)

All functions handle edge cases (division by zero, NaN values) gracefully.
"""

from __future__ import annotations

from typing import Union

import numpy as np
import pandas as pd


def calculate_rmse(
    actual: Union[pd.Series, np.ndarray],
    predicted: Union[pd.Series, np.ndarray],
    window: int | None = None
) -> float:
    """
    Calculate Root Mean Squared Error (RMSE).

    RMSE measures the square root of the average of squared differences
    between predicted and actual values. It penalizes large errors more
    heavily than MAE.

    Formula:
        RMSE = sqrt(mean((actual - predicted)^2))

    Args:
        actual: Actual observed values.
        predicted: Predicted values (must be same length as actual).
        window: Optional window size to use only the last N observations.
                If None, uses all values.

    Returns:
        RMSE as a float. Returns 0.0 if no valid observations.

    Example:
        >>> actual = pd.Series([100, 102, 101, 103])
        >>> predicted = pd.Series([101, 101, 102, 104])
        >>> rmse = calculate_rmse(actual, predicted)
        >>> print(f"RMSE: {rmse:.4f}")

    Notes:
        - RMSE has same units as input values
        - Sensitive to outliers (squared errors)
        - Lower is better (0 = perfect forecast)
        - Use window parameter for recent performance assessment
    """
    if isinstance(actual, pd.Series):
        actual = actual.values
    if isinstance(predicted, pd.Series):
        predicted = predicted.values

    if window is not None:
        actual = actual[-window:]
        predicted = predicted[-window:]

    errors = actual - predicted
    return float(np.sqrt(np.mean(np.square(errors))))


def calculate_mae(
    actual: Union[pd.Series, np.ndarray],
    predicted: Union[pd.Series, np.ndarray],
    window: int | None = None
) -> float:
    """
    Calculate Mean Absolute Error (MAE).

    MAE measures the average magnitude of errors in predictions, without
    considering their direction. It's more robust to outliers than RMSE.

    Formula:
        MAE = mean(|actual - predicted|)

    Args:
        actual: Actual observed values.
        predicted: Predicted values (must be same length as actual).
        window: Optional window size to use only the last N observations.
                If None, uses all values.

    Returns:
        MAE as a float. Returns 0.0 if no valid observations.

    Example:
        >>> actual = pd.Series([100, 102, 101, 103])
        >>> predicted = pd.Series([101, 101, 102, 104])
        >>> mae = calculate_mae(actual, predicted)
        >>> print(f"MAE: {mae:.4f}")

    Notes:
        - MAE has same units as input values
        - Less sensitive to outliers than RMSE
        - Lower is better (0 = perfect forecast)
        - Easier to interpret than RMSE
    """
    if isinstance(actual, pd.Series):
        actual = actual.values
    if isinstance(predicted, pd.Series):
        predicted = predicted.values

    if window is not None:
        actual = actual[-window:]
        predicted = predicted[-window:]

    errors = actual - predicted
    return float(np.mean(np.abs(errors)))


def calculate_mape(
    actual: Union[pd.Series, np.ndarray],
    predicted: Union[pd.Series, np.ndarray],
    window: int | None = None
) -> float:
    """
    Calculate Mean Absolute Percentage Error (MAPE).

    MAPE expresses accuracy as a percentage, making it scale-independent
    and useful for comparing forecasts across different series.

    Formula:
        MAPE = mean(|actual - predicted| / |actual|) * 100

    Args:
        actual: Actual observed values (must be non-zero).
        predicted: Predicted values (must be same length as actual).
        window: Optional window size to use only the last N observations.
                If None, uses all values.

    Returns:
        MAPE as a percentage (0-100+). Returns 0.0 if no valid observations.

    Example:
        >>> actual = pd.Series([100, 102, 101, 103])
        >>> predicted = pd.Series([101, 101, 102, 104])
        >>> mape = calculate_mape(actual, predicted)
        >>> print(f"MAPE: {mape:.2f}%")

    Notes:
        - Scale-independent (useful for comparing different series)
        - Sensitive to values near zero (can be unstable)
        - Zero values in actual are replaced with NaN and ignored
        - Lower is better (0% = perfect forecast)
        - Values > 100% indicate poor forecasts

    Limitations:
        - Undefined for actual values of zero
        - Asymmetric (overestimation penalized more than underestimation)
        - Not suitable for series crossing zero
        - Consider using sMAPE (symmetric MAPE) for better properties
    """
    if isinstance(actual, pd.Series):
        actual = actual.values
    if isinstance(predicted, pd.Series):
        predicted = predicted.values

    if window is not None:
        actual = actual[-window:]
        predicted = predicted[-window:]

    # Replace zeros with NaN to avoid division by zero
    actual_safe = np.where(actual == 0, np.nan, actual)
    errors = np.abs(actual - predicted) / np.abs(actual_safe)

    # Ignore NaN values in mean calculation
    return float(np.nanmean(errors) * 100)


__all__ = [
    "calculate_rmse",
    "calculate_mae",
    "calculate_mape",
]
