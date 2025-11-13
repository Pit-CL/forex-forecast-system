"""
Unified forecasting engine for forex time series.

This module provides the ForecastEngine class which orchestrates:
- Model selection (ARIMA+GARCH, VAR, Random Forest)
- Horizon-aware resampling (daily for 7d, monthly for 12m)
- Ensemble combination with inverse RMSE weighting
- Metrics logging and artifact tracking

The engine supports both short-term (7-day) and long-term (12-month)
forecasting through parameterized frequency handling.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, TYPE_CHECKING, Literal

import numpy as np
import pandas as pd
import psutil
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

from .arima import auto_select_arima_order, fit_arima, forecast_arima
from .garch import fit_garch, forecast_garch_volatility
from .var import fit_var, forecast_var, var_price_reconstruction
from .ensemble import ModelResult, EnsembleArtifacts, compute_weights, combine_forecasts
from .metrics import calculate_rmse, calculate_mape
from ..data.models import ForecastPackage, ForecastPoint
from ..utils.logging import get_logger

if TYPE_CHECKING:
    from ..data.loader import DataBundle
    from ..config.base import ForecastConfig

logger = get_logger(__name__)


class ForecastEngine:
    """
    Unified forecasting engine for forex time series.

    This class orchestrates the complete forecasting pipeline:
    1. Data preparation (resampling based on horizon)
    2. Model fitting (ARIMA+GARCH, VAR, Random Forest)
    3. Ensemble combination (inverse RMSE weighting)
    4. Metrics logging and artifact tracking

    Supports two modes:
    - Daily forecasting (7-day horizon)
    - Monthly forecasting (12-month horizon)

    Attributes:
        config: Forecast configuration (model selection, parameters).
        horizon: Forecast horizon type ("daily" or "monthly").
        steps: Number of steps to forecast.

    Example:
        >>> from forex_core.data.loader import load_data
        >>> from forex_core.config.base import ForecastConfig
        >>> config = ForecastConfig(
        ...     enable_arima=True,
        ...     enable_var=True,
        ...     enable_rf=False,
        ...     ensemble_window=30
        ... )
        >>> engine = ForecastEngine(config, horizon="daily", steps=7)
        >>> bundle = load_data()
        >>> forecast, artifacts = engine.forecast(bundle)
        >>> print(f"7-day forecast: {forecast.series[-1].mean:.2f}")
    """

    def __init__(
        self,
        config: ForecastConfig,
        horizon: Literal["daily", "monthly"] = "daily",
        steps: int = 7
    ):
        """
        Initialize ForecastEngine.

        Args:
            config: Forecast configuration object.
            horizon: "daily" for 7d forecasts, "monthly" for 12m forecasts.
            steps: Number of steps to forecast (7 for daily, 12 for monthly).
        """
        self.config = config
        self.horizon = horizon
        self.steps = steps

    def forecast(
        self,
        bundle: DataBundle
    ) -> Tuple[ForecastPackage, EnsembleArtifacts]:
        """
        Generate ensemble forecast from DataBundle.

        This method:
        1. Resamples data based on horizon (daily/monthly)
        2. Fits enabled models
        3. Computes ensemble weights (inverse RMSE)
        4. Combines forecasts
        5. Logs metrics and returns artifacts

        Args:
            bundle: DataBundle with historical data and indicators.

        Returns:
            Tuple of (ensemble_forecast, artifacts).

        Raises:
            RuntimeError: If no models execute successfully.

        Example:
            >>> forecast, artifacts = engine.forecast(bundle)
            >>> print(f"Weights: {artifacts.weights}")
            >>> print(f"ARIMA order: {artifacts.arima_order}")
        """
        # Resample series based on horizon
        usdclp_series = self._resample_series(bundle.usdclp_series)

        # Fit models
        results: Dict[str, ModelResult] = {}

        if self.config.enable_arima:
            try:
                results["arima_garch"] = self._run_arima_garch(
                    usdclp_series, self.steps
                )
            except Exception as exc:
                logger.warning(f"ARIMA+GARCH failed: {exc}")

        if self.config.enable_var:
            try:
                results["var"] = self._run_var(bundle, usdclp_series, self.steps)
            except Exception as exc:
                logger.warning(f"VAR failed: {exc}")

        if self.config.enable_rf:
            try:
                results["random_forest"] = self._run_random_forest(
                    bundle, usdclp_series, self.steps
                )
            except Exception as exc:
                logger.warning(f"Random Forest failed: {exc}")

        if self.config.enable_chronos:
            try:
                results["chronos"] = self._run_chronos(usdclp_series, self.steps)
            except Exception as exc:
                logger.warning(f"Chronos failed: {exc}")

        if not results:
            raise RuntimeError("No models executed successfully.")

        # Compute ensemble weights
        weights = compute_weights(results, self.config.ensemble_window)

        # Combine forecasts
        ensemble_package = combine_forecasts(results, weights, self.steps)

        # Create artifacts
        artifacts = EnsembleArtifacts(
            weights=weights,
            component_metrics={
                name: {"RMSE": res.rmse, "MAPE": res.mape, **res.extras}
                for name, res in results.items()
            },
            arima_order=(
                results["arima_garch"].extras.get("order_tuple")
                if "arima_garch" in results else None
            ),
        )

        # Log metrics
        if hasattr(self.config, 'metrics_log_path'):
            self._log_metrics(weights, results, ensemble_package)

        return ensemble_package, artifacts

    def _resample_series(self, series: pd.Series) -> pd.Series:
        """Resample series based on horizon (daily/monthly)."""
        if self.horizon == "monthly":
            # Remove timezone if present
            if series.index.tz is not None:
                series = series.tz_convert("UTC").tz_localize(None)
            # Resample to month-end
            monthly = series.resample("ME").last().dropna()
            return monthly
        else:
            # Daily - return as-is
            return series

    def _run_arima_garch(
        self,
        series: pd.Series,
        steps: int
    ) -> ModelResult:
        """Run ARIMA+GARCH model."""
        # Convert to log returns
        log_returns = np.log(series).diff().dropna()

        # Auto-select ARIMA order
        order = auto_select_arima_order(log_returns, max_p=2, max_q=2)

        # Fit ARIMA
        arima_model = fit_arima(log_returns, order)

        # Forecast mean
        price_path, mean_returns = forecast_arima(
            arima_model, steps, last_price=series.iloc[-1]
        )

        # Fit GARCH for volatility
        garch_model = fit_garch(log_returns, p=1, q=1)
        sigma = forecast_garch_volatility(garch_model, horizon=steps)

        # Build forecast points
        points = self._build_points(series.index[-1], price_path, sigma)

        # Calculate metrics
        window = min(self.config.ensemble_window, len(arima_model.resid))
        rmse = calculate_rmse(
            arima_model.resid.tail(window),
            np.zeros(window),
            window=None
        )
        denom = log_returns.replace(0, np.nan)
        mape = float(np.nanmean(np.abs(arima_model.resid / denom)))

        package = ForecastPackage(
            series=points,
            methodology=f"ARIMA({order[0]},0,{order[2]}) + GARCH(1,1)",
            error_metrics={"RMSE": rmse, "MAPE": mape},
            residual_vol=float(np.std(arima_model.resid)),
        )

        return ModelResult(
            name="arima_garch",
            package=package,
            rmse=rmse,
            mape=mape,
            extras={"order_p": order[0], "order_q": order[2], "order_tuple": order},
        )

    def _run_var(
        self,
        bundle: DataBundle,
        usdclp_series: pd.Series,
        steps: int
    ) -> ModelResult:
        """Run VAR model."""
        # Build macro frame
        frame = self._build_macro_frame(bundle, usdclp_series.index)

        # Differencing (percentage changes)
        diff_df = frame.pct_change().dropna()

        if len(diff_df) < 10:
            raise RuntimeError("Insufficient data for VAR.")

        # Fit VAR
        maxlags = min(5, len(diff_df) - 1)
        var_model = fit_var(diff_df, maxlags=maxlags)

        # Forecast
        forecast_df = forecast_var(var_model, steps=steps)

        # Reconstruct prices
        price_path = var_price_reconstruction(
            forecast_df,
            target_col="usdclp",
            last_price=frame["usdclp"].iloc[-1]
        )

        # Volatility estimate
        resid = var_model.resid["usdclp"].dropna()
        std = np.full(steps, resid.std())

        # Build points
        points = self._build_points(frame.index[-1], price_path, std)

        # Metrics
        window = min(self.config.ensemble_window, len(resid))
        rmse = calculate_rmse(
            resid.tail(window),
            np.zeros(window),
            window=None
        )
        mape = float(np.mean(np.abs(resid.tail(window))))

        package = ForecastPackage(
            series=points,
            methodology="VAR(2) sobre retornos (usdclp/cobre/dxy/tpm)",
            error_metrics={"RMSE": rmse, "MAPE": mape},
            residual_vol=float(resid.std()),
        )

        return ModelResult(
            name="var",
            package=package,
            rmse=rmse,
            mape=mape,
            extras={"lag_order": var_model.k_ar},
        )

    def _run_random_forest(
        self,
        bundle: DataBundle,
        usdclp_series: pd.Series,
        steps: int
    ) -> ModelResult:
        """Run Random Forest model."""
        # Build feature frame
        df = self._build_feature_frame(bundle, usdclp_series.index)
        target = df.pop("target")
        feature_cols = df.columns.tolist()

        # Scale features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(df)

        # Train RF
        model = RandomForestRegressor(
            n_estimators=400,
            random_state=42,
            max_depth=10
        )
        model.fit(features_scaled, target)

        # In-sample predictions for metrics
        preds_in_sample = model.predict(features_scaled)
        resid = target - preds_in_sample

        window = min(self.config.ensemble_window, len(resid))
        rmse = calculate_rmse(
            resid.tail(window),
            np.zeros(window),
            window=None
        )
        mape = calculate_mape(target.tail(window), preds_in_sample[-window:])

        # Multi-step forecast
        future_path = []
        std_series = np.full(steps, resid.std())
        current_df = df.copy()
        current_target = target.copy()

        # Determine time offset
        if self.horizon == "monthly":
            time_offset = pd.offsets.MonthEnd(1)
        else:
            time_offset = pd.Timedelta(days=1)

        for _ in range(steps):
            latest_features = self._next_feature_row(
                current_df, current_target, feature_cols
            )
            scaled = scaler.transform(latest_features[feature_cols])
            pred = float(model.predict(scaled)[0])
            future_path.append(pred)

            next_idx = current_target.index[-1] + time_offset
            current_target = pd.concat([
                current_target,
                pd.Series([pred], index=[next_idx])
            ])
            latest_features.index = [next_idx]
            current_df = pd.concat([current_df, latest_features[feature_cols]])

        # Build points
        points = self._build_points(usdclp_series.index[-1], future_path, std_series)

        package = ForecastPackage(
            series=points,
            methodology="RandomForest (lags USD/CLP + cobre + DXY + TPM)",
            error_metrics={"RMSE": rmse, "MAPE": mape},
            residual_vol=float(resid.std()),
        )

        return ModelResult(
            name="random_forest",
            package=package,
            rmse=rmse,
            mape=mape,
            extras={"estimators": 400},
        )

    def _run_chronos(
        self,
        series: pd.Series,
        steps: int
    ) -> ModelResult:
        """Run Chronos-Bolt-Small deep learning model."""
        # Check available memory before loading model
        available_memory_mb = psutil.virtual_memory().available / (1024 * 1024)
        required_memory_mb = 800  # Conservative estimate

        if available_memory_mb < required_memory_mb:
            raise MemoryError(
                f"Insufficient memory for Chronos: {available_memory_mb:.0f}MB "
                f"available, {required_memory_mb}MB required"
            )

        logger.info(
            f"Running Chronos model (available RAM: {available_memory_mb:.0f}MB)"
        )

        # Determine context length based on horizon
        # Short-term (7d, 15d): 180 days (6 months)
        # Medium-term (30d): 90 days (3 months)
        # Long-term (90d+): 365 days (1 year)
        if steps <= 15:
            context_length = 180
        elif steps <= 30:
            context_length = 90
        else:
            context_length = 365

        # Import Chronos module (lazy loading to avoid startup overhead)
        try:
            from .chronos_model import forecast_chronos
        except ImportError as exc:
            logger.error("chronos_model module not found or dependencies missing")
            raise ImportError(
                "Chronos integration requires: pip install chronos-forecasting"
            ) from exc

        # Generate forecast
        package = forecast_chronos(
            series=series,
            steps=steps,
            context_length=context_length,
            num_samples=100,  # Good balance of accuracy vs speed
            temperature=1.0,
            validate=True,
            validation_window=30,
        )

        # Extract metrics from package
        rmse = package.error_metrics.get("pseudo_RMSE", 0.0)
        mape = package.error_metrics.get("pseudo_MAPE", 0.0)

        # If validation failed (NaN), use conservative fallback
        if np.isnan(rmse) or rmse == 0.0:
            # Estimate based on residual volatility
            rmse = package.residual_vol * 1.5
            logger.warning(
                f"Chronos validation failed, using fallback RMSE: {rmse:.4f}"
            )

        if np.isnan(mape) or mape == 0.0:
            mape = rmse / series.mean()

        return ModelResult(
            name="chronos",
            package=package,
            rmse=rmse,
            mape=mape,
            extras={
                "context_length": context_length,
                "num_samples": 100,
                "model_variant": "chronos-bolt-small",
            },
        )

    def _build_points(
        self,
        last_index: pd.Timestamp,
        price_path: list | np.ndarray,
        std: np.ndarray | list
    ) -> list[ForecastPoint]:
        """
        Build ForecastPoint list from price path and volatility.

        Uses t-distribution critical values instead of normal distribution
        to account for estimation uncertainty and achieve proper CI coverage.

        For confidence intervals, we use:
        - t-distribution with df=30 (conservative, reflects typical training data)
        - CI_80: mean ± t(0.90, df=30) * std
        - CI_95: mean ± t(0.975, df=30) * std

        This accounts for:
        1. Parameter uncertainty (we estimate std from finite samples)
        2. Non-normality in forex returns (t has fatter tails)
        3. Small sample effects in validation

        References:
        - Student's t-distribution for finite sample inference
        - Box, G.E.P., Jenkins, G.M. (1976). Time Series Analysis
        """
        from scipy import stats

        if not isinstance(std, np.ndarray):
            std = np.array(std)

        # Degrees of freedom for t-distribution
        # Use df=30 as conservative estimate (typical training window)
        # This gives wider intervals than normal distribution
        df = 30

        # Critical values from t-distribution
        # t(0.90, df=30) ≈ 1.310 (vs z=1.282 for normal)
        # t(0.975, df=30) ≈ 2.042 (vs z=1.96 for normal)
        t_80 = stats.t.ppf(0.90, df=df)
        t_95 = stats.t.ppf(0.975, df=df)

        # Generate dates based on horizon
        if self.horizon == "monthly":
            start = last_index + pd.offsets.MonthEnd(1)
            dates = pd.date_range(start, periods=len(price_path), freq="ME")
        else:
            dates = pd.date_range(
                last_index + pd.Timedelta(days=1),
                periods=len(price_path),
                freq="D"
            )

        points = []
        for i, price in enumerate(price_path):
            std_price = abs(std[i]) if i < len(std) else abs(std[-1])
            points.append(
                ForecastPoint(
                    date=dates[i].to_pydatetime(),
                    mean=float(price),
                    ci80_low=float(price - t_80 * std_price),
                    ci80_high=float(price + t_80 * std_price),
                    ci95_low=float(price - t_95 * std_price),
                    ci95_high=float(price + t_95 * std_price),
                    std_dev=float(std_price),
                )
            )
        return points

    def _build_macro_frame(
        self,
        bundle: DataBundle,
        index: pd.DatetimeIndex
    ) -> pd.DataFrame:
        """Build macro dataframe for VAR model."""
        if self.horizon == "monthly":
            usd = bundle.usdclp_series.resample("ME").last()
            frame = pd.DataFrame({"usdclp": usd.reindex(index, method="ffill")})

            def align(series: pd.Series) -> pd.Series:
                monthly = series.resample("ME").last().reindex(index, method="ffill")
                return monthly.bfill()
        else:
            frame = pd.DataFrame({"usdclp": bundle.usdclp_series})

            def align(series: pd.Series) -> pd.Series:
                aligned = series.reindex(index, method="ffill")
                return aligned.bfill()

        frame["copper"] = align(bundle.copper_series)
        frame["dxy"] = align(bundle.dxy_series)
        frame["tpm"] = align(bundle.tpm_series)
        return frame.dropna()

    def _build_feature_frame(
        self,
        bundle: DataBundle,
        index: pd.DatetimeIndex,
        max_lag: int = 5
    ) -> pd.DataFrame:
        """Build feature dataframe for Random Forest."""
        frame = self._build_macro_frame(bundle, index)

        # Create lagged features
        for lag in range(1, max_lag + 1):
            frame[f"usd_lag_{lag}"] = frame["usdclp"].shift(lag)
            frame[f"copper_lag_{lag}"] = frame["copper"].shift(lag)
            frame[f"dxy_lag_{lag}"] = frame["dxy"].shift(lag)

        frame["target"] = frame["usdclp"]
        frame = frame.dropna()
        return frame

    def _next_feature_row(
        self,
        features: pd.DataFrame,
        target: pd.Series,
        feature_cols: list[str],
        max_lag: int = 5
    ) -> pd.DataFrame:
        """Build next feature row for iterative forecasting."""
        data = {}
        for lag in range(1, max_lag + 1):
            data[f"usd_lag_{lag}"] = target.iloc[-lag]
            data[f"copper_lag_{lag}"] = features["copper"].iloc[-lag]
            data[f"dxy_lag_{lag}"] = features["dxy"].iloc[-lag]

        data["usdclp"] = target.iloc[-1]
        data["copper"] = features["copper"].iloc[-1]
        data["dxy"] = features["dxy"].iloc[-1]
        data["tpm"] = features["tpm"].iloc[-1]

        row = pd.DataFrame([data])
        row = row.reindex(columns=feature_cols, fill_value=0.0)

        if self.horizon == "monthly":
            row.index = [target.index[-1] + pd.offsets.MonthEnd(1)]
        else:
            row.index = [target.index[-1] + pd.Timedelta(days=1)]

        return row

    def _log_metrics(
        self,
        weights: Dict[str, float],
        results: Dict[str, ModelResult],
        package: ForecastPackage
    ) -> None:
        """Log metrics to file."""
        log_path = Path(self.config.metrics_log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "horizon": self.horizon,
            "steps": self.steps,
            "weights": weights,
            "models": {
                name: {"RMSE": res.rmse, "MAPE": res.mape}
                for name, res in results.items()
            },
            "final_mean": package.series[-1].mean,
        }

        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")


__all__ = ["ForecastEngine"]
