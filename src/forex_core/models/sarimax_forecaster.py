"""
SARIMAX Forecaster for USD/CLP Multi-Horizon Forecasting.

This module implements a SARIMAX-based forecasting system with:
- Seasonal ARIMA with exogenous variables
- Auto-ARIMA for order selection using AIC/BIC
- Multi-horizon support (7d, 15d, 30d, 90d)
- Stationarity testing and handling
- Seasonal pattern detection
- Comprehensive residual diagnostics
- Model persistence and versioning

SARIMAX model specification:
    ARIMA(p,d,q)(P,D,Q)[s] with exogenous variables
    where:
    - (p,d,q): Non-seasonal (AR order, differencing, MA order)
    - (P,D,Q): Seasonal (AR order, differencing, MA order)
    - [s]: Seasonal period (7 for weekly, 30 for monthly)
    - X: Exogenous variables (copper, DXY, VIX, TPM, Fed Funds)

The forecaster is designed for production use with comprehensive error handling,
logging, and integration with the ensemble system.
"""

from __future__ import annotations

import json
import pickle
import warnings
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.statespace.sarimax import SARIMAX, SARIMAXResults
from statsmodels.tsa.stattools import adfuller, acf, pacf

# Import loguru logger from project utils
from forex_core.utils.logging import logger

# Optional: pmdarima for Auto-ARIMA
try:
    from pmdarima import auto_arima
    PMDARIMA_AVAILABLE = True
except ImportError:
    PMDARIMA_AVAILABLE = False
    logger.warning("pmdarima not available. Using grid search for order selection.")

warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)


@dataclass
class SARIMAXConfig:
    """Configuration for SARIMAX forecaster with horizon-specific defaults."""

    horizon_days: int
    p: int = 1  # Non-seasonal AR order
    d: int = 1  # Non-seasonal differencing
    q: int = 1  # Non-seasonal MA order
    P: int = 1  # Seasonal AR order
    D: int = 0  # Seasonal differencing
    Q: int = 1  # Seasonal MA order
    s: int = 7  # Seasonal period (7=weekly, 30=monthly)

    # Exogenous variables to include
    exog_vars: List[str] = None

    # Model selection
    selection_metric: str = 'aic'  # 'aic' or 'bic'

    # Stationarity
    enforce_stationarity: bool = True
    enforce_invertibility: bool = True

    # Order search bounds (for auto-ARIMA)
    max_p: int = 5
    max_d: int = 2
    max_q: int = 5
    max_P: int = 2
    max_D: int = 1
    max_Q: int = 2

    def __post_init__(self):
        if self.exog_vars is None:
            self.exog_vars = []

    @classmethod
    def from_horizon(cls, horizon_days: int) -> SARIMAXConfig:
        """
        Create horizon-specific configuration with optimized defaults.

        Different horizons require different seasonal patterns and exogenous variables:
        - 7d: Short-term, weekly patterns, minimal exog variables
        - 15d: Bi-weekly patterns, moderate exog variables
        - 30d: Monthly patterns, more exog variables
        - 90d: Quarterly patterns, all exog variables

        Args:
            horizon_days: Forecast horizon in days

        Returns:
            SARIMAXConfig with horizon-appropriate defaults
        """
        if horizon_days <= 7:
            # Short-term: Weekly seasonality, few exog variables
            return cls(
                horizon_days=horizon_days,
                p=2, d=1, q=2,
                P=1, D=0, Q=1,
                s=7,  # Weekly seasonality
                exog_vars=['copper_price', 'dxy_index'],
                max_p=3, max_q=3,
                max_P=1, max_Q=1
            )
        elif horizon_days <= 15:
            # Medium-short: Weekly seasonality, moderate exog
            return cls(
                horizon_days=horizon_days,
                p=2, d=1, q=2,
                P=1, D=0, Q=1,
                s=7,  # Weekly seasonality
                exog_vars=['copper_price', 'dxy_index', 'vix'],
                max_p=4, max_q=4,
                max_P=1, max_Q=1
            )
        elif horizon_days <= 30:
            # Medium-term: Monthly seasonality, more exog
            return cls(
                horizon_days=horizon_days,
                p=3, d=1, q=3,
                P=1, D=0, Q=1,
                s=30,  # Monthly seasonality
                exog_vars=['copper_price', 'dxy_index', 'vix', 'tpm'],
                max_p=5, max_q=5,
                max_P=2, max_Q=2
            )
        else:
            # Long-term: Monthly seasonality, all exog variables
            return cls(
                horizon_days=horizon_days,
                p=3, d=1, q=3,
                P=1, D=0, Q=1,
                s=30,  # Monthly seasonality (quarterly too sparse)
                exog_vars=['copper_price', 'dxy_index', 'vix', 'tpm', 'fed_rate'],
                max_p=5, max_q=5,
                max_P=2, max_Q=2
            )


