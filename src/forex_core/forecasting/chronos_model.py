"""
Chronos-Bolt-Small integration for forex time series forecasting.

This module provides integration with Amazon's Chronos-Bolt-Small foundation model
for time series forecasting. Chronos is a pretrained transformer-based model
that can forecast unseen time series with zero-shot capability.

Key features:
- Zero-shot forecasting (no training required)
- Probabilistic forecasts with confidence intervals
- Memory-efficient singleton pattern for model loading
- Pseudo-validation using historical data
- Compatible with ForecastPackage interface

Model specifications:
- Chronos-Bolt-Small: ~100M parameters
- Context length: Configurable (64-512 tokens typical)
- Inference: CPU-compatible (GPU optional)
- Memory requirement: ~400-600MB RAM

References:
    Ansari et al. (2024). "Chronos: Learning the Language of Time Series"
    https://arxiv.org/abs/2403.07815
"""

from __future__ import annotations

import gc
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

import numpy as np
import pandas as pd
import psutil
import torch

from ..data.models import ForecastPackage, ForecastPoint
from ..utils.logging import get_logger

if TYPE_CHECKING:
    from chronos import ChronosPipeline

logger = get_logger(__name__)

# Singleton instance for pipeline to avoid repeated model loading
_CHRONOS_PIPELINE: Optional["ChronosPipeline"] = None
# Fallback to chronos-t5-small (stable) if chronos-bolt-small fails
_MODEL_VARIANTS = [
    "amazon/chronos-bolt-small",  # Preferred: more efficient
    "amazon/chronos-t5-small",    # Fallback: stable and compatible
]


def get_chronos_pipeline(force_reload: bool = False) -> "ChronosPipeline":
    """
    Get or create singleton Chronos pipeline instance.

    Uses lazy loading with singleton pattern to minimize memory usage.
    The model is loaded once and reused across all forecasts.

    Args:
        force_reload: If True, force reload the model even if already loaded.

    Returns:
        ChronosPipeline instance ready for inference.

    Raises:
        ImportError: If chronos package is not installed.
        MemoryError: If insufficient RAM available.
        RuntimeError: If model loading fails.

    Example:
        >>> pipeline = get_chronos_pipeline()
        >>> # Use pipeline for forecasting
        >>> pipeline = get_chronos_pipeline(force_reload=True)  # Reload model
    """
    global _CHRONOS_PIPELINE

    if _CHRONOS_PIPELINE is not None and not force_reload:
        logger.debug("Reusing existing Chronos pipeline")
        return _CHRONOS_PIPELINE

    try:
        from chronos import ChronosPipeline
    except ImportError as exc:
        logger.error("chronos-forecasting package not installed")
        raise ImportError(
            "Please install chronos-forecasting: "
            "pip install chronos-forecasting"
        ) from exc

    # Check available memory before loading
    available_memory_mb = psutil.virtual_memory().available / (1024 * 1024)
    required_memory_mb = 800  # Conservative estimate for Chronos-Bolt-Small

    if available_memory_mb < required_memory_mb:
        logger.warning(
            f"Low memory: {available_memory_mb:.0f}MB available, "
            f"{required_memory_mb}MB recommended for Chronos"
        )

    # Try each model variant in order
    device_map = "cpu"
    torch_dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32

    last_error = None
    for model_variant in _MODEL_VARIANTS:
        logger.info(f"Loading Chronos pipeline: {model_variant}")

        try:
            # Load model on CPU (production environment constraint)
            _CHRONOS_PIPELINE = ChronosPipeline.from_pretrained(
                model_variant,
                device_map=device_map,
                torch_dtype=torch_dtype,
            )

            logger.info(
                f"Chronos pipeline loaded successfully: {model_variant} "
                f"(device={device_map}, dtype={torch_dtype})"
            )

            return _CHRONOS_PIPELINE

        except Exception as exc:
            logger.warning(f"Failed to load {model_variant}: {exc}")
            last_error = exc
            continue

    # All variants failed
    logger.error(f"Failed to load any Chronos variant. Last error: {last_error}")
    raise RuntimeError(f"Chronos pipeline loading failed: {last_error}") from last_error


