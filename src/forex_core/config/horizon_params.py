"""
Horizon-specific model parameters.

This module defines model parameters optimized for different forecast horizons.
Based on statistical analysis and recommendations from the USD/CLP forecasting agent.

The parameters are tuned to balance model complexity with forecast accuracy
across different time horizons (7d, 15d, 30d, 90d).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ARIMAParams:
    """ARIMA model parameters for a specific forecast horizon."""

    max_p: int  # Maximum AR order
    max_d: int  # Maximum differencing order
    max_q: int  # Maximum MA order
    seasonal: bool  # Whether to use seasonal ARIMA
    m: int  # Seasonal period (if seasonal=True)


@dataclass(frozen=True)
class VARParams:
    """VAR (Vector Autoregression) model parameters for a specific forecast horizon."""

    maxlags: int  # Maximum number of lags to consider
    ic: Literal["aic", "bic", "hqic", "fpe"]  # Information criterion for lag selection


@dataclass(frozen=True)
class RandomForestParams:
    """Random Forest model parameters for a specific forecast horizon."""

    n_estimators: int  # Number of trees
    max_depth: int  # Maximum tree depth
    min_samples_split: int  # Minimum samples to split a node
    min_samples_leaf: int  # Minimum samples in a leaf node
    max_features: Literal["sqrt", "log2", None]  # Number of features to consider


@dataclass(frozen=True)
class EnsembleWeights:
    """Ensemble model weights for a specific forecast horizon."""

    arima_weight: float  # Weight for ARIMA+GARCH model
    var_weight: float  # Weight for VAR model
    rf_weight: float  # Weight for Random Forest model

    def __post_init__(self) -> None:
        """Validate that weights sum to 1.0."""
        total = self.arima_weight + self.var_weight + self.rf_weight
        if not (0.99 <= total <= 1.01):  # Allow small floating point errors
            msg = f"Ensemble weights must sum to 1.0, got {total}"
            raise ValueError(msg)


@dataclass(frozen=True)
class HorizonParameters:
    """Complete model parameter configuration for a specific forecast horizon."""

    horizon: Literal["7d", "15d", "30d", "90d"]
    arima: ARIMAParams
    var: VARParams
    rf: RandomForestParams
    ensemble: EnsembleWeights
    confidence_multiplier: float  # Multiplier for confidence interval widening


# 7-day horizon parameters (current production configuration)
PARAMS_7D = HorizonParameters(
    horizon="7d",
    arima=ARIMAParams(max_p=2, max_d=1, max_q=2, seasonal=False, m=1),
    var=VARParams(maxlags=5, ic="aic"),
    rf=RandomForestParams(
        n_estimators=400,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        max_features="sqrt",
    ),
    ensemble=EnsembleWeights(arima_weight=0.45, var_weight=0.35, rf_weight=0.20),
    confidence_multiplier=1.00,
)

# 15-day horizon parameters
PARAMS_15D = HorizonParameters(
    horizon="15d",
    arima=ARIMAParams(max_p=3, max_d=1, max_q=3, seasonal=False, m=1),
    var=VARParams(maxlags=7, ic="aic"),
    rf=RandomForestParams(
        n_estimators=500,
        max_depth=12,
        min_samples_split=5,
        min_samples_leaf=2,
        max_features="sqrt",
    ),
    ensemble=EnsembleWeights(arima_weight=0.40, var_weight=0.40, rf_weight=0.20),
    confidence_multiplier=1.15,
)

# 30-day horizon parameters
PARAMS_30D = HorizonParameters(
    horizon="30d",
    arima=ARIMAParams(max_p=5, max_d=1, max_q=5, seasonal=False, m=1),
    var=VARParams(maxlags=10, ic="aic"),
    rf=RandomForestParams(
        n_estimators=600,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        max_features="sqrt",
    ),
    ensemble=EnsembleWeights(arima_weight=0.35, var_weight=0.40, rf_weight=0.25),
    confidence_multiplier=1.35,
)

# 90-day horizon parameters
PARAMS_90D = HorizonParameters(
    horizon="90d",
    arima=ARIMAParams(max_p=7, max_d=1, max_q=7, seasonal=True, m=20),  # ~20 business days per month
    var=VARParams(maxlags=15, ic="bic"),  # Use BIC for longer horizons to avoid overfitting
    rf=RandomForestParams(
        n_estimators=800,
        max_depth=20,
        min_samples_split=8,
        min_samples_leaf=3,
        max_features="sqrt",
    ),
    ensemble=EnsembleWeights(arima_weight=0.30, var_weight=0.35, rf_weight=0.35),
    confidence_multiplier=1.75,
)


def get_horizon_params(horizon: Literal["7d", "15d", "30d", "90d"]) -> HorizonParameters:
    """
    Get model parameters for a specific forecast horizon.

    Args:
        horizon: Forecast horizon - "7d", "15d", "30d", or "90d".

    Returns:
        HorizonParameters object with optimized model parameters.

    Raises:
        ValueError: If horizon is not supported.

    Example:
        >>> params = get_horizon_params("15d")
        >>> params.arima.max_p
        3
        >>> params.ensemble.arima_weight
        0.4
        >>> params.confidence_multiplier
        1.15
    """
    params_map = {
        "7d": PARAMS_7D,
        "15d": PARAMS_15D,
        "30d": PARAMS_30D,
        "90d": PARAMS_90D,
    }
    if horizon not in params_map:
        msg = f"Unsupported horizon: {horizon}. Must be one of {list(params_map.keys())}"
        raise ValueError(msg)
    return params_map[horizon]


__all__ = [
    "ARIMAParams",
    "VARParams",
    "RandomForestParams",
    "EnsembleWeights",
    "HorizonParameters",
    "PARAMS_7D",
    "PARAMS_15D",
    "PARAMS_30D",
    "PARAMS_90D",
    "get_horizon_params",
]