@dataclass
class ForecastMetrics:
    """Performance metrics for forecast evaluation."""

    rmse: float
    mae: float
    mape: float
    directional_accuracy: float
    train_size: int
    test_size: int
    aic: float = 0.0
    bic: float = 0.0
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


@dataclass
class StationarityTest:
    """Results from Augmented Dickey-Fuller stationarity test."""

    is_stationary: bool
    adf_statistic: float
    p_value: float
    critical_values: Dict[str, float]
    n_lags: int


@dataclass
class ResidualDiagnostics:
    """Residual diagnostics for model validation."""

    ljung_box_p_value: float
    jarque_bera_p_value: float
    mean: float
    std: float
    skewness: float
    kurtosis: float
    is_white_noise: bool
    is_normal: bool


class SARIMAXForecaster:
    """
    SARIMAX-based multi-horizon forecaster for USD/CLP exchange rate.

    Features:
    - Seasonal ARIMA with exogenous variables
    - Auto-ARIMA for order selection (using pmdarima or grid search)
    - Stationarity testing and handling (ADF test)
    - Seasonal pattern detection
    - Residual diagnostics (Ljung-Box, normality tests)
    - Model persistence with metadata
    - Comprehensive error handling and logging

    Example:
        >>> config = SARIMAXConfig.from_horizon(horizon_days=30)
        >>> forecaster = SARIMAXForecaster(config)
        >>> forecaster.train(data, target_col='close', exog_data=macro_data)
        >>> predictions = forecaster.predict(test_data, exog_forecast=future_macro, steps=30)
        >>> diagnostics = forecaster.get_diagnostics()
    """

    def __init__(self, config: SARIMAXConfig):
        """
        Initialize SARIMAX forecaster.

        Args:
            config: Configuration object with hyperparameters
        """
        self.config = config
        self.model: Optional[SARIMAXResults] = None
        self.is_fitted = False
        self.training_metrics: Optional[ForecastMetrics] = None
        self.selected_order: Optional[Tuple] = None
        self.seasonal_order: Optional[Tuple] = None
        self.exog_columns: List[str] = []
        self.target_mean: float = 0.0
        self.target_std: float = 1.0

        logger.info(f"Initialized SARIMAXForecaster for {config.horizon_days}-day horizon")

    def test_stationarity(self, series: pd.Series, max_lag: int = 20) -> StationarityTest:
        """
        Test time series stationarity using Augmented Dickey-Fuller test.

        The ADF test checks the null hypothesis that a unit root is present
        (i.e., series is non-stationary). We reject H0 if p-value < 0.05.

        Args:
            series: Time series to test
            max_lag: Maximum lag for ADF test

        Returns:
            StationarityTest object with results
        """
        # Remove any NaN values
        series_clean = series.dropna()

        if len(series_clean) < max_lag + 1:
            logger.warning(f"Insufficient data for stationarity test: {len(series_clean)} < {max_lag+1}")
            return StationarityTest(
                is_stationary=False,
                adf_statistic=0.0,
                p_value=1.0,
                critical_values={},
                n_lags=0
            )

        # Perform ADF test
        result = adfuller(series_clean, maxlag=max_lag, autolag='AIC')

        adf_stat = result[0]
        p_value = result[1]
        n_lags = result[2]
        critical_values = result[4]

        # Series is stationary if p-value < 0.05
        is_stationary = p_value < 0.05

        logger.info(f"ADF test: statistic={adf_stat:.4f}, p-value={p_value:.4f}, "
                   f"stationary={is_stationary}")

        return StationarityTest(
            is_stationary=is_stationary,
            adf_statistic=adf_stat,
            p_value=p_value,
            critical_values=critical_values,
            n_lags=n_lags
        )

    def _grid_search_order(
        self,
        endog: pd.Series,
        exog: Optional[pd.DataFrame] = None
    ) -> Tuple[Tuple[int, int, int], Tuple[int, int, int, int]]:
        """
        Grid search for best SARIMAX order using AIC/BIC.

        This is a fallback when pmdarima is not available.

        Args:
            endog: Endogenous variable (target)
            exog: Exogenous variables (optional)

        Returns:
            Tuple of ((p,d,q), (P,D,Q,s))
        """
        logger.info("Performing grid search for SARIMAX order selection...")

        best_metric = np.inf
        best_order = (self.config.p, self.config.d, self.config.q)
        best_seasonal = (self.config.P, self.config.D, self.config.Q, self.config.s)

        # Test stationarity to determine d
        stationarity = self.test_stationarity(endog)
        d_range = [0] if stationarity.is_stationary else [1, self.config.max_d]

        # Grid search over reduced space (to avoid long computation)
        p_range = range(0, min(3, self.config.max_p + 1))
        q_range = range(0, min(3, self.config.max_q + 1))
        P_range = range(0, min(2, self.config.max_P + 1))
        Q_range = range(0, min(2, self.config.max_Q + 1))

        n_models = 0
        for p in p_range:
            for d in d_range:
                for q in q_range:
                    for P in P_range:
                        for Q in Q_range:
                            try:
                                order = (p, d, q)
                                seasonal_order = (P, self.config.D, Q, self.config.s)

                                model = SARIMAX(
                                    endog,
                                    exog=exog,
                                    order=order,
                                    seasonal_order=seasonal_order,
                                    enforce_stationarity=self.config.enforce_stationarity,
                                    enforce_invertibility=self.config.enforce_invertibility
                                )

                                result = model.fit(disp=False, maxiter=100)

                                # Select based on AIC or BIC
                                metric = result.aic if self.config.selection_metric == 'aic' else result.bic

                                if metric < best_metric:
                                    best_metric = metric
                                    best_order = order
                                    best_seasonal = seasonal_order

                                n_models += 1

                            except Exception as e:
                                # Skip orders that fail to converge
                                continue

        logger.info(f"Grid search tested {n_models} models. Best: ARIMA{best_order}x{best_seasonal}, "
                   f"{self.config.selection_metric.upper()}={best_metric:.2f}")

        return best_order, best_seasonal

    def auto_arima(
        self,
        endog: pd.Series,
        exog: Optional[pd.DataFrame] = None
    ) -> Tuple[Tuple[int, int, int], Tuple[int, int, int, int]]:
        """
        Automatically select SARIMAX order using pmdarima or grid search.

        Uses pmdarima.auto_arima if available, otherwise falls back to grid search.

        Args:
            endog: Endogenous variable (target)
            exog: Exogenous variables (optional)

        Returns:
            Tuple of ((p,d,q), (P,D,Q,s))
        """
        if not PMDARIMA_AVAILABLE:
            return self._grid_search_order(endog, exog)

        try:
            logger.info("Running auto_arima for order selection...")

            model = auto_arima(
                endog,
                exogenous=exog,
                start_p=0, max_p=self.config.max_p,
                start_q=0, max_q=self.config.max_q,
                max_d=self.config.max_d,
                start_P=0, max_P=self.config.max_P,
                start_Q=0, max_Q=self.config.max_Q,
                max_D=self.config.max_D,
                seasonal=True,
                m=self.config.s,  # Seasonal period
                information_criterion=self.config.selection_metric,
                stepwise=True,  # Faster than exhaustive search
                suppress_warnings=True,
                error_action='ignore',
                trace=False,
                n_jobs=-1
            )

            order = model.order
            seasonal_order = model.seasonal_order

            logger.info(f"Auto-ARIMA selected: ARIMA{order}x{seasonal_order}, "
                       f"AIC={model.aic():.2f}, BIC={model.bic():.2f}")

            return order, seasonal_order

        except Exception as e:
            logger.warning(f"auto_arima failed: {e}. Falling back to grid search.")
            return self._grid_search_order(endog, exog)

    def _prepare_data(
        self,
        data: pd.DataFrame,
        target_col: str,
        exog_data: Optional[pd.DataFrame] = None
    ) -> Tuple[pd.Series, Optional[pd.DataFrame]]:
        """
        Prepare endogenous and exogenous data for SARIMAX.

        Args:
            data: DataFrame with target variable
            target_col: Name of target column
            exog_data: DataFrame with exogenous variables (optional)

        Returns:
            Tuple of (endog, exog)
        """
        # Extract endogenous variable
        endog = data[target_col].copy()

        # Extract exogenous variables
        exog = None
        if exog_data is not None and len(self.config.exog_vars) > 0:
            available_vars = [v for v in self.config.exog_vars if v in exog_data.columns]

            if len(available_vars) < len(self.config.exog_vars):
                missing = set(self.config.exog_vars) - set(available_vars)
                logger.warning(f"Missing exogenous variables: {missing}")

            if available_vars:
                exog = exog_data[available_vars].copy()
                self.exog_columns = available_vars
                logger.info(f"Using exogenous variables: {available_vars}")
            else:
                logger.warning("No exogenous variables available, training without exog")

        # Handle missing values
        if endog.isna().any():
            logger.warning(f"Found {endog.isna().sum()} missing values in target, forward filling")
            endog = endog.fillna(method='ffill').fillna(method='bfill')

        if exog is not None and exog.isna().any().any():
            logger.warning("Missing values in exogenous variables, forward filling")
            exog = exog.fillna(method='ffill').fillna(method='bfill')

        return endog, exog

    def train(
        self,
        data: pd.DataFrame,
        target_col: str = 'close',
        exog_data: Optional[pd.DataFrame] = None,
        auto_select_order: bool = True,
        validation_split: float = 0.2
    ) -> ForecastMetrics:
        """
        Train SARIMAX model with optional auto order selection.

        Args:
            data: Training data with target variable
            target_col: Name of target column
            exog_data: DataFrame with exogenous variables
            auto_select_order: Whether to use auto_arima for order selection
            validation_split: Fraction for validation

        Returns:
            Training metrics

        Raises:
            ValueError: If data is insufficient or invalid
        """
        try:
            # Validate input
            min_samples = max(100, self.config.s * 4)  # At least 4 seasonal periods
            if len(data) < min_samples:
                raise ValueError(f"Insufficient data: {len(data)} rows (minimum {min_samples} required)")

            if target_col not in data.columns:
                raise ValueError(f"Target column '{target_col}' not found in data")

            # Prepare data
            endog, exog = self._prepare_data(data, target_col, exog_data)

            # Store normalization parameters
            self.target_mean = endog.mean()
            self.target_std = endog.std()

            # Test stationarity
            stationarity = self.test_stationarity(endog)
            if not stationarity.is_stationary:
                logger.warning("Series is non-stationary. SARIMAX will apply differencing.")

            # Split into train/validation
            split_idx = int(len(endog) * (1 - validation_split))
            endog_train = endog.iloc[:split_idx]
            endog_val = endog.iloc[split_idx:]

            exog_train = None
            exog_val = None
            if exog is not None:
                exog_train = exog.iloc[:split_idx]
                exog_val = exog.iloc[split_idx:]

            logger.info(f"Training samples: {len(endog_train)}, Validation samples: {len(endog_val)}")

            # Auto-select order if requested
            if auto_select_order:
                self.selected_order, self.seasonal_order = self.auto_arima(endog_train, exog_train)
            else:
                self.selected_order = (self.config.p, self.config.d, self.config.q)
                self.seasonal_order = (self.config.P, self.config.D, self.config.Q, self.config.s)

            # Train SARIMAX model on full training data
            logger.info(f"Training SARIMAX{self.selected_order}x{self.seasonal_order}...")

            model = SARIMAX(
                endog_train,
                exog=exog_train,
                order=self.selected_order,
                seasonal_order=self.seasonal_order,
                enforce_stationarity=self.config.enforce_stationarity,
                enforce_invertibility=self.config.enforce_invertibility
            )

            self.model = model.fit(disp=False, maxiter=200)
            self.is_fitted = True

            # Validate on hold-out set
            forecast_result = self.model.forecast(steps=len(endog_val), exog=exog_val)
            y_pred = forecast_result.values
            y_true = endog_val.values

            # Calculate metrics
            metrics = self.evaluate(
                y_true, y_pred,
                len(endog_train), len(endog_val),
                self.model.aic, self.model.bic
            )
            self.training_metrics = metrics

            logger.info(f"Training complete. RMSE: {metrics.rmse:.2f}, MAE: {metrics.mae:.2f}, "
                       f"MAPE: {metrics.mape:.2f}%, AIC: {metrics.aic:.2f}, BIC: {metrics.bic:.2f}")

            return metrics

        except Exception as e:
            logger.error(f"Training failed: {str(e)}")
            raise

    def predict(
        self,
        steps: int,
        exog_forecast: Optional[pd.DataFrame] = None,
        return_conf_int: bool = False,
        alpha: float = 0.05
    ) -> pd.DataFrame:
        """
        Generate forecasts for specified number of steps.

        Args:
            steps: Number of steps to forecast
            exog_forecast: Future values of exogenous variables (required if model uses exog)
            return_conf_int: Whether to return confidence intervals
            alpha: Significance level for confidence intervals (default 0.05 for 95% CI)

        Returns:
            DataFrame with predictions, dates, and optional confidence intervals

        Raises:
            RuntimeError: If model is not trained
            ValueError: If exogenous forecast is required but not provided
        """
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Model must be trained before prediction. Call train() first.")

        # Validate exogenous variables
        if self.exog_columns and exog_forecast is None:
            raise ValueError(f"Model requires exogenous variables: {self.exog_columns}")

        if exog_forecast is not None:
            missing_vars = set(self.exog_columns) - set(exog_forecast.columns)
            if missing_vars:
                raise ValueError(f"Missing exogenous variables in forecast: {missing_vars}")

            if len(exog_forecast) < steps:
                raise ValueError(f"Exogenous forecast has {len(exog_forecast)} rows but {steps} steps required")

            # Use only required columns in correct order
            exog_forecast = exog_forecast[self.exog_columns].iloc[:steps]

        try:
            # Generate forecast
            logger.info(f"Generating {steps}-step SARIMAX forecast...")

            if return_conf_int:
                forecast_result = self.model.get_forecast(steps=steps, exog=exog_forecast)
                y_pred = forecast_result.predicted_mean.values
                conf_int = forecast_result.conf_int(alpha=alpha)
                lower_bound = conf_int.iloc[:, 0].values
                upper_bound = conf_int.iloc[:, 1].values
            else:
                y_pred = self.model.forecast(steps=steps, exog=exog_forecast).values
                lower_bound = None
                upper_bound = None

            # Create result DataFrame
            # Check if model has data with dates, otherwise use current date
            if hasattr(self.model, 'data') and self.model.data is not None and hasattr(self.model.data, 'dates'):
                last_date = self.model.data.dates[-1]
            else:
                last_date = datetime.now()

            forecast_dates = pd.date_range(
                start=last_date + timedelta(days=1),
                periods=steps,
                freq='D'
            )

            result = pd.DataFrame({
                'date': forecast_dates,
                'forecast': y_pred
            })

            if return_conf_int:
                result['lower_bound'] = lower_bound
                result['upper_bound'] = upper_bound
                result['confidence_level'] = (1 - alpha) * 100

            result.set_index('date', inplace=True)

            logger.info(f"Forecast complete. Mean: {y_pred.mean():.2f}, Range: [{y_pred.min():.2f}, {y_pred.max():.2f}]")

            return result

        except Exception as e:
            logger.error(f"Prediction failed: {str(e)}")
            raise

    def get_diagnostics(self) -> ResidualDiagnostics:
        """
        Perform comprehensive residual diagnostics.

        Checks:
        - Ljung-Box test for autocorrelation (white noise test)
        - Jarque-Bera test for normality
        - Descriptive statistics (mean, std, skewness, kurtosis)

        Returns:
            ResidualDiagnostics object with test results
        """
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Model must be trained before diagnostics")

        residuals = self.model.resid

        # Ljung-Box test for white noise (no autocorrelation)
        # H0: residuals are white noise (no autocorrelation)
        from statsmodels.stats.diagnostic import acorr_ljungbox
        lb_test = acorr_ljungbox(residuals, lags=min(10, len(residuals) // 5), return_df=True)
        lb_p_value = lb_test['lb_pvalue'].iloc[-1]  # Use last lag
        is_white_noise = lb_p_value > 0.05  # Fail to reject H0

        # Jarque-Bera test for normality
        # H0: residuals are normally distributed
        from statsmodels.stats.stattools import jarque_bera
        jb_stat, jb_p_value, _, _ = jarque_bera(residuals)
        is_normal = jb_p_value > 0.05  # Fail to reject H0

        # Descriptive statistics
        mean = float(residuals.mean())
        std = float(residuals.std())
        skewness = float(stats.skew(residuals))
        kurtosis = float(stats.kurtosis(residuals))

        diagnostics = ResidualDiagnostics(
            ljung_box_p_value=float(lb_p_value),
            jarque_bera_p_value=float(jb_p_value),
            mean=mean,
            std=std,
            skewness=skewness,
            kurtosis=kurtosis,
            is_white_noise=is_white_noise,
            is_normal=is_normal
        )

        logger.info(f"Diagnostics: White noise={is_white_noise} (p={lb_p_value:.4f}), "
                   f"Normal={is_normal} (p={jb_p_value:.4f})")

        return diagnostics

    def plot_diagnostics(self, save_path: Optional[Path] = None) -> None:
        """
        Generate diagnostic plots (ACF, PACF, residuals, Q-Q).

        Args:
            save_path: Path to save figure (optional)
        """
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Model must be trained before plotting diagnostics")

        try:
            import matplotlib.pyplot as plt
            from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

            residuals = self.model.resid

            fig, axes = plt.subplots(2, 2, figsize=(12, 8))

            # 1. Residuals over time
            axes[0, 0].plot(residuals)
            axes[0, 0].axhline(y=0, color='r', linestyle='--')
            axes[0, 0].set_title('Residuals over Time')
            axes[0, 0].set_xlabel('Time')
            axes[0, 0].set_ylabel('Residual')

            # 2. Histogram of residuals
            axes[0, 1].hist(residuals, bins=30, edgecolor='black', alpha=0.7)
            axes[0, 1].set_title('Residual Distribution')
            axes[0, 1].set_xlabel('Residual')
            axes[0, 1].set_ylabel('Frequency')

            # 3. ACF of residuals
            plot_acf(residuals, lags=min(40, len(residuals) // 4), ax=axes[1, 0])
            axes[1, 0].set_title('ACF of Residuals')

            # 4. Q-Q plot
            stats.probplot(residuals, dist="norm", plot=axes[1, 1])
            axes[1, 1].set_title('Q-Q Plot')

            plt.tight_layout()

            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches='tight')
                logger.info(f"Diagnostics plot saved to {save_path}")
            else:
                plt.show()

            plt.close()

        except Exception as e:
            logger.error(f"Failed to generate diagnostic plots: {e}")

    @staticmethod
    def evaluate(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        train_size: int,
        test_size: int,
        aic: float = 0.0,
        bic: float = 0.0
    ) -> ForecastMetrics:
        """
        Calculate comprehensive forecast metrics.

        Args:
            y_true: Actual values
            y_pred: Predicted values
            train_size: Number of training samples
            test_size: Number of test samples
            aic: Akaike Information Criterion
            bic: Bayesian Information Criterion

        Returns:
            ForecastMetrics object with all metrics
        """
        # Regression metrics
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)

        # MAPE (handle division by zero)
        mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1e-10))) * 100

        # Directional accuracy
        if len(y_true) > 1:
            true_direction = np.sign(np.diff(y_true))
            pred_direction = np.sign(np.diff(y_pred))
            directional_accuracy = np.mean(true_direction == pred_direction) * 100
        else:
            directional_accuracy = 0.0

        return ForecastMetrics(
            rmse=float(rmse),
            mae=float(mae),
            mape=float(mape),
            directional_accuracy=float(directional_accuracy),
            train_size=train_size,
            test_size=test_size,
            aic=float(aic),
            bic=float(bic)
        )

    def save_model(self, path: Path, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Save model and metadata to disk.

        Args:
            path: Directory path to save model
            metadata: Additional metadata to store
        """
        if not self.is_fitted:
            raise RuntimeError("Cannot save untrained model")

        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        # Save SARIMAX model
        model_path = path / "sarimax_model.pkl"
        self.model.save(model_path)

        # Save metadata
        meta = {
            'config': asdict(self.config),
            'selected_order': self.selected_order,
            'seasonal_order': self.seasonal_order,
            'exog_columns': self.exog_columns,
            'target_mean': self.target_mean,
            'target_std': self.target_std,
            'is_fitted': self.is_fitted,
            'training_metrics': self.training_metrics.to_dict() if self.training_metrics else None,
            'saved_at': datetime.now().isoformat(),
            'model_version': '1.0.0'
        }

        if metadata:
            meta.update(metadata)

        meta_path = path / "metadata.json"
        with open(meta_path, 'w') as f:
            json.dump(meta, f, indent=2)

        logger.info(f"Model saved to {path}")

    def load_model(self, path: Path) -> None:
        """
        Load model and metadata from disk.

        Args:
            path: Directory path containing saved model
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Model path not found: {path}")

        # Load SARIMAX model
        model_path = path / "sarimax_model.pkl"
        self.model = SARIMAXResults.load(model_path)

        # Load metadata
        meta_path = path / "metadata.json"
        with open(meta_path, 'r') as f:
            meta = json.load(f)
            self.selected_order = tuple(meta['selected_order'])
            self.seasonal_order = tuple(meta['seasonal_order'])
            self.exog_columns = meta['exog_columns']
            self.target_mean = meta['target_mean']
            self.target_std = meta['target_std']
            self.is_fitted = meta['is_fitted']

            if meta.get('training_metrics'):
                self.training_metrics = ForecastMetrics(**meta['training_metrics'])

        logger.info(f"Model loaded from {path}")


# Example usage and testing
if __name__ == "__main__":
    # Example: Create and train a 30-day forecaster
    config = SARIMAXConfig.from_horizon(horizon_days=30)
    forecaster = SARIMAXForecaster(config)

    # Create sample data
    dates = pd.date_range(start='2022-01-01', end='2024-11-14', freq='D')
    np.random.seed(42)

    sample_data = pd.DataFrame({
        'close': np.random.randn(len(dates)).cumsum() + 900,
    }, index=dates)

    # Exogenous variables
    exog_data = pd.DataFrame({
        'copper_price': np.random.randn(len(dates)).cumsum() + 4.0,
        'dxy_index': np.random.randn(len(dates)).cumsum() + 100,
        'vix': np.abs(np.random.randn(len(dates)).cumsum() + 15),
        'tpm': np.clip(np.random.randn(len(dates)).cumsum() + 5, 0, 15),
    }, index=dates)

    # Train
    logger.info("Training SARIMAX model...")
    metrics = forecaster.train(
        sample_data,
        target_col='close',
        exog_data=exog_data,
        auto_select_order=True
    )
    print(f"\nTraining Metrics:\n{metrics}")

    # Diagnostics
    logger.info("\nPerforming residual diagnostics...")
    diagnostics = forecaster.get_diagnostics()
    print(f"\nResidual Diagnostics:\n{diagnostics}")

    # Predict with confidence intervals
    logger.info("\nGenerating forecast...")
    future_exog = pd.DataFrame({
        'copper_price': [4.0] * 30,
        'dxy_index': [100.0] * 30,
        'vix': [15.0] * 30,
        'tpm': [5.0] * 30,
    })

    forecast = forecaster.predict(steps=30, exog_forecast=future_exog, return_conf_int=True)
    print(f"\n30-Day Forecast:\n{forecast.head(10)}")

    # Save model
    save_path = Path("./models/sarimax_30d")
    forecaster.save_model(save_path)

    logger.info(f"\nModel successfully saved to {save_path}")
