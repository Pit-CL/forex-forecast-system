"""
Walk-Forward Validation System for Forex Forecasting.

Implementa validación walk-forward (time-series cross-validation) para
evaluar performance de modelos en condiciones realistas, respetando
el orden temporal de los datos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

from forex_core.data.loader import DataBundle, DataLoader
from forex_core.data.models import ForecastPackage


class ValidationMode(str, Enum):
    """Modo de validación walk-forward."""

    EXPANDING = "expanding"  # Expanding window (baseline crece)
    ROLLING = "rolling"  # Rolling window (baseline fijo)


@dataclass
class ValidationMetrics:
    """
    Métricas de validación para un fold específico.

    Attributes:
        fold: Número del fold.
        train_start: Fecha inicio del periodo de entrenamiento.
        train_end: Fecha fin del periodo de entrenamiento.
        test_start: Fecha inicio del periodo de prueba.
        test_end: Fecha fin del periodo de prueba.
        n_train: Observaciones en entrenamiento.
        n_test: Observaciones en prueba.
        rmse: Root Mean Squared Error.
        mae: Mean Absolute Error.
        mape: Mean Absolute Percentage Error.
        ci95_coverage: % de observaciones dentro del IC 95%.
        bias: Sesgo promedio (predicted - actual).
        forecast_values: Valores predichos.
        actual_values: Valores reales.
        ci95_low: Límite inferior IC 95%.
        ci95_high: Límite superior IC 95%.
    """

    fold: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    n_train: int
    n_test: int
    rmse: float
    mae: float
    mape: float
    ci95_coverage: float
    bias: float
    forecast_values: np.ndarray
    actual_values: np.ndarray
    ci95_low: np.ndarray
    ci95_high: np.ndarray

    def to_dict(self) -> dict:
        """Convert metrics to dictionary (excluding arrays)."""
        return {
            "fold": self.fold,
            "train_start": self.train_start,
            "train_end": self.train_end,
            "test_start": self.test_start,
            "test_end": self.test_end,
            "n_train": self.n_train,
            "n_test": self.n_test,
            "rmse": self.rmse,
            "mae": self.mae,
            "mape": self.mape,
            "ci95_coverage": self.ci95_coverage,
            "bias": self.bias,
        }


@dataclass
class ValidationReport:
    """
    Reporte completo de validación walk-forward.

    Attributes:
        horizon: Horizonte validado (7d, 15d, etc.).
        mode: Modo de validación (expanding/rolling).
        n_folds: Número de folds ejecutados.
        fold_metrics: Lista de métricas por fold.
        avg_rmse: RMSE promedio.
        avg_mae: MAE promedio.
        avg_mape: MAPE promedio.
        avg_ci95_coverage: Cobertura IC 95% promedio.
        avg_bias: Sesgo promedio.
        std_rmse: Desviación estándar de RMSE.
        std_mae: Desviación estándar de MAE.
        best_fold: Fold con mejor performance (menor RMSE).
        worst_fold: Fold con peor performance (mayor RMSE).
        timestamp: Cuándo se generó el reporte.
        total_duration_seconds: Duración total de validación.
    """

    horizon: str
    mode: ValidationMode
    n_folds: int
    fold_metrics: list[ValidationMetrics]
    avg_rmse: float
    avg_mae: float
    avg_mape: float
    avg_ci95_coverage: float
    avg_bias: float
    std_rmse: float
    std_mae: float
    best_fold: int
    worst_fold: int
    timestamp: datetime
    total_duration_seconds: float

    def is_acceptable(
        self,
        rmse_threshold: float = 50.0,
        mape_threshold: float = 5.0,
        ci_coverage_min: float = 0.85,
    ) -> bool:
        """
        Determina si la performance es aceptable.

        Args:
            rmse_threshold: RMSE máximo aceptable.
            mape_threshold: MAPE máximo aceptable (%).
            ci_coverage_min: Cobertura IC mínima aceptable.

        Returns:
            True si todas las métricas son aceptables.
        """
        return (
            self.avg_rmse <= rmse_threshold
            and self.avg_mape <= mape_threshold
            and self.avg_ci95_coverage >= ci_coverage_min
        )

    def to_summary_dict(self) -> dict:
        """Convert report to summary dictionary."""
        return {
            "horizon": self.horizon,
            "mode": self.mode.value,
            "n_folds": self.n_folds,
            "avg_rmse": self.avg_rmse,
            "avg_mae": self.avg_mae,
            "avg_mape": self.avg_mape,
            "avg_ci95_coverage": self.avg_ci95_coverage,
            "avg_bias": self.avg_bias,
            "std_rmse": self.std_rmse,
            "std_mae": self.std_mae,
            "best_fold": self.best_fold,
            "worst_fold": self.worst_fold,
            "is_acceptable": self.is_acceptable(),
            "timestamp": self.timestamp,
            "duration_seconds": self.total_duration_seconds,
        }


class WalkForwardValidator:
    """
    Validador walk-forward para modelos de forecasting.

    Implementa time-series cross-validation respetando el orden temporal,
    útil para evaluar performance realista de modelos en producción.
    """

    def __init__(
        self,
        forecaster_func,
        horizon_days: int,
        initial_train_days: int = 365,
        test_days: int = 30,
        step_days: int = 30,
        mode: ValidationMode = ValidationMode.EXPANDING,
        storage_path: Optional[Path] = None,
    ):
        """
        Initialize walk-forward validator.

        Args:
            forecaster_func: Función que toma (DataBundle, horizon_days) y retorna ForecastPackage.
            horizon_days: Días hacia adelante del forecast.
            initial_train_days: Días de entrenamiento inicial.
            test_days: Días de prueba por fold.
            step_days: Días de avance entre folds.
            mode: Modo de validación (expanding/rolling).
            storage_path: Path para almacenar resultados.
        """
        self.forecaster_func = forecaster_func
        self.horizon_days = horizon_days
        self.initial_train_days = initial_train_days
        self.test_days = test_days
        self.step_days = step_days
        self.mode = mode

        if storage_path is None:
            from forex_core.config import get_settings

            settings = get_settings()
            storage_path = settings.data_dir / "validation_reports"

        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"WalkForwardValidator initialized: horizon={horizon_days}d, "
            f"mode={mode.value}, initial_train={initial_train_days}d, "
            f"test={test_days}d, step={step_days}d"
        )

    def validate(
        self,
        series: pd.Series,
        max_folds: Optional[int] = None,
    ) -> ValidationReport:
        """
        Ejecuta validación walk-forward en la serie.

        Args:
            series: Serie temporal a validar (USD/CLP).
            max_folds: Máximo número de folds (None = todos posibles).

        Returns:
            ValidationReport con resultados completos.
        """
        logger.info(f"Starting walk-forward validation: {len(series)} observations")
        start_time = datetime.now()

        # Calculate folds
        folds = self._calculate_folds(series, max_folds)
        logger.info(f"Will execute {len(folds)} folds")

        if len(folds) == 0:
            logger.error("No folds available for validation")
            return self._create_empty_report()

        # Execute each fold
        fold_metrics = []
        for i, (train_idx, test_idx) in enumerate(folds, 1):
            logger.info(f"Executing fold {i}/{len(folds)}...")

            try:
                metrics = self._execute_fold(
                    fold=i,
                    series=series,
                    train_idx=train_idx,
                    test_idx=test_idx,
                )
                fold_metrics.append(metrics)

                logger.info(
                    f"Fold {i} complete: RMSE={metrics.rmse:.2f}, "
                    f"MAE={metrics.mae:.2f}, MAPE={metrics.mape:.2f}%"
                )

            except Exception as e:
                logger.error(f"Fold {i} failed: {e}")
                continue

        if not fold_metrics:
            logger.error("All folds failed")
            return self._create_empty_report()

        # Calculate aggregate metrics
        total_duration = (datetime.now() - start_time).total_seconds()
        report = self._create_report(fold_metrics, total_duration)

        logger.info(
            f"Validation complete: avg_rmse={report.avg_rmse:.2f}, "
            f"avg_mape={report.avg_mape:.2f}%, duration={total_duration:.1f}s"
        )

        return report

    def _calculate_folds(
        self,
        series: pd.Series,
        max_folds: Optional[int],
    ) -> list[tuple[np.ndarray, np.ndarray]]:
        """
        Calcula índices de train/test para cada fold.

        Returns:
            Lista de (train_indices, test_indices) para cada fold.
        """
        folds = []

        # Start after initial training period
        current_test_start = self.initial_train_days

        while current_test_start + self.test_days <= len(series):
            # Train indices
            if self.mode == ValidationMode.EXPANDING:
                # Expanding: train desde el inicio hasta antes del test
                train_idx = np.arange(0, current_test_start)
            else:
                # Rolling: train window fijo
                train_start = max(0, current_test_start - self.initial_train_days)
                train_idx = np.arange(train_start, current_test_start)

            # Test indices
            test_idx = np.arange(
                current_test_start, current_test_start + self.test_days
            )

            folds.append((train_idx, test_idx))

            # Move to next fold
            current_test_start += self.step_days

            # Check max_folds limit
            if max_folds and len(folds) >= max_folds:
                break

        return folds

    def _execute_fold(
        self,
        fold: int,
        series: pd.Series,
        train_idx: np.ndarray,
        test_idx: np.ndarray,
    ) -> ValidationMetrics:
        """
        Ejecuta un fold específico de validación.

        Args:
            fold: Número del fold.
            series: Serie completa.
            train_idx: Índices de entrenamiento.
            test_idx: Índices de prueba.

        Returns:
            ValidationMetrics para este fold.
        """
        # Get train/test data
        train_series = series.iloc[train_idx]
        test_series = series.iloc[test_idx]

        # Create bundle with train data only
        # NOTE: In production, you'd load a real DataBundle with all features
        # For now, we'll create a minimal mock bundle
        bundle = self._create_bundle(train_series)

        # Generate forecast
        forecast = self.forecaster_func(bundle, self.horizon_days)

        # Extract values from ForecastPoint series
        # Use first N days of forecast to match test period
        n_forecast = min(len(forecast.series), len(test_series))

        forecast_values = np.array([p.mean for p in forecast.series[:n_forecast]])
        ci95_low = np.array([p.ci95_low for p in forecast.series[:n_forecast]])
        ci95_high = np.array([p.ci95_high for p in forecast.series[:n_forecast]])
        actual_values = test_series.values[:n_forecast]

        # Calculate error metrics
        errors = forecast_values - actual_values
        rmse = float(np.sqrt(np.mean(errors**2)))
        mae = float(np.mean(np.abs(errors)))
        mape = float(np.mean(np.abs(errors / actual_values)) * 100)
        bias = float(np.mean(errors))

        # Calculate CI coverage
        within_ci = (actual_values >= ci95_low) & (actual_values <= ci95_high)
        ci95_coverage = float(np.mean(within_ci))

        return ValidationMetrics(
            fold=fold,
            train_start=train_series.index[0],
            train_end=train_series.index[-1],
            test_start=test_series.index[0],
            test_end=test_series.index[-1],
            n_train=len(train_series),
            n_test=len(test_series),
            rmse=rmse,
            mae=mae,
            mape=mape,
            ci95_coverage=ci95_coverage,
            bias=bias,
            forecast_values=forecast_values,
            actual_values=actual_values,
            ci95_low=ci95_low,
            ci95_high=ci95_high,
        )

    def _create_bundle(self, series: pd.Series) -> DataBundle:
        """
        Crea un DataBundle minimal para el forecast.

        NOTE: En producción, esto debería cargar un DataBundle completo
        con todas las features. Por ahora, creamos uno mínimo.
        """
        # Create minimal bundle with just USD/CLP series
        from forex_core.data.registry import SourceRegistry

        bundle = DataBundle(
            usdclp_series=series,
            copper_series=pd.Series(dtype=float),
            tpm_series=pd.Series(dtype=float),
            inflation_series=pd.Series(dtype=float),
            indicators={},
            macro_events=[],
            news=[],
            dxy_series=pd.Series(dtype=float),
            vix_series=pd.Series(dtype=float),
            eem_series=pd.Series(dtype=float),
            fed_dot_plot={},
            fed_dot_source_id=0,
            next_fomc=None,
            rate_differential=0.0,
            sources=SourceRegistry(),
            usdclp_intraday=None,
        )

        return bundle

    def _create_report(
        self,
        fold_metrics: list[ValidationMetrics],
        duration_seconds: float,
    ) -> ValidationReport:
        """Crea reporte agregado a partir de métricas de folds."""
        # Calculate aggregate statistics
        rmse_values = [m.rmse for m in fold_metrics]
        mae_values = [m.mae for m in fold_metrics]
        mape_values = [m.mape for m in fold_metrics]
        ci_coverage_values = [m.ci95_coverage for m in fold_metrics]
        bias_values = [m.bias for m in fold_metrics]

        avg_rmse = float(np.mean(rmse_values))
        avg_mae = float(np.mean(mae_values))
        avg_mape = float(np.mean(mape_values))
        avg_ci95_coverage = float(np.mean(ci_coverage_values))
        avg_bias = float(np.mean(bias_values))

        std_rmse = float(np.std(rmse_values))
        std_mae = float(np.std(mae_values))

        # Find best/worst folds
        best_fold = int(np.argmin(rmse_values)) + 1
        worst_fold = int(np.argmax(rmse_values)) + 1

        return ValidationReport(
            horizon=f"{self.horizon_days}d",
            mode=self.mode,
            n_folds=len(fold_metrics),
            fold_metrics=fold_metrics,
            avg_rmse=avg_rmse,
            avg_mae=avg_mae,
            avg_mape=avg_mape,
            avg_ci95_coverage=avg_ci95_coverage,
            avg_bias=avg_bias,
            std_rmse=std_rmse,
            std_mae=std_mae,
            best_fold=best_fold,
            worst_fold=worst_fold,
            timestamp=datetime.now(),
            total_duration_seconds=duration_seconds,
        )

    def _create_empty_report(self) -> ValidationReport:
        """Crea reporte vacío cuando no hay datos suficientes."""
        return ValidationReport(
            horizon=f"{self.horizon_days}d",
            mode=self.mode,
            n_folds=0,
            fold_metrics=[],
            avg_rmse=0.0,
            avg_mae=0.0,
            avg_mape=0.0,
            avg_ci95_coverage=0.0,
            avg_bias=0.0,
            std_rmse=0.0,
            std_mae=0.0,
            best_fold=0,
            worst_fold=0,
            timestamp=datetime.now(),
            total_duration_seconds=0.0,
        )

    def save_report(
        self,
        report: ValidationReport,
        filename: Optional[str] = None,
    ) -> Path:
        """
        Guarda reporte de validación a disco.

        Args:
            report: Reporte a guardar.
            filename: Nombre de archivo (opcional).

        Returns:
            Path al archivo guardado.
        """
        if filename is None:
            timestamp = report.timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"validation_{report.horizon}_{report.mode.value}_{timestamp}.parquet"

        filepath = self.storage_path / filename

        # Convert to DataFrame
        summary = report.to_summary_dict()

        # Add fold-level metrics
        fold_data = []
        for metrics in report.fold_metrics:
            fold_data.append(metrics.to_dict())

        # Save summary
        summary_df = pd.DataFrame([summary])
        summary_path = self.storage_path / f"summary_{filename}"
        summary_df.to_parquet(summary_path, index=False)

        # Save fold metrics
        if fold_data:
            folds_df = pd.DataFrame(fold_data)
            folds_df.to_parquet(filepath, index=False)

        logger.info(f"Validation report saved to {filepath}")

        return filepath


__all__ = [
    "WalkForwardValidator",
    "ValidationReport",
    "ValidationMetrics",
    "ValidationMode",
]
