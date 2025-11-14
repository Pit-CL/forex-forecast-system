"""
Chronos Model Hyperparameter Optimizer.

Optimizes Chronos model hyperparameters using grid search and backtesting.
Since Chronos is a pretrained foundation model, we don't retrain the model
itself but optimize:
- context_length: How much historical data to use
- num_samples: Number of probabilistic samples
- temperature: Sampling diversity

Example:
    >>> optimizer = ChronosHyperparameterOptimizer(horizon="7d")
    >>> best_config = optimizer.optimize(usdclp_series)
    >>> print(f"Best RMSE: {best_config.validation_rmse:.2f}")
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

from ..forecasting.chronos_model import forecast_chronos
from ..forecasting.metrics import calculate_rmse, calculate_mape, calculate_mae


# Hyperparameter search spaces per horizon
CONTEXT_LENGTH_SEARCH_SPACE = {
    "7d": [90, 180, 270],  # 3, 6, 9 months
    "15d": [90, 180, 365],  # 3, 6, 12 months
    "30d": [180, 365, 540],  # 6, 12, 18 months
    "90d": [365, 540, 730],  # 1, 1.5, 2 years
}

NUM_SAMPLES_SEARCH_SPACE = [50, 100, 200]
TEMPERATURE_SEARCH_SPACE = [0.8, 1.0, 1.2]


@dataclass
class OptimizedConfig:
    """
    Optimized configuration for Chronos model.

    Attributes:
        horizon: Forecast horizon this config is for.
        context_length: Optimal historical context window (days).
        num_samples: Optimal number of probabilistic samples.
        temperature: Optimal sampling temperature.
        validation_rmse: RMSE on validation set.
        validation_mape: MAPE on validation set.
        validation_mae: MAE on validation set.
        search_iterations: Number of configs tested.
        optimization_time_seconds: Time taken to optimize.
        timestamp: When optimization was performed.
    """

    horizon: str
    context_length: int
    num_samples: int
    temperature: float
    validation_rmse: float
    validation_mape: float
    validation_mae: float
    search_iterations: int
    optimization_time_seconds: float
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "horizon": self.horizon,
            "context_length": self.context_length,
            "num_samples": self.num_samples,
            "temperature": self.temperature,
            "validation_rmse": self.validation_rmse,
            "validation_mape": self.validation_mape,
            "validation_mae": self.validation_mae,
            "search_iterations": self.search_iterations,
            "optimization_time_seconds": self.optimization_time_seconds,
            "timestamp": self.timestamp.isoformat(),
        }


class ChronosHyperparameterOptimizer:
    """
    Optimizes Chronos model hyperparameters using grid search.

    Uses walk-forward backtesting on recent historical data to find
    the best hyperparameter combination.

    Args:
        horizon: Forecast horizon to optimize (e.g., "7d", "15d").
        validation_window: Number of days to use for validation (default: 30).
        search_method: "grid" or "random" (default: "grid").
        max_iterations: Max iterations for random search (default: 20).

    Example:
        >>> optimizer = ChronosHyperparameterOptimizer(horizon="7d")
        >>> best_config = optimizer.optimize(usdclp_series)
        >>>
        >>> print(f"Optimal context: {best_config.context_length} days")
        >>> print(f"Validation RMSE: {best_config.validation_rmse:.2f}")
    """

    def __init__(
        self,
        horizon: str,
        validation_window: int = 30,
        search_method: str = "grid",
        max_iterations: int = 20,
    ):
        self.horizon = horizon
        self.validation_window = validation_window
        self.search_method = search_method
        self.max_iterations = max_iterations

        # Extract horizon days
        self.horizon_days = self._parse_horizon(horizon)

        logger.info(
            f"ChronosHyperparameterOptimizer initialized: "
            f"horizon={horizon}, validation_window={validation_window}d, "
            f"method={search_method}"
        )

    def optimize(self, series: pd.Series) -> OptimizedConfig:
        """
        Find optimal hyperparameters using grid search.

        Args:
            series: Historical USD/CLP series.

        Returns:
            OptimizedConfig with best hyperparameters and validation metrics.

        Example:
            >>> best_config = optimizer.optimize(usdclp_series)
            >>> print(f"Best RMSE: {best_config.validation_rmse:.2f}")
        """
        logger.info(
            f"Starting optimization for {self.horizon} "
            f"(series length: {len(series)} days)"
        )

        start_time = datetime.now()

        if self.search_method == "grid":
            best_config = self._grid_search(series)
        elif self.search_method == "random":
            best_config = self._random_search(series)
        else:
            raise ValueError(f"Unknown search method: {self.search_method}")

        elapsed = (datetime.now() - start_time).total_seconds()
        best_config.optimization_time_seconds = elapsed

        logger.info(
            f"Optimization complete: {self.horizon}, "
            f"RMSE={best_config.validation_rmse:.2f}, "
            f"iterations={best_config.search_iterations}, "
            f"time={elapsed:.1f}s"
        )

        return best_config

    def _grid_search(self, series: pd.Series) -> OptimizedConfig:
        """
        Exhaustive grid search over hyperparameter space.

        Complexity: O(|context| x |samples| x |temp|)
        Example: 3 x 3 x 3 = 27 evaluations
        """
        context_lengths = CONTEXT_LENGTH_SEARCH_SPACE.get(
            self.horizon, [180]
        )
        num_samples_options = NUM_SAMPLES_SEARCH_SPACE
        temperature_options = TEMPERATURE_SEARCH_SPACE

        best_rmse = float("inf")
        best_config = None
        iterations = 0

        total_combinations = (
            len(context_lengths)
            * len(num_samples_options)
            * len(temperature_options)
        )

        logger.info(
            f"Grid search: {total_combinations} combinations to evaluate"
        )

        for context in context_lengths:
            for num_samples in num_samples_options:
                for temp in temperature_options:
                    iterations += 1

                    logger.debug(
                        f"Evaluating [{iterations}/{total_combinations}]: "
                        f"context={context}, samples={num_samples}, temp={temp}"
                    )

                    # Backtest this configuration
                    rmse, mape, mae = self._backtest_config(
                        series=series,
                        context_length=context,
                        num_samples=num_samples,
                        temperature=temp,
                    )

                    # Update best if better
                    if rmse < best_rmse:
                        best_rmse = rmse
                        best_config = OptimizedConfig(
                            horizon=self.horizon,
                            context_length=context,
                            num_samples=num_samples,
                            temperature=temp,
                            validation_rmse=rmse,
                            validation_mape=mape,
                            validation_mae=mae,
                            search_iterations=iterations,
                            optimization_time_seconds=0,  # Will be set later
                        )

                        logger.info(
                            f"New best: RMSE={rmse:.2f}, "
                            f"config=(context={context}, samples={num_samples}, temp={temp})"
                        )

        if best_config is None:
            raise RuntimeError("Grid search failed to find any valid configuration")

        return best_config

    def _random_search(self, series: pd.Series) -> OptimizedConfig:
        """
        Random search over hyperparameter space (for faster optimization).

        Samples random combinations up to max_iterations.
        """
        context_lengths = CONTEXT_LENGTH_SEARCH_SPACE.get(
            self.horizon, [180]
        )
        num_samples_options = NUM_SAMPLES_SEARCH_SPACE
        temperature_options = TEMPERATURE_SEARCH_SPACE

        best_rmse = float("inf")
        best_config = None

        logger.info(f"Random search: {self.max_iterations} iterations")

        for iteration in range(self.max_iterations):
            # Sample random config
            context = np.random.choice(context_lengths)
            num_samples = np.random.choice(num_samples_options)
            temp = np.random.choice(temperature_options)

            logger.debug(
                f"Evaluating [{iteration + 1}/{self.max_iterations}]: "
                f"context={context}, samples={num_samples}, temp={temp}"
            )

            # Backtest
            rmse, mape, mae = self._backtest_config(
                series=series,
                context_length=context,
                num_samples=num_samples,
                temperature=temp,
            )

            # Update best
            if rmse < best_rmse:
                best_rmse = rmse
                best_config = OptimizedConfig(
                    horizon=self.horizon,
                    context_length=context,
                    num_samples=num_samples,
                    temperature=temp,
                    validation_rmse=rmse,
                    validation_mape=mape,
                    validation_mae=mae,
                    search_iterations=iteration + 1,
                    optimization_time_seconds=0,
                )

                logger.info(
                    f"New best: RMSE={rmse:.2f}, "
                    f"config=(context={context}, samples={num_samples}, temp={temp})"
                )

        if best_config is None:
            raise RuntimeError("Random search failed to find any valid configuration")

        return best_config

    def _backtest_config(
        self,
        series: pd.Series,
        context_length: int,
        num_samples: int,
        temperature: float,
    ) -> tuple[float, float, float]:
        """
        Backtest a specific hyperparameter configuration.

        Uses walk-forward validation:
        1. Hold out last `validation_window` days
        2. Generate forecasts from (len - validation_window) point
        3. Compare forecasts to actuals
        4. Return RMSE, MAPE, MAE

        Returns:
            (rmse, mape, mae)
        """
        try:
            # Ensure enough data for context + validation
            min_required = context_length + self.validation_window
            if len(series) < min_required:
                logger.warning(
                    f"Insufficient data: need {min_required}, have {len(series)}"
                )
                return float("inf"), float("inf"), float("inf")

            # Split: train up to (len - validation_window)
            split_point = len(series) - self.validation_window
            train_series = series.iloc[:split_point]
            actual_values = series.iloc[
                split_point : split_point + self.horizon_days
            ].values

            # Generate forecast
            forecast_package = forecast_chronos(
                series=train_series,
                steps=self.horizon_days,
                context_length=context_length,
                num_samples=num_samples,
                temperature=temperature,
                validate=False,  # Skip internal validation (we're doing it)
            )

            # Extract predictions
            predicted_values = np.array(
                [point.mean for point in forecast_package.series]
            )

            # Ensure same length
            min_len = min(len(predicted_values), len(actual_values))
            predicted_values = predicted_values[:min_len]
            actual_values = actual_values[:min_len]

            # Calculate metrics
            rmse = calculate_rmse(actual_values, predicted_values)
            mape = calculate_mape(actual_values, predicted_values)
            mae = calculate_mae(actual_values, predicted_values)

            return rmse, mape, mae

        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            return float("inf"), float("inf"), float("inf")

    def _parse_horizon(self, horizon: str) -> int:
        """
        Parse horizon string to number of days.

        Examples:
            "7d" -> 7
            "15d" -> 15
            "30d" -> 30
            "90d" -> 90
        """
        horizon_map = {
            "7d": 7,
            "15d": 15,
            "30d": 30,
            "90d": 90,
        }

        days = horizon_map.get(horizon)
        if days is None:
            # Try to parse manually
            try:
                days = int(horizon.replace("d", ""))
            except ValueError:
                raise ValueError(f"Invalid horizon format: {horizon}")

        return days


__all__ = [
    "ChronosHyperparameterOptimizer",
    "OptimizedConfig",
    "CONTEXT_LENGTH_SEARCH_SPACE",
    "NUM_SAMPLES_SEARCH_SPACE",
    "TEMPERATURE_SEARCH_SPACE",
]
