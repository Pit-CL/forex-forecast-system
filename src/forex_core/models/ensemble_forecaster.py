"""
Ensemble Forecaster for USD/CLP Multi-Horizon Forecasting.

This module combines XGBoost, SARIMAX, and GARCH/EGARCH models using weighted
averaging with horizon-specific weights. Designed following KISS principle for
simplicity and maintainability.

Weighted Ensemble Strategy (from implementation plan):
- 7d:  XGBoost 60%, SARIMAX 40% + EGARCH volatility
- 15d: XGBoost 50%, SARIMAX 50% + EGARCH volatility
- 30d: SARIMAX 60%, XGBoost 40% + GARCH volatility
- 90d: SARIMAX 70%, XGBoost 30% + GARCH volatility

Features:
- Simple weighted average (no complex meta-learning)
- Automatic fallback if one model fails
- Performance tracking per model
- Confidence intervals from GARCH/EGARCH
- Model persistence with metadata
"""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Import project models
from forex_core.models.xgboost_forecaster import XGBoostForecaster, XGBoostConfig
from forex_core.models.sarimax_forecaster import SARIMAXForecaster, SARIMAXConfig
from forex_core.models.garch_volatility import GARCHVolatility, GARCHConfig

# Import logger
from forex_core.utils.logging import logger

warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)