def release_chronos_pipeline() -> None:
    """
    Release the Chronos pipeline from memory.

    Useful for freeing memory after forecasting is complete.
    The pipeline will be reloaded on next call to get_chronos_pipeline().

    Example:
        >>> forecast = forecast_chronos(series, steps=7)
        >>> release_chronos_pipeline()  # Free memory
    """
    global _CHRONOS_PIPELINE

    if _CHRONOS_PIPELINE is not None:
        logger.info("Releasing Chronos pipeline from memory")
        _CHRONOS_PIPELINE = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


def forecast_chronos(
    series: pd.Series,
    steps: int,
    context_length: Optional[int] = None,
    num_samples: int = 100,
    temperature: float = 1.0,
    top_k: int = 50,
    top_p: float = 1.0,
    validate: bool = True,
    validation_window: int = 30,
) -> ForecastPackage:
    """
    Generate probabilistic forecast using Chronos-Bolt-Small.

    This function:
    1. Validates input data
    2. Loads Chronos pipeline (cached singleton)
    3. Generates probabilistic samples
    4. Computes statistics (mean, std, confidence intervals)
    5. Optionally validates against recent history
    6. Returns standardized ForecastPackage

    Args:
        series: Pandas Series with datetime index and price values.
        steps: Number of steps to forecast (e.g., 7 for 7-day forecast).
        context_length: Number of historical points to use as context.
                       If None, uses adaptive strategy based on series length.
        num_samples: Number of probabilistic samples to generate (default: 100).
                    Higher = more accurate uncertainty but slower.
        temperature: Sampling temperature (0.0-2.0). Higher = more diverse samples.
        top_k: Top-K sampling parameter.
        top_p: Nucleus sampling parameter.
        validate: If True, perform pseudo-validation on recent history.
        validation_window: Number of recent points to use for validation.

    Returns:
        ForecastPackage with forecast series and metadata.

    Raises:
        ValueError: If series is too short or has invalid data.
        RuntimeError: If forecasting fails.

    Example:
        >>> series = pd.Series([950, 945, 955, ...], index=pd.date_range(...))
        >>> forecast = forecast_chronos(series, steps=7, context_length=180)
        >>> print(f"7-day forecast: {forecast.series[-1].mean:.2f}")
        >>> print(f"Methodology: {forecast.methodology}")

    Notes:
        - Chronos expects regular time series (no missing dates)
        - Model is pretrained, no fine-tuning required
        - Memory usage: ~400-600MB + (num_samples * steps * 8 bytes)
        - CPU inference time: ~2-10 seconds per forecast
        - Context length recommendations:
          * 7d forecast: 180 days (6 months)
          * 15d forecast: 180 days
          * 30d forecast: 90 days (3 months)
          * 90d forecast: 365 days (1 year)
    """
    # Validate input
    if len(series) < 30:
        raise ValueError(
            f"Series too short for Chronos: {len(series)} points "
            "(minimum 30 required)"
        )

    if series.isnull().any():
        logger.warning(
            f"Series contains {series.isnull().sum()} null values, forward filling"
        )
        series = series.ffill().bfill()

    if steps < 1 or steps > 365:
        raise ValueError(f"Invalid steps: {steps} (must be 1-365)")

    # Determine optimal context length
    if context_length is None:
        context_length = _adaptive_context_length(len(series), steps)

    logger.info(
        f"Chronos forecast: {steps} steps, "
        f"context={context_length}, samples={num_samples}"
    )

    # Limit context to available data
    context_length = min(context_length, len(series))
    context_series = series.iloc[-context_length:]

    try:
        # Load pipeline (singleton, cached)
        pipeline = get_chronos_pipeline()

        # Convert to tensor format
        context_tensor = torch.tensor(
            context_series.values, dtype=torch.float32
        ).unsqueeze(0)

        # Generate forecast samples
        logger.debug("Generating Chronos forecast samples...")
        start_time = datetime.now()

        forecast_samples = pipeline.predict(
            context=context_tensor,
            prediction_length=steps,
            num_samples=num_samples,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
        )

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Chronos inference completed in {elapsed:.2f}s")

        # Extract samples as numpy array [num_samples, steps]
        samples = forecast_samples[0].numpy()

        # Compute statistics
        mean_forecast = samples.mean(axis=0)
        std_forecast = samples.std(axis=0)

        # Build forecast points with confidence intervals
        points = _build_forecast_points(
            series.index[-1],
            mean_forecast,
            std_forecast,
            freq=series.index.freq or pd.infer_freq(series.index),
        )

        # Pseudo-validation on recent history
        pseudo_rmse = None
        if validate and len(series) >= validation_window + steps:
            pseudo_rmse = _pseudo_validate(
                series,
                steps=steps,
                context_length=context_length,
                num_samples=num_samples,
                validation_window=validation_window,
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
            )
            logger.info(f"Chronos pseudo-validation RMSE: {pseudo_rmse:.4f}")

        # Build metadata
        methodology = (
            f"Chronos-Bolt-Small (pretrained transformer, "
            f"context={context_length}, samples={num_samples})"
        )

        error_metrics = {}
        if pseudo_rmse is not None:
            error_metrics["pseudo_RMSE"] = float(pseudo_rmse)
            error_metrics["pseudo_MAPE"] = float(
                pseudo_rmse / series.iloc[-validation_window:].mean()
            )

        package = ForecastPackage(
            series=points,
            methodology=methodology,
            error_metrics=error_metrics,
            residual_vol=float(std_forecast.mean()),
        )

        logger.info(
            f"Chronos forecast complete: mean={mean_forecast[-1]:.2f}, "
            f"std={std_forecast[-1]:.2f}"
        )

        return package

    except Exception as exc:
        logger.error(f"Chronos forecasting failed: {exc}")
        raise RuntimeError(f"Chronos forecast generation failed: {exc}") from exc


