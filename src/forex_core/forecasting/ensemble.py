"""
Ensemble forecasting methods.

Ensemble methods combine predictions from multiple models to improve
forecast accuracy and robustness. This module implements:
- Inverse RMSE weighting (better models get more weight)
- Weighted mean and variance combination
- Ensemble artifact tracking (weights, metrics, metadata)

Research shows ensemble forecasts often outperform individual models by:
- Reducing variance through diversification
- Capturing different aspects of the data generating process
- Being robust to model misspecification

Weighting schemes:
1. Inverse RMSE (implemented): w_i = (1/RMSE_i) / sum(1/RMSE_j)
2. Equal weights: w_i = 1/n (naive but often competitive)
3. OLS stacking: Learn optimal weights via regression
4. Bayesian Model Averaging: Posterior model probabilities
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from ..data.models import ForecastPoint, ForecastPackage


@dataclass
class ModelResult:
    """
    Individual model forecast result with performance metrics.

    Attributes:
        name: Model identifier (e.g., "arima_garch", "var", "random_forest").
        package: ForecastPackage with forecast series and metadata.
        rmse: Root Mean Squared Error on validation set.
        mape: Mean Absolute Percentage Error on validation set.
        extras: Additional model-specific metadata (e.g., ARIMA order, lag order).

    Example:
        >>> result = ModelResult(
        ...     name="arima_garch",
        ...     package=forecast_package,
        ...     rmse=3.45,
        ...     mape=0.36,
        ...     extras={"order_p": 1, "order_q": 1}
        ... )
    """
    name: str
    package: ForecastPackage
    rmse: float
    mape: float
    extras: Dict[str, float | tuple]


@dataclass
class EnsembleArtifacts:
    """
    Ensemble metadata and diagnostics.

    Attributes:
        weights: Dictionary mapping model name to ensemble weight (sum to 1.0).
        component_metrics: Dictionary of each model's performance metrics.
        arima_order: ARIMA order if ARIMA is in ensemble, else None.

    Example:
        >>> artifacts = EnsembleArtifacts(
        ...     weights={"arima_garch": 0.45, "var": 0.35, "random_forest": 0.20},
        ...     component_metrics={
        ...         "arima_garch": {"RMSE": 3.45, "MAPE": 0.36},
        ...         "var": {"RMSE": 4.21, "MAPE": 0.42},
        ...         "random_forest": {"RMSE": 5.12, "MAPE": 0.48}
        ...     },
        ...     arima_order=(1, 0, 1)
        ... )
    """
    weights: Dict[str, float]
    component_metrics: Dict[str, Dict[str, float]]
    arima_order: tuple[int, int, int] | None


def compute_weights(
    results: Dict[str, ModelResult],
    window: int | None = None
) -> Dict[str, float]:
    """
    Compute ensemble weights using inverse RMSE weighting.

    Models with lower RMSE receive higher weights. This is a simple but
    effective weighting scheme that emphasizes recent forecast accuracy.

    Formula:
        w_i = (1 / RMSE_i) / sum_j(1 / RMSE_j)

    Args:
        results: Dictionary of ModelResult objects keyed by model name.
        window: Optional window size (not used in current implementation,
                but reserved for rolling window weighting).

    Returns:
        Dictionary of weights (same keys as results, values sum to 1.0).

    Example:
        >>> results = {
        ...     "arima_garch": ModelResult(..., rmse=3.45, ...),
        ...     "var": ModelResult(..., rmse=4.21, ...),
        ...     "random_forest": ModelResult(..., rmse=5.12, ...)
        ... }
        >>> weights = compute_weights(results)
        >>> print(weights)
        {'arima_garch': 0.45, 'var': 0.35, 'random_forest': 0.20}

    Notes:
        - Requires rmse > 0 for all models (enforces minimum 1e-6)
        - If all models have identical RMSE, returns equal weights
        - Alternative schemes: inverse variance, BMA, CV-optimized
        - Consider time-varying weights for non-stationary environments

    Statistical properties:
        - Asymptotically optimal under squared loss
        - No guarantee of optimal out-of-sample performance
        - Can be unstable with small sample sizes
        - Sensitive to outliers in RMSE estimation

    Improvements to consider:
        - Use cross-validated RMSE instead of in-sample
        - Shrink extreme weights toward 1/n (Bates-Granger, 1969)
        - Use exponential weighting to emphasize recent performance
        - Implement weight constraints (e.g., min 0.1, max 0.5)
    """
    inverted = {}
    for name, result in results.items():
        # Enforce minimum RMSE to avoid division by zero
        rmse = max(result.rmse, 1e-6)
        inverted[name] = 1.0 / rmse

    total = sum(inverted.values())

    # Handle edge case: all models equally bad
    if total == 0:
        return {name: 1.0 / len(results) for name in results}

    # Normalize to sum to 1
    weights = {name: value / total for name, value in inverted.items()}

    return weights


def combine_forecasts(
    results: Dict[str, ModelResult],
    weights: Dict[str, float],
    steps: int
) -> ForecastPackage:
    """
    Combine multiple forecast packages into weighted ensemble.

    This function:
    1. Takes weighted average of point forecasts (mean)
    2. Takes weighted average of standard deviations
    3. Reconstructs confidence intervals from ensemble std dev
    4. Creates methodology string describing ensemble composition

    Args:
        results: Dictionary of ModelResult objects.
        weights: Dictionary of ensemble weights (must sum to ~1.0).
        steps: Number of forecast steps.

    Returns:
        ForecastPackage with ensemble forecast series.

    Example:
        >>> ensemble = combine_forecasts(results, weights, steps=7)
        >>> print(ensemble.methodology)
        >>> print(f"Day 7 forecast: {ensemble.series[-1].mean:.2f}")

    Notes:
        - Assumes all models have same forecast horizon
        - Assumes all models have same date index
        - Confidence intervals use normal distribution assumption
        - Alternative: Bootstrap ensemble distributions for non-normality

    Confidence interval formulas:
        CI_80: mean +/- 1.2816 * std_dev
        CI_95: mean +/- 1.96 * std_dev

    Where:
        - 1.2816 = z-score for 80% CI (90th percentile)
        - 1.96 = z-score for 95% CI (97.5th percentile)

    Theoretical justification:
        - Weighted mean is minimum variance unbiased estimator (MVUE)
          if weights are optimal (inverse variance)
        - Ensemble variance typically < individual model variances
        - Forecast combination literature: Bates & Granger (1969),
          Timmermann (2006), Genre et al. (2013)

    Limitations:
        - Assumes independence of forecast errors (often violated)
        - Correlation between models reduces diversification benefit
        - Simple linear combination (nonlinear combinations possible)
        - No accounting for model correlation in uncertainty quantification
    """
    names = list(results.keys())
    base_series = results[names[0]].package.series

    combined_points: List[ForecastPoint] = []

    for idx in range(steps):
        # Get date from first model (assume all have same dates)
        date = base_series[idx].date

        # Weighted average of means
        mean = sum(
            weights[name] * results[name].package.series[idx].mean
            for name in names
        )

        # Weighted average of standard deviations
        std = sum(
            weights[name] * results[name].package.series[idx].std_dev
            for name in names
        )

        # Reconstruct confidence intervals
        # 80% CI: +/- 1.2816 std (z-score for 90th percentile)
        ci80_low = mean - 1.2816 * std
        ci80_high = mean + 1.2816 * std

        # 95% CI: +/- 1.96 std (z-score for 97.5th percentile)
        ci95_low = mean - 1.96 * std
        ci95_high = mean + 1.96 * std

        combined_points.append(
            ForecastPoint(
                date=date,
                mean=mean,
                ci80_low=ci80_low,
                ci80_high=ci80_high,
                ci95_low=ci95_low,
                ci95_high=ci95_high,
                std_dev=std,
            )
        )

    # Create methodology description
    methodology = "Ensemble ponderado (" + ", ".join(
        f"{name}:{weights[name]:.2f}" for name in names
    ) + ")"

    # Weighted average of residual volatilities
    residual_vol = float(np.mean([
        res.package.residual_vol for res in results.values()
    ]))

    package = ForecastPackage(
        series=combined_points,
        methodology=methodology,
        error_metrics={},  # Ensemble doesn't have single in-sample metrics
        residual_vol=residual_vol,
    )

    return package


__all__ = [
    "ModelResult",
    "EnsembleArtifacts",
    "compute_weights",
    "combine_forecasts",
]