@dataclass
class EnsembleWeights:
    """Horizon-specific weights for ensemble components."""

    horizon_days: int
    xgboost_weight: float
    sarimax_weight: float
    volatility_model: str  # "GARCH" or "EGARCH"

    @classmethod
    def from_horizon(cls, horizon_days: int) -> EnsembleWeights:
        """
        Get horizon-specific ensemble weights.

        Based on implementation plan:
        - Short horizons (7d, 15d): XGBoost dominates + EGARCH
        - Long horizons (30d, 90d): SARIMAX dominates + GARCH

        Args:
            horizon_days: Forecast horizon in days

        Returns:
            EnsembleWeights with appropriate configuration
        """
        if horizon_days <= 7:
            return cls(
                horizon_days=horizon_days,
                xgboost_weight=0.6,
                sarimax_weight=0.4,
                volatility_model="EGARCH"
            )
        elif horizon_days <= 15:
            return cls(
                horizon_days=horizon_days,
                xgboost_weight=0.5,
                sarimax_weight=0.5,
                volatility_model="EGARCH"
            )
        elif horizon_days <= 30:
            return cls(
                horizon_days=horizon_days,
                xgboost_weight=0.4,
                sarimax_weight=0.6,
                volatility_model="GARCH"
            )
        else:  # 90d
            return cls(
                horizon_days=horizon_days,
                xgboost_weight=0.3,
                sarimax_weight=0.7,
                volatility_model="GARCH"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class EnsembleMetrics:
    """Performance metrics for ensemble and individual models."""

    # Ensemble metrics
    ensemble_rmse: float
    ensemble_mae: float
    ensemble_mape: float
    ensemble_directional_accuracy: float

    # Individual model metrics
    xgboost_rmse: float
    xgboost_mae: float
    sarimax_rmse: float
    sarimax_mae: float

    # Model contributions
    xgboost_weight_used: float
    sarimax_weight_used: float

    # Training info
    train_size: int
    test_size: int
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class EnsembleForecast:
    """Container for ensemble forecast results."""

    dates: pd.DatetimeIndex
    ensemble_forecast: np.ndarray
    xgboost_forecast: Optional[np.ndarray]
    sarimax_forecast: Optional[np.ndarray]

    # Confidence intervals from GARCH/EGARCH
    lower_1sigma: np.ndarray
    upper_1sigma: np.ndarray
    lower_2sigma: np.ndarray
    upper_2sigma: np.ndarray

    # Metadata
    horizon_days: int
    weights_used: Dict[str, float]
    volatility_model: str
    volatility_regime: str

    def to_dataframe(self) -> pd.DataFrame:
        """Convert to DataFrame for easy export."""
        df = pd.DataFrame({
            'date': self.dates,
            'ensemble_forecast': self.ensemble_forecast,
            'lower_68pct': self.lower_1sigma,
            'upper_68pct': self.upper_1sigma,
            'lower_95pct': self.lower_2sigma,
            'upper_95pct': self.upper_2sigma,
        })

        # Add individual model forecasts if available
        if self.xgboost_forecast is not None:
            df['xgboost_forecast'] = self.xgboost_forecast

        if self.sarimax_forecast is not None:
            df['sarimax_forecast'] = self.sarimax_forecast

        df.set_index('date', inplace=True)
        return df


class EnsembleForecaster:
    """
    Weighted ensemble of XGBoost, SARIMAX, and GARCH/EGARCH models.

    Simple and transparent approach:
    1. Train XGBoost and SARIMAX independently
    2. Combine predictions with horizon-specific fixed weights
    3. Fit GARCH/EGARCH on ensemble residuals
    4. Generate confidence intervals from volatility model
    5. Track performance of each component

    Key Features:
    - Fixed weights (no complex optimization)
    - Automatic fallback if one model fails
    - Clear individual model contributions
    - Comprehensive error handling

    Example:
        >>> from pathlib import Path
        >>> import pandas as pd
        >>>
        >>> # Initialize for 7-day horizon
        >>> ensemble = EnsembleForecaster(horizon_days=7)
        >>>
        >>> # Train on historical data
        >>> data = pd.read_csv('usdclp_data.csv', index_col='date', parse_dates=True)
        >>> metrics = ensemble.train(data, target_col='close')
        >>>
        >>> # Generate forecast
        >>> forecast = ensemble.predict(data, steps=7)
        >>> print(forecast.to_dataframe())
        >>>
        >>> # Save trained models
        >>> ensemble.save_models(Path('./models/ensemble_7d'))
    """

    def __init__(
        self,
        horizon_days: int,
        weights: Optional[EnsembleWeights] = None,
        xgboost_config: Optional[XGBoostConfig] = None,
        sarimax_config: Optional[SARIMAXConfig] = None,
        garch_config: Optional[GARCHConfig] = None
    ):
        """
        Initialize ensemble forecaster.

        Args:
            horizon_days: Forecast horizon in days (7, 15, 30, 90)
            weights: Custom weights (defaults to horizon-specific)
            xgboost_config: XGBoost configuration (optional)
            sarimax_config: SARIMAX configuration (optional)
            garch_config: GARCH configuration (optional)
        """
        self.horizon_days = horizon_days
        self.weights = weights or EnsembleWeights.from_horizon(horizon_days)

        # Initialize individual models
        self.xgboost = XGBoostForecaster(
            xgboost_config or XGBoostConfig.from_horizon(horizon_days)
        )
        self.sarimax = SARIMAXForecaster(
            sarimax_config or SARIMAXConfig.from_horizon(horizon_days)
        )
        self.garch = GARCHVolatility(
            horizon_days=horizon_days,
            config=garch_config or GARCHConfig.from_horizon(horizon_days)
        )

        # Track which models are fitted
        self.xgboost_fitted = False
        self.sarimax_fitted = False
        self.garch_fitted = False

        # Performance tracking
        self.training_metrics: Optional[EnsembleMetrics] = None
        self.ensemble_residuals: Optional[np.ndarray] = None

        logger.info(
            f"Initialized EnsembleForecaster for {horizon_days}d horizon "
            f"(XGBoost: {self.weights.xgboost_weight:.0%}, "
            f"SARIMAX: {self.weights.sarimax_weight:.0%}, "
            f"Volatility: {self.weights.volatility_model})"
        )

    def train(
        self,
        data: pd.DataFrame,
        target_col: str = 'close',
        exog_data: Optional[pd.DataFrame] = None,
        validation_split: float = 0.2,
        verbose: bool = True
    ) -> EnsembleMetrics:
        """
        Train ensemble: XGBoost, SARIMAX, then GARCH on residuals.

        Training process:
        1. Train XGBoost on engineered features
        2. Train SARIMAX with exogenous variables
        3. Generate ensemble predictions on validation set
        4. Calculate residuals
        5. Fit GARCH/EGARCH on residuals for confidence intervals
        6. Evaluate performance

        Args:
            data: Training data with OHLCV and features
            target_col: Target column name (default: 'close')
            exog_data: Exogenous variables for SARIMAX (optional)
            validation_split: Fraction for validation (default: 0.2)
            verbose: Print training progress (default: True)

        Returns:
            EnsembleMetrics with performance of ensemble and components

        Raises:
            ValueError: If both models fail to train
        """
        if verbose:
            logger.info(f"Training ensemble for {self.horizon_days}d horizon...")

        # Validate input
        if len(data) < 100:
            raise ValueError(f"Insufficient data: {len(data)} rows (need >= 100)")

        if target_col not in data.columns:
            raise ValueError(f"Target column '{target_col}' not found")

        # Split data for validation
        split_idx = int(len(data) * (1 - validation_split))
        train_data = data.iloc[:split_idx]
        val_data = data.iloc[split_idx:]

        if exog_data is not None:
            exog_train = exog_data.iloc[:split_idx]
            exog_val = exog_data.iloc[split_idx:]
        else:
            exog_train = None
            exog_val = None

        # Track predictions and errors
        xgb_pred = None
        sarimax_pred = None
        xgb_error = None
        sarimax_error = None

        # ========================================
        # 1. Train XGBoost
        # ========================================
        try:
            if verbose:
                logger.info("Training XGBoost model...")

            xgb_metrics = self.xgboost.train(
                train_data,
                target_col=target_col,
                validation_split=validation_split,
                verbose=False
            )
            self.xgboost_fitted = True

            # Get validation predictions
            xgb_forecast = self.xgboost.predict(val_data.iloc[:-self.horizon_days], steps=self.horizon_days)
            xgb_pred = np.repeat(xgb_forecast['forecast'].values[0], len(val_data))

            if verbose:
                logger.info(f"XGBoost trained: RMSE={xgb_metrics.rmse:.2f}, MAE={xgb_metrics.mae:.2f}")

        except Exception as e:
            logger.error(f"XGBoost training failed: {str(e)}")
            xgb_error = str(e)
            self.xgboost_fitted = False

        # ========================================
        # 2. Train SARIMAX
        # ========================================
        try:
            if verbose:
                logger.info("Training SARIMAX model...")

            sarimax_metrics = self.sarimax.train(
                train_data,
                target_col=target_col,
                exog_data=exog_train,
                validation_split=validation_split,
                auto_select_order=True
            )
            self.sarimax_fitted = True

            # Get validation predictions
            sarimax_forecast = self.sarimax.predict(
                steps=len(val_data),
                exog_forecast=exog_val,
                return_conf_int=False
            )
            sarimax_pred = sarimax_forecast['forecast'].values

            if verbose:
                logger.info(f"SARIMAX trained: RMSE={sarimax_metrics.rmse:.2f}, MAE={sarimax_metrics.mae:.2f}")

        except Exception as e:
            logger.error(f"SARIMAX training failed: {str(e)}")
            sarimax_error = str(e)
            self.sarimax_fitted = False

        # ========================================
        # 3. Check if at least one model succeeded
        # ========================================
        if not self.xgboost_fitted and not self.sarimax_fitted:
            raise ValueError(
                f"Both models failed to train.\n"
                f"XGBoost error: {xgb_error}\n"
                f"SARIMAX error: {sarimax_error}"
            )

        # ========================================
        # 4. Create ensemble predictions
        # ========================================
        actual_values = val_data[target_col].values

        # Apply fallback logic
        if self.xgboost_fitted and self.sarimax_fitted:
            # Both models available: use weighted average
            ensemble_pred = (
                self.weights.xgboost_weight * xgb_pred +
                self.weights.sarimax_weight * sarimax_pred
            )
            weights_used = {
                'xgboost': self.weights.xgboost_weight,
                'sarimax': self.weights.sarimax_weight
            }

        elif self.xgboost_fitted:
            # Only XGBoost: use 100%
            logger.warning("SARIMAX failed, using XGBoost only (100%)")
            ensemble_pred = xgb_pred
            weights_used = {'xgboost': 1.0, 'sarimax': 0.0}

        else:
            # Only SARIMAX: use 100%
            logger.warning("XGBoost failed, using SARIMAX only (100%)")
            ensemble_pred = sarimax_pred
            weights_used = {'xgboost': 0.0, 'sarimax': 1.0}

        # ========================================
        # 5. Fit GARCH on ensemble residuals
        # ========================================
        self.ensemble_residuals = actual_values - ensemble_pred

        try:
            if verbose:
                logger.info(f"Fitting {self.weights.volatility_model} on ensemble residuals...")

            self.garch.fit(self.ensemble_residuals, show_warning=False)
            self.garch_fitted = True

            if verbose:
                logger.info(f"{self.weights.volatility_model} fitted successfully")

        except Exception as e:
            logger.warning(f"GARCH fitting failed: {str(e)}. Confidence intervals will use rolling std.")
            self.garch_fitted = False

        # ========================================
        # 6. Calculate metrics
        # ========================================
        ensemble_rmse = np.sqrt(mean_squared_error(actual_values, ensemble_pred))
        ensemble_mae = mean_absolute_error(actual_values, ensemble_pred)
        ensemble_mape = np.mean(np.abs((actual_values - ensemble_pred) / (actual_values + 1e-10))) * 100

        # Directional accuracy
        if len(actual_values) > 1:
            true_direction = np.sign(np.diff(actual_values))
            pred_direction = np.sign(np.diff(ensemble_pred))
            ensemble_dir_acc = np.mean(true_direction == pred_direction) * 100
        else:
            ensemble_dir_acc = 0.0

        # Individual model metrics (if available)
        xgb_rmse = np.sqrt(mean_squared_error(actual_values, xgb_pred)) if xgb_pred is not None else 0.0
        xgb_mae = mean_absolute_error(actual_values, xgb_pred) if xgb_pred is not None else 0.0
        sarimax_rmse = np.sqrt(mean_squared_error(actual_values, sarimax_pred)) if sarimax_pred is not None else 0.0
        sarimax_mae = mean_absolute_error(actual_values, sarimax_pred) if sarimax_pred is not None else 0.0

        # Create metrics object
        self.training_metrics = EnsembleMetrics(
            ensemble_rmse=ensemble_rmse,
            ensemble_mae=ensemble_mae,
            ensemble_mape=ensemble_mape,
            ensemble_directional_accuracy=ensemble_dir_acc,
            xgboost_rmse=xgb_rmse,
            xgboost_mae=xgb_mae,
            sarimax_rmse=sarimax_rmse,
            sarimax_mae=sarimax_mae,
            xgboost_weight_used=weights_used['xgboost'],
            sarimax_weight_used=weights_used['sarimax'],
            train_size=len(train_data),
            test_size=len(val_data)
        )

        if verbose:
            logger.info(f"Ensemble training complete:")
            logger.info(f"  Ensemble: RMSE={ensemble_rmse:.2f}, MAE={ensemble_mae:.2f}, MAPE={ensemble_mape:.2f}%")
            logger.info(f"  XGBoost:  RMSE={xgb_rmse:.2f}, MAE={xgb_mae:.2f}")
            logger.info(f"  SARIMAX:  RMSE={sarimax_rmse:.2f}, MAE={sarimax_mae:.2f}")
            logger.info(f"  Directional Accuracy: {ensemble_dir_acc:.1f}%")

        return self.training_metrics

    def predict(
        self,
        data: pd.DataFrame,
        steps: Optional[int] = None,
        exog_forecast: Optional[pd.DataFrame] = None
    ) -> EnsembleForecast:
        """
        Generate ensemble forecast with confidence intervals.

        Process:
        1. Get predictions from XGBoost and SARIMAX
        2. Combine with weighted average
        3. Calculate confidence intervals from GARCH/EGARCH
        4. Package results

        Args:
            data: Input data for forecasting
            steps: Number of steps to forecast (defaults to horizon_days)
            exog_forecast: Future exogenous variables for SARIMAX (optional)

        Returns:
            EnsembleForecast with predictions and confidence intervals

        Raises:
            RuntimeError: If no models are fitted
        """
        if not self.xgboost_fitted and not self.sarimax_fitted:
            raise RuntimeError("No models trained. Call train() first.")

        steps = steps or self.horizon_days

        # ========================================
        # 1. Get individual predictions
        # ========================================
        xgb_pred = None
        sarimax_pred = None

        if self.xgboost_fitted:
            try:
                xgb_forecast = self.xgboost.predict(data, steps=steps)
                xgb_pred = xgb_forecast['forecast'].values
            except Exception as e:
                logger.error(f"XGBoost prediction failed: {str(e)}")
                self.xgboost_fitted = False

        if self.sarimax_fitted:
            try:
                sarimax_forecast = self.sarimax.predict(
                    steps=steps,
                    exog_forecast=exog_forecast,
                    return_conf_int=False
                )
                sarimax_pred = sarimax_forecast['forecast'].values
            except Exception as e:
                logger.error(f"SARIMAX prediction failed: {str(e)}")
                self.sarimax_fitted = False

        # Check if at least one prediction succeeded
        if xgb_pred is None and sarimax_pred is None:
            raise RuntimeError("Both models failed during prediction")

        # ========================================
        # 2. Create ensemble prediction
        # ========================================
        if xgb_pred is not None and sarimax_pred is not None:
            # Both available: weighted average
            ensemble_pred = (
                self.weights.xgboost_weight * xgb_pred +
                self.weights.sarimax_weight * sarimax_pred
            )
            weights_used = {
                'xgboost': self.weights.xgboost_weight,
                'sarimax': self.weights.sarimax_weight
            }

        elif xgb_pred is not None:
            # XGBoost only
            logger.warning("Using XGBoost only (SARIMAX unavailable)")
            ensemble_pred = xgb_pred
            weights_used = {'xgboost': 1.0, 'sarimax': 0.0}

        else:
            # SARIMAX only
            logger.warning("Using SARIMAX only (XGBoost unavailable)")
            ensemble_pred = sarimax_pred
            weights_used = {'xgboost': 0.0, 'sarimax': 1.0}

        # ========================================
        # 3. Calculate confidence intervals
        # ========================================
        if self.garch_fitted:
            # Use GARCH/EGARCH for confidence intervals
            try:
                vol_forecast = self.garch.forecast_volatility(
                    point_forecast=ensemble_pred.mean(),
                    steps=steps
                )

                # Apply volatility to all forecast points
                volatility = vol_forecast.volatility
                lower_1sigma = ensemble_pred - volatility
                upper_1sigma = ensemble_pred + volatility
                lower_2sigma = ensemble_pred - 2 * volatility
                upper_2sigma = ensemble_pred + 2 * volatility

                volatility_regime = vol_forecast.regime.value

            except Exception as e:
                logger.warning(f"GARCH forecast failed: {str(e)}. Using rolling std.")
                self.garch_fitted = False

        if not self.garch_fitted:
            # Fallback: use rolling std from training residuals
            if self.ensemble_residuals is not None:
                rolling_std = np.std(self.ensemble_residuals)
            else:
                # Last resort: 1% of forecast
                rolling_std = ensemble_pred.mean() * 0.01

            lower_1sigma = ensemble_pred - rolling_std
            upper_1sigma = ensemble_pred + rolling_std
            lower_2sigma = ensemble_pred - 2 * rolling_std
            upper_2sigma = ensemble_pred + 2 * rolling_std

            volatility_regime = "unknown"

        # ========================================
        # 4. Create result object
        # ========================================
        last_date = data.index[-1]
        forecast_dates = pd.date_range(
            start=last_date + pd.Timedelta(days=1),
            periods=steps,
            freq='D'
        )

        result = EnsembleForecast(
            dates=forecast_dates,
            ensemble_forecast=ensemble_pred,
            xgboost_forecast=xgb_pred,
            sarimax_forecast=sarimax_pred,
            lower_1sigma=lower_1sigma,
            upper_1sigma=upper_1sigma,
            lower_2sigma=lower_2sigma,
            upper_2sigma=upper_2sigma,
            horizon_days=self.horizon_days,
            weights_used=weights_used,
            volatility_model=self.weights.volatility_model,
            volatility_regime=volatility_regime
        )

        logger.info(
            f"Ensemble forecast generated: {ensemble_pred.mean():.2f} CLP "
            f"(95% CI: [{lower_2sigma.mean():.2f}, {upper_2sigma.mean():.2f}])"
        )

        return result

    def get_model_contributions(self) -> Dict[str, Any]:
        """
        Get detailed breakdown of ensemble components for transparency.

        Returns:
            Dictionary with model status, weights, and performance
        """
        contributions = {
            'horizon_days': self.horizon_days,
            'weights': self.weights.to_dict(),
            'model_status': {
                'xgboost_fitted': self.xgboost_fitted,
                'sarimax_fitted': self.sarimax_fitted,
                'garch_fitted': self.garch_fitted
            }
        }

        if self.training_metrics:
            contributions['performance'] = self.training_metrics.to_dict()

        if self.xgboost_fitted and self.xgboost.training_metrics:
            contributions['xgboost_metrics'] = self.xgboost.training_metrics.to_dict()

        if self.sarimax_fitted and self.sarimax.training_metrics:
            contributions['sarimax_metrics'] = self.sarimax.training_metrics.to_dict()

        if self.garch_fitted:
            contributions['garch_diagnostics'] = self.garch.get_diagnostics()

        return contributions

    def evaluate(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> EnsembleMetrics:
        """
        Evaluate ensemble performance on test data.

        Args:
            y_true: Actual values
            y_pred: Predicted values

        Returns:
            EnsembleMetrics with performance scores
        """
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1e-10))) * 100

        # Directional accuracy
        if len(y_true) > 1:
            true_direction = np.sign(np.diff(y_true))
            pred_direction = np.sign(np.diff(y_pred))
            dir_acc = np.mean(true_direction == pred_direction) * 100
        else:
            dir_acc = 0.0

        return EnsembleMetrics(
            ensemble_rmse=rmse,
            ensemble_mae=mae,
            ensemble_mape=mape,
            ensemble_directional_accuracy=dir_acc,
            xgboost_rmse=0.0,  # Not available in evaluation mode
            xgboost_mae=0.0,
            sarimax_rmse=0.0,
            sarimax_mae=0.0,
            xgboost_weight_used=self.weights.xgboost_weight,
            sarimax_weight_used=self.weights.sarimax_weight,
            train_size=0,
            test_size=len(y_true)
        )

    def save_models(self, path: Path, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Save all ensemble components to disk.

        Saves:
        - XGBoost model (if fitted)
        - SARIMAX model (if fitted)
        - GARCH model (if fitted)
        - Ensemble metadata (weights, metrics, configuration)

        Args:
            path: Directory to save models
            metadata: Additional metadata to include
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        # Save individual models
        if self.xgboost_fitted:
            xgb_path = path / "xgboost"
            self.xgboost.save_model(xgb_path)

        if self.sarimax_fitted:
            sarimax_path = path / "sarimax"
            self.sarimax.save_model(sarimax_path)

        if self.garch_fitted:
            garch_path = path / "garch_model"
            self.garch.save_model(garch_path)

        # Save ensemble metadata
        ensemble_meta = {
            'saved_at': datetime.now().isoformat(),
            'horizon_days': self.horizon_days,
            'weights': self.weights.to_dict(),
            'model_status': {
                'xgboost_fitted': self.xgboost_fitted,
                'sarimax_fitted': self.sarimax_fitted,
                'garch_fitted': self.garch_fitted
            },
            'training_metrics': self.training_metrics.to_dict() if self.training_metrics else None,
            'model_version': '1.0.0'
        }

        if metadata:
            ensemble_meta.update(metadata)

        meta_path = path / "ensemble_metadata.json"
        with open(meta_path, 'w') as f:
            json.dump(ensemble_meta, f, indent=2)

        logger.info(f"Ensemble models saved to {path}")

    def load_models(self, path: Path) -> None:
        """
        Load all ensemble components from disk.

        Args:
            path: Directory containing saved models

        Raises:
            FileNotFoundError: If path doesn't exist or missing critical files
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Model path not found: {path}")

        # Load ensemble metadata
        meta_path = path / "ensemble_metadata.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"Ensemble metadata not found: {meta_path}")

        with open(meta_path, 'r') as f:
            meta = json.load(f)
            self.horizon_days = meta['horizon_days']
            self.weights = EnsembleWeights(**meta['weights'])

            if meta.get('training_metrics'):
                self.training_metrics = EnsembleMetrics(**meta['training_metrics'])

        # Load individual models (if available)
        xgb_path = path / "xgboost"
        if xgb_path.exists():
            try:
                self.xgboost.load_model(xgb_path)
                self.xgboost_fitted = True
                logger.info("XGBoost model loaded")
            except Exception as e:
                logger.warning(f"Failed to load XGBoost: {str(e)}")
                self.xgboost_fitted = False

        sarimax_path = path / "sarimax"
        if sarimax_path.exists():
            try:
                self.sarimax.load_model(sarimax_path)
                self.sarimax_fitted = True
                logger.info("SARIMAX model loaded")
            except Exception as e:
                logger.warning(f"Failed to load SARIMAX: {str(e)}")
                self.sarimax_fitted = False

        garch_path = path / "garch_model"
        if garch_path.exists():
            try:
                self.garch.load_model(garch_path)
                self.garch_fitted = True
                logger.info("GARCH model loaded")
            except Exception as e:
                logger.warning(f"Failed to load GARCH: {str(e)}")
                self.garch_fitted = False

        if not self.xgboost_fitted and not self.sarimax_fitted:
            raise ValueError("No models could be loaded from the specified path")

        logger.info(f"Ensemble models loaded from {path}")


# Example usage and testing
if __name__ == "__main__":
    from pathlib import Path

    # Create sample data
    dates = pd.date_range(start='2023-01-01', end='2024-11-14', freq='D')
    np.random.seed(42)

    sample_data = pd.DataFrame({
        'close': np.random.randn(len(dates)).cumsum() + 900,
        'high': np.random.randn(len(dates)).cumsum() + 905,
        'low': np.random.randn(len(dates)).cumsum() + 895,
        'copper_price': np.random.randn(len(dates)).cumsum() + 4.0,
        'dxy_index': np.random.randn(len(dates)).cumsum() + 100,
        'vix': np.abs(np.random.randn(len(dates)).cumsum() + 15),
        'tpm': np.clip(np.random.randn(len(dates)).cumsum() + 5, 0, 15),
    }, index=dates)

    # Exogenous variables
    exog_data = sample_data[['copper_price', 'dxy_index', 'vix', 'tpm']].copy()

    # Test 7-day ensemble
    logger.info("Testing 7-day ensemble forecaster...")
    ensemble_7d = EnsembleForecaster(horizon_days=7)

    # Train
    logger.info("\n" + "="*60)
    logger.info("TRAINING ENSEMBLE")
    logger.info("="*60)
    metrics = ensemble_7d.train(
        sample_data,
        target_col='close',
        exog_data=exog_data,
        verbose=True
    )

    print(f"\nTraining Metrics:")
    print(f"  Ensemble RMSE: {metrics.ensemble_rmse:.2f}")
    print(f"  Ensemble MAE:  {metrics.ensemble_mae:.2f}")
    print(f"  Ensemble MAPE: {metrics.ensemble_mape:.2f}%")
    print(f"  Directional Accuracy: {metrics.ensemble_directional_accuracy:.1f}%")
    print(f"\nModel Contributions:")
    print(f"  XGBoost: {metrics.xgboost_weight_used:.0%} (RMSE: {metrics.xgboost_rmse:.2f})")
    print(f"  SARIMAX: {metrics.sarimax_weight_used:.0%} (RMSE: {metrics.sarimax_rmse:.2f})")

    # Predict
    logger.info("\n" + "="*60)
    logger.info("GENERATING FORECAST")
    logger.info("="*60)

    # Future exog (assume constant)
    future_exog = pd.DataFrame({
        'copper_price': [4.0] * 7,
        'dxy_index': [100.0] * 7,
        'vix': [15.0] * 7,
        'tpm': [5.0] * 7,
    })

    forecast = ensemble_7d.predict(
        sample_data,
        steps=7,
        exog_forecast=future_exog
    )

    print(f"\n7-Day Ensemble Forecast:")
    print(forecast.to_dataframe())

    # Get model contributions
    logger.info("\n" + "="*60)
    logger.info("MODEL CONTRIBUTIONS")
    logger.info("="*60)
    contributions = ensemble_7d.get_model_contributions()
    print(json.dumps(contributions, indent=2, default=str))

    # Save models
    save_path = Path("./models/ensemble_7d")
    ensemble_7d.save_models(save_path)
    logger.info(f"\nEnsemble saved to {save_path}")

    # Test loading
    logger.info("\n" + "="*60)
    logger.info("TESTING MODEL LOADING")
    logger.info("="*60)
    ensemble_loaded = EnsembleForecaster(horizon_days=7)
    ensemble_loaded.load_models(save_path)

    # Generate forecast with loaded model
    forecast_loaded = ensemble_loaded.predict(sample_data, steps=7, exog_forecast=future_exog)
    print(f"\nForecast from loaded model:")
    print(forecast_loaded.to_dataframe().head())

    logger.info("\n✅ All tests passed!")