def _adaptive_context_length(series_length: int, forecast_steps: int) -> int:
    """
    Determine optimal context length based on series length and horizon.

    Strategy:
    - Short-term forecasts (7-15d): Use more context (6 months)
    - Medium-term (30d): Use moderate context (3 months)
    - Long-term (90d+): Use extensive context (1 year)
    - Always respect available data length

    Args:
        series_length: Total length of historical series.
        forecast_steps: Number of steps to forecast.

    Returns:
        Recommended context length.
    """
    if forecast_steps <= 15:
        # Short-term: 6 months context
        recommended = 180
    elif forecast_steps <= 30:
        # Medium-term: 3 months context
        recommended = 90
    else:
        # Long-term: 1 year context
        recommended = 365

    # Don't exceed available data (leave at least 10% for validation)
    max_context = int(series_length * 0.9)
    context = min(recommended, max_context)

    logger.debug(
        f"Adaptive context: {context} days "
        f"(series_length={series_length}, steps={forecast_steps})"
    )

    return context


def _build_forecast_points(
    last_date: pd.Timestamp,
    mean_values: np.ndarray,
    std_values: np.ndarray,
    freq: Optional[str] = None,
) -> list[ForecastPoint]:
    """
    Build ForecastPoint list from mean and std arrays.

    Args:
        last_date: Last date in historical series.
        mean_values: Array of mean forecasts.
        std_values: Array of forecast standard deviations.
        freq: Frequency string (e.g., 'D', 'ME'). If None, assumes daily.

    Returns:
        List of ForecastPoint objects with confidence intervals.
    """
    steps = len(mean_values)

    # Generate future dates
    if freq is None or freq == "D":
        # Daily frequency
        future_dates = pd.date_range(
            start=last_date + timedelta(days=1),
            periods=steps,
            freq="D",
        )
    elif freq in ["ME", "M"]:
        # Monthly frequency
        future_dates = pd.date_range(
            start=last_date + pd.offsets.MonthEnd(1),
            periods=steps,
            freq="ME",
        )
    else:
        # Fallback to inferred frequency
        try:
            future_dates = pd.date_range(
                start=last_date,
                periods=steps + 1,
                freq=freq,
            )[1:]
        except Exception:
            # Last resort: daily
            logger.warning(f"Unknown frequency '{freq}', using daily")
            future_dates = pd.date_range(
                start=last_date + timedelta(days=1),
                periods=steps,
                freq="D",
            )

    points = []
    for i, (date, mean, std) in enumerate(zip(future_dates, mean_values, std_values)):
        # Confidence intervals (normal distribution assumption)
        # 80% CI: +/- 1.2816 std (z-score for 90th percentile)
        # 95% CI: +/- 1.96 std (z-score for 97.5th percentile)
        points.append(
            ForecastPoint(
                date=date.to_pydatetime(),
                mean=float(mean),
                ci80_low=float(mean - 1.2816 * std),
                ci80_high=float(mean + 1.2816 * std),
                ci95_low=float(mean - 1.96 * std),
                ci95_high=float(mean + 1.96 * std),
                std_dev=float(std),
            )
        )

    return points


