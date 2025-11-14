"""
GARCH/EGARCH Volatility Models for USD/CLP Forecasting.

This module implements volatility forecasting using:
- GARCH(1,1) for symmetric volatility (30d, 90d horizons)
- EGARCH for asymmetric/leverage effects (7d, 15d horizons)
- Volatility regime detection (low, normal, high, extreme)
- Dynamic confidence intervals for predictions
- Model persistence and diagnostics

The volatility models are designed to work with residuals from SARIMAX/XGBoost
forecasters and provide uncertainty quantification for the ensemble system.
"""

from __future__ import annotations

import json
import pickle
import warnings
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
from arch import arch_model
from arch.univariate import ConstantMean, GARCH, EGARCH, Normal

# Import loguru logger from project utils
from forex_core.utils.logging import logger

warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', module='arch')


class VolatilityRegime(str, Enum):
    """Volatility regime classification."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class GARCHConfig:
    """Configuration for GARCH/EGARCH volatility models."""

    horizon_days: int
    model_type: str = "GARCH"  # "GARCH" or "EGARCH"
    p: int = 1  # ARCH order
    q: int = 1  # GARCH order
    vol_scaling: float = 100.0  # Scale residuals for numerical stability

    # Regime detection thresholds (multipliers of historical mean volatility)
    regime_low_threshold: float = 0.5
    regime_normal_lower: float = 0.5
    regime_normal_upper: float = 1.5
    regime_high_lower: float = 1.5
    regime_high_upper: float = 2.5
    regime_extreme_threshold: float = 2.5

    @classmethod
    def from_horizon(cls, horizon_days: int) -> GARCHConfig:
        """
        Create horizon-specific volatility model configuration.

        Model selection rationale:
        - 7d, 15d: EGARCH captures leverage effects and asymmetric shocks
          (bad news increases volatility more than good news)
        - 30d, 90d: GARCH(1,1) provides smoother, symmetric volatility
          (mean reversion dominates over longer horizons)

        Args:
            horizon_days: Forecast horizon in days

        Returns:
            GARCHConfig with horizon-appropriate model type
        """
        if horizon_days <= 15:
            # Short-term: EGARCH for asymmetric volatility
            return cls(
                horizon_days=horizon_days,
                model_type="EGARCH",
                p=1,
                q=1,
                vol_scaling=100.0
            )
        else:
            # Long-term: GARCH for symmetric volatility
            return cls(
                horizon_days=horizon_days,
                model_type="GARCH",
                p=1,
                q=1,
                vol_scaling=100.0
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GARCHConfig:
        """Create config from dictionary."""
        return cls(**data)


@dataclass
class VolatilityForecast:
    """Container for volatility forecast results."""

    forecast_date: datetime
    horizon_days: int
    volatility: float  # Forecasted standard deviation
    confidence_intervals: Dict[str, Tuple[float, float]]  # {"1sigma": (lower, upper), ...}
    regime: VolatilityRegime
    historical_mean_vol: float
    model_type: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'forecast_date': self.forecast_date.isoformat(),
            'horizon_days': self.horizon_days,
            'volatility': float(self.volatility),
            'confidence_intervals': {
                k: (float(v[0]), float(v[1])) for k, v in self.confidence_intervals.items()
            },
            'regime': self.regime.value,
            'historical_mean_vol': float(self.historical_mean_vol),
            'model_type': self.model_type
        }


class GARCHVolatility:
    """
    GARCH/EGARCH volatility forecaster for confidence interval estimation.

    This class fits GARCH or EGARCH models on residuals from point forecasters
    (XGBoost, SARIMAX) to generate volatility forecasts and confidence intervals.

    Key Features:
    - Automatic model selection (GARCH vs EGARCH) based on horizon
    - Volatility regime detection
    - Multi-step volatility forecasting
    - Robust convergence handling
    - Model persistence

    Example:
        >>> from datetime import datetime
        >>> import numpy as np
        >>>
        >>> # Create volatility model for 7-day horizon
        >>> vol_model = GARCHVolatility(horizon_days=7)
        >>>
        >>> # Fit on residuals from point forecaster
        >>> residuals = np.random.randn(252)  # 1 year of daily residuals
        >>> vol_model.fit(residuals)
        >>>
        >>> # Forecast volatility and get confidence intervals
        >>> point_forecast = 950.0  # USD/CLP forecast
        >>> vol_forecast = vol_model.forecast_volatility(point_forecast, steps=7)
        >>>
        >>> print(f"Volatility: {vol_forecast.volatility:.2f}")
        >>> print(f"Regime: {vol_forecast.regime.value}")
        >>> print(f"95% CI: {vol_forecast.confidence_intervals['2sigma']}")
    """

    def __init__(
        self,
        horizon_days: int,
        config: Optional[GARCHConfig] = None
    ):
        """
        Initialize GARCH/EGARCH volatility model.

        Args:
            horizon_days: Forecast horizon in days
            config: Optional custom configuration (defaults to horizon-specific)
        """
        self.horizon_days = horizon_days
        self.config = config or GARCHConfig.from_horizon(horizon_days)
        self.model = None
        self.fitted_model = None
        self.historical_mean_vol: Optional[float] = None
        self.training_residuals: Optional[np.ndarray] = None

        logger.info(
            f"Initialized {self.config.model_type} volatility model for {horizon_days}d horizon"
        )

    def fit(
        self,
        residuals: np.ndarray,
        max_iter: int = 1000,
        show_warning: bool = False
    ) -> GARCHVolatility:
        """
        Fit GARCH/EGARCH model on residuals.

        Args:
            residuals: Residuals from point forecaster (1D array)
            max_iter: Maximum iterations for optimization
            show_warning: Whether to show arch library warnings

        Returns:
            Self for method chaining

        Raises:
            ValueError: If residuals are invalid or model fails to converge
        """
        # Validate input
        residuals = np.asarray(residuals).flatten()

        if len(residuals) < 30:
            raise ValueError(
                f"Insufficient data: need at least 30 observations, got {len(residuals)}"
            )

        if np.any(np.isnan(residuals)) or np.any(np.isinf(residuals)):
            logger.warning(f"Found {np.isnan(residuals).sum()} NaN and {np.isinf(residuals).sum()} inf values")
            residuals = residuals[~(np.isnan(residuals) | np.isinf(residuals))]

        if len(residuals) < 30:
            raise ValueError("Too many invalid values in residuals after cleaning")

        # Store training data
        self.training_residuals = residuals.copy()

        # Scale residuals for numerical stability (GARCH works better with larger numbers)
        scaled_residuals = residuals * self.config.vol_scaling

        # Calculate historical mean volatility
        self.historical_mean_vol = np.std(residuals)

        try:
            # Create model specification
            if self.config.model_type == "EGARCH":
                # EGARCH: Log(volatility^2) = constant + leverage + GARCH terms
                # Better for asymmetric shocks (bad news > good news impact)
                self.model = arch_model(
                    scaled_residuals,
                    mean='Zero',  # Residuals should have zero mean
                    vol='EGARCH',
                    p=self.config.p,
                    q=self.config.q,
                    dist='Normal'
                )
            else:
                # GARCH: variance = constant + ARCH terms + GARCH terms
                # Simpler, symmetric volatility model
                self.model = arch_model(
                    scaled_residuals,
                    mean='Zero',
                    vol='GARCH',
                    p=self.config.p,
                    q=self.config.q,
                    dist='Normal'
                )

            # Fit model
            with warnings.catch_warnings():
                if not show_warning:
                    warnings.filterwarnings('ignore')

                self.fitted_model = self.model.fit(
                    update_freq=0,  # Suppress iteration output
                    disp='off',
                    options={'maxiter': max_iter}
                )

            # Validate convergence
            if not hasattr(self.fitted_model, 'conditional_volatility'):
                raise ValueError("Model fitting failed: no conditional_volatility attribute")

            # Check for negative variance (should not happen with proper constraints)
            fitted_vol = self.fitted_model.conditional_volatility
            if np.any(fitted_vol <= 0) or np.any(np.isnan(fitted_vol)):
                raise ValueError("Model produced invalid volatility values")

            logger.info(
                f"{self.config.model_type}({self.config.p},{self.config.q}) fitted successfully. "
                f"Mean vol: {self.historical_mean_vol:.4f}, "
                f"Log-likelihood: {self.fitted_model.loglikelihood:.2f}"
            )

            return self

        except Exception as e:
            logger.error(f"GARCH fitting failed: {str(e)}")
            raise ValueError(f"Failed to fit {self.config.model_type} model: {str(e)}")

    def forecast_volatility(
        self,
        point_forecast: float,
        steps: Optional[int] = None,
        forecast_date: Optional[datetime] = None
    ) -> VolatilityForecast:
        """
        Generate volatility forecast and confidence intervals.

        Args:
            point_forecast: Point forecast from ensemble (e.g., 950 CLP)
            steps: Number of steps ahead (defaults to horizon_days)
            forecast_date: Date of forecast (defaults to now)

        Returns:
            VolatilityForecast with volatility and confidence intervals

        Raises:
            ValueError: If model not fitted or forecast fails
        """
        if self.fitted_model is None:
            raise ValueError("Model not fitted. Call fit() first.")

        steps = steps or self.horizon_days
        forecast_date = forecast_date or datetime.now()

        try:
            # Generate volatility forecast
            # Returns variance forecast, need to take sqrt
            vol_forecast = self.fitted_model.forecast(horizon=steps, reindex=False)

            # Extract variance forecast (last value in forecast path)
            # variance is in scaled units, convert back
            variance = vol_forecast.variance.values[-1, -1]  # Last step
            volatility_scaled = np.sqrt(variance)
            volatility = volatility_scaled / self.config.vol_scaling

            # Calculate confidence intervals
            # For normal distribution: ±1σ = 68%, ±2σ = 95%, ±3σ = 99.7%
            ci_1sigma = (
                point_forecast - volatility,
                point_forecast + volatility
            )
            ci_2sigma = (
                point_forecast - 2 * volatility,
                point_forecast + 2 * volatility
            )
            ci_3sigma = (
                point_forecast - 3 * volatility,
                point_forecast + 3 * volatility
            )

            confidence_intervals = {
                '1sigma': ci_1sigma,  # 68% confidence
                '2sigma': ci_2sigma,  # 95% confidence
                '3sigma': ci_3sigma   # 99.7% confidence
            }

            # Detect volatility regime
            regime = self.detect_regime(volatility)

            result = VolatilityForecast(
                forecast_date=forecast_date,
                horizon_days=steps,
                volatility=volatility,
                confidence_intervals=confidence_intervals,
                regime=regime,
                historical_mean_vol=self.historical_mean_vol,
                model_type=self.config.model_type
            )

            logger.info(
                f"Volatility forecast: {volatility:.4f} (regime: {regime.value}), "
                f"95% CI: [{ci_2sigma[0]:.2f}, {ci_2sigma[1]:.2f}]"
            )

            return result

        except Exception as e:
            logger.error(f"Volatility forecasting failed: {str(e)}")
            raise ValueError(f"Failed to generate volatility forecast: {str(e)}")

    def detect_regime(self, volatility: float) -> VolatilityRegime:
        """
        Detect volatility regime based on historical context.

        Regime classification:
        - LOW: volatility < 0.5 × historical mean (calm markets)
        - NORMAL: 0.5-1.5 × historical mean (typical conditions)
        - HIGH: 1.5-2.5 × historical mean (elevated uncertainty)
        - EXTREME: >2.5 × historical mean (crisis/shock)

        Args:
            volatility: Current volatility estimate

        Returns:
            VolatilityRegime classification
        """
        if self.historical_mean_vol is None:
            logger.warning("No historical volatility available, defaulting to NORMAL regime")
            return VolatilityRegime.NORMAL

        ratio = volatility / self.historical_mean_vol

        if ratio < self.config.regime_low_threshold:
            return VolatilityRegime.LOW
        elif ratio < self.config.regime_normal_upper:
            return VolatilityRegime.NORMAL
        elif ratio < self.config.regime_high_upper:
            return VolatilityRegime.HIGH
        else:
            return VolatilityRegime.EXTREME

    def get_confidence_intervals(
        self,
        point_forecast: float,
        volatility: Optional[float] = None
    ) -> Dict[str, Tuple[float, float]]:
        """
        Calculate confidence intervals for a point forecast.

        Convenience method that can use either:
        1. Provided volatility value
        2. Last forecasted volatility (if available)

        Args:
            point_forecast: Point forecast value
            volatility: Optional volatility (uses last forecast if None)

        Returns:
            Dictionary with confidence intervals
        """
        if volatility is None:
            if self.fitted_model is None:
                raise ValueError("No volatility available. Provide volatility or call forecast_volatility()")

            # Use last fitted conditional volatility
            cond_vol = self.fitted_model.conditional_volatility
            if isinstance(cond_vol, pd.Series):
                fitted_vol = cond_vol.iloc[-1]
            else:
                fitted_vol = cond_vol[-1]
            volatility = fitted_vol / self.config.vol_scaling

        return {
            '1sigma': (point_forecast - volatility, point_forecast + volatility),
            '2sigma': (point_forecast - 2 * volatility, point_forecast + 2 * volatility),
            '3sigma': (point_forecast - 3 * volatility, point_forecast + 3 * volatility)
        }

    def save_model(self, filepath: Path) -> None:
        """
        Save fitted model and configuration to disk.

        Saves both the fitted GARCH/EGARCH model and metadata for reproducibility.

        Args:
            filepath: Path to save model (will create .pkl and .json files)
        """
        if self.fitted_model is None:
            raise ValueError("No fitted model to save. Call fit() first.")

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Save model object
        model_path = filepath.with_suffix('.pkl')
        with open(model_path, 'wb') as f:
            pickle.dump({
                'fitted_model': self.fitted_model,
                'model_spec': self.model,
                'historical_mean_vol': self.historical_mean_vol,
                'training_residuals': self.training_residuals
            }, f)

        # Save metadata
        metadata = {
            'saved_at': datetime.now().isoformat(),
            'horizon_days': self.horizon_days,
            'config': self.config.to_dict(),
            'n_observations': len(self.training_residuals) if self.training_residuals is not None else 0,
            'historical_mean_vol': float(self.historical_mean_vol) if self.historical_mean_vol else None,
            'model_summary': {
                'aic': float(self.fitted_model.aic),
                'bic': float(self.fitted_model.bic),
                'loglikelihood': float(self.fitted_model.loglikelihood),
                'num_params': int(self.fitted_model.num_params)
            }
        }

        metadata_path = filepath.with_suffix('.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Model saved to {model_path} and {metadata_path}")

    def load_model(self, filepath: Path) -> GARCHVolatility:
        """
        Load fitted model from disk.

        Args:
            filepath: Path to model file (without extension)

        Returns:
            Self for method chaining
        """
        filepath = Path(filepath)
        model_path = filepath.with_suffix('.pkl')
        metadata_path = filepath.with_suffix('.json')

        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        # Load model
        with open(model_path, 'rb') as f:
            data = pickle.load(f)
            self.fitted_model = data['fitted_model']
            self.model = data['model_spec']
            self.historical_mean_vol = data['historical_mean_vol']
            self.training_residuals = data['training_residuals']

        # Load metadata
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                self.config = GARCHConfig.from_dict(metadata['config'])
                self.horizon_days = metadata['horizon_days']

        logger.info(f"Model loaded from {model_path}")
        return self

    def get_diagnostics(self) -> Dict[str, Any]:
        """
        Get model diagnostics and fit statistics.

        Returns:
            Dictionary with diagnostic information
        """
        if self.fitted_model is None:
            raise ValueError("Model not fitted. Call fit() first.")

        return {
            'model_type': self.config.model_type,
            'order': f"({self.config.p}, {self.config.q})",
            'horizon_days': self.horizon_days,
            'n_observations': len(self.training_residuals) if self.training_residuals is not None else 0,
            'historical_mean_vol': float(self.historical_mean_vol) if self.historical_mean_vol else None,
            'fit_statistics': {
                'aic': float(self.fitted_model.aic),
                'bic': float(self.fitted_model.bic),
                'loglikelihood': float(self.fitted_model.loglikelihood),
                'num_params': int(self.fitted_model.num_params)
            },
            'parameters': {
                name: float(value)
                for name, value in self.fitted_model.params.items()
            }
        }