def _pseudo_validate(
    series: pd.Series,
    steps: int,
    context_length: int,
    num_samples: int,
    validation_window: int,
    temperature: float,
    top_k: int,
    top_p: float,
) -> float:
    """
    Perform pseudo-validation using recent historical data.

    Strategy:
    1. Hold out last `validation_window` points
    2. Forecast from earlier point
    3. Compare forecast to actual held-out values
    4. Compute RMSE as validation metric

    Args:
        series: Full historical series.
        steps: Forecast horizon.
        context_length: Context length for forecasting.
        num_samples: Number of samples to generate.
        validation_window: Number of recent points for validation.
        temperature: Sampling temperature.
        top_k: Top-K sampling.
        top_p: Nucleus sampling.

    Returns:
        Validation RMSE.

    Notes:
        - This is a pseudo-validation (not true out-of-sample)
        - Provides rough estimate of model performance
        - More robust than in-sample metrics
        - Computational cost: ~2x inference time
    """
    try:
        # Split: use data up to (len - validation_window) for context
        split_point = len(series) - validation_window
        train_series = series.iloc[:split_point]
        test_actual = series.iloc[split_point : split_point + steps].values

        if len(train_series) < context_length:
            logger.warning(
                f"Insufficient data for validation "
                f"(need {context_length}, have {len(train_series)})"
            )
            return np.nan

        # Generate forecast
        pipeline = get_chronos_pipeline()
        context = train_series.iloc[-context_length:]
        context_tensor = torch.tensor(context.values, dtype=torch.float32).unsqueeze(0)

        forecast_samples = pipeline.predict(
            context=context_tensor,
            prediction_length=min(steps, len(test_actual)),
            num_samples=num_samples,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
        )

        # Extract mean forecast
        samples = forecast_samples[0].numpy()
        mean_forecast = samples.mean(axis=0)

        # Compute RMSE on overlapping portion
        min_len = min(len(mean_forecast), len(test_actual))
        rmse = np.sqrt(np.mean((mean_forecast[:min_len] - test_actual[:min_len]) ** 2))

        return float(rmse)

    except Exception as exc:
        logger.warning(f"Pseudo-validation failed: {exc}")
        return np.nan


__all__ = [
    "forecast_chronos",
    "get_chronos_pipeline",
    "release_chronos_pipeline",
]
