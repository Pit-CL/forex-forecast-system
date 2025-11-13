"""
Drift Trend Analysis System for Forex Forecasting.

Analiza tendencias de drift a lo largo del tiempo para identificar patrones
de empeoramiento o mejora en la calidad de los datos, permitiendo decisiones
proactivas de re-entrenamiento.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats

from forex_core.mlops.monitoring import DataDriftDetector, DriftReport, DriftSeverity


class DriftTrend(str, Enum):
    """Tendencia de drift a lo largo del tiempo."""

    STABLE = "stable"  # Drift se mantiene estable
    IMPROVING = "improving"  # Drift está mejorando
    WORSENING = "worsening"  # Drift está empeorando
    UNKNOWN = "unknown"  # Datos insuficientes para determinar


@dataclass
class DriftTrendReport:
    """
    Reporte de tendencia de drift a lo largo del tiempo.

    Attributes:
        trend: Tendencia general del drift.
        current_score: Score de drift actual (0-100).
        avg_score_30d: Score promedio últimos 30 días.
        avg_score_90d: Score promedio últimos 90 días.
        trend_slope: Pendiente de regresión lineal (positivo = empeorando).
        trend_r2: R² de la regresión (qué tan claro es el trend).
        consecutive_high: Días consecutivos con drift HIGH.
        last_stable_date: Última fecha con drift NONE.
        recommendation: Recomendación basada en tendencia.
        timestamp: Cuándo se generó el reporte.
    """

    trend: DriftTrend
    current_score: float
    avg_score_30d: float
    avg_score_90d: float
    trend_slope: float
    trend_r2: float
    consecutive_high: int
    last_stable_date: Optional[datetime]
    recommendation: str
    timestamp: datetime

    def requires_action(self) -> bool:
        """Determina si se requiere acción inmediata."""
        return (
            self.trend == DriftTrend.WORSENING
            or self.consecutive_high >= 3
            or self.current_score >= 75
        )


class DriftTrendAnalyzer:
    """
    Analiza tendencias de drift a lo largo del tiempo.

    Mantiene un histórico de reportes de drift y detecta patrones
    de empeoramiento o mejora que justifiquen re-entrenamiento.
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        drift_detector: Optional[DataDriftDetector] = None,
    ):
        """
        Initialize drift trend analyzer.

        Args:
            storage_path: Path para almacenar histórico de drift.
                         Por defecto: data/drift_history/drift_history.parquet
            drift_detector: Detector de drift a usar.
        """
        if storage_path is None:
            from forex_core.config import get_settings

            settings = get_settings()
            storage_path = settings.data_dir / "drift_history" / "drift_history.parquet"

        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.drift_detector = drift_detector or DataDriftDetector()

        logger.info(f"DriftTrendAnalyzer initialized with storage: {storage_path}")

    def record_drift(self, report: DriftReport, horizon: str) -> None:
        """
        Registra un reporte de drift en el histórico.

        Args:
            report: Reporte de drift a registrar.
            horizon: Horizonte del forecast (7d, 15d, etc.).
        """
        drift_score = self._calculate_drift_score(report)

        record = {
            "timestamp": report.timestamp,
            "horizon": horizon,
            "drift_detected": report.drift_detected,
            "severity": report.severity.value,
            "drift_score": drift_score,
            "p_value": report.p_value,
            "ks_statistic": report.statistic,
            "baseline_mean": report.baseline_mean,
            "recent_mean": report.recent_mean,
            "baseline_std": report.baseline_std,
            "recent_std": report.recent_std,
            "ks_drift": report.tests.get("ks_test", None) is not None
            and report.tests["ks_test"].drift_detected,
            "t_drift": report.tests.get("t_test", None) is not None
            and report.tests["t_test"].drift_detected,
            "levene_drift": report.tests.get("levene_test", None) is not None
            and report.tests["levene_test"].drift_detected,
            "ljungbox_drift": report.tests.get("ljungbox_test", None) is not None
            and report.tests["ljungbox_test"].drift_detected,
        }

        # Load existing history or create new DataFrame
        if self.storage_path.exists():
            df = pd.read_parquet(self.storage_path)
            df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
        else:
            df = pd.DataFrame([record])

        # Save updated history
        df.to_parquet(self.storage_path, index=False)

        logger.info(
            f"Drift recorded for {horizon}: score={drift_score:.1f}, "
            f"severity={report.severity.value}"
        )

    def analyze_trend(
        self,
        horizon: str,
        lookback_days: int = 90,
    ) -> DriftTrendReport:
        """
        Analiza tendencia de drift para un horizonte.

        Args:
            horizon: Horizonte a analizar (7d, 15d, etc.).
            lookback_days: Días a considerar para el análisis.

        Returns:
            DriftTrendReport con análisis de tendencia.
        """
        logger.info(f"Analyzing drift trend for {horizon} (lookback: {lookback_days}d)")

        # Load historical data
        history = self.get_drift_history(horizon, days=lookback_days)

        if history.empty or len(history) < 3:
            logger.warning(f"Insufficient data for trend analysis: {len(history)} records")
            return self._create_empty_report()

        # Calculate metrics
        current_score = history["drift_score"].iloc[-1]
        avg_score_30d = self._calculate_avg_score(history, days=30)
        avg_score_90d = self._calculate_avg_score(history, days=90)

        # Detect trend via linear regression
        trend_slope, trend_r2 = self._fit_trend_line(history)

        # Detect trend direction
        trend = self._detect_trend(trend_slope, trend_r2, current_score)

        # Count consecutive high severity days
        consecutive_high = self._count_consecutive_high(history)

        # Find last stable date
        last_stable_date = self._find_last_stable_date(history)

        # Generate recommendation
        recommendation = self._generate_trend_recommendation(
            trend=trend,
            current_score=current_score,
            avg_score_30d=avg_score_30d,
            consecutive_high=consecutive_high,
        )

        report = DriftTrendReport(
            trend=trend,
            current_score=current_score,
            avg_score_30d=avg_score_30d,
            avg_score_90d=avg_score_90d,
            trend_slope=trend_slope,
            trend_r2=trend_r2,
            consecutive_high=consecutive_high,
            last_stable_date=last_stable_date,
            recommendation=recommendation,
            timestamp=datetime.now(),
        )

        logger.info(
            f"Drift trend analysis complete: trend={trend.value}, "
            f"score={current_score:.1f}, slope={trend_slope:.2f}"
        )

        return report

    def get_drift_history(
        self,
        horizon: Optional[str] = None,
        days: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Obtiene histórico de drift.

        Args:
            horizon: Filtrar por horizonte específico (opcional).
            days: Filtrar últimos N días (opcional).

        Returns:
            DataFrame con histórico de drift.
        """
        if not self.storage_path.exists():
            return pd.DataFrame()

        df = pd.read_parquet(self.storage_path)

        # Filter by horizon if specified
        if horizon:
            df = df[df["horizon"] == horizon].copy()

        # Filter by days if specified
        if days:
            cutoff = datetime.now() - pd.Timedelta(days=days)
            df = df[pd.to_datetime(df["timestamp"]) >= cutoff].copy()

        return df.sort_values("timestamp").reset_index(drop=True)

    def _calculate_drift_score(self, report: DriftReport) -> float:
        """
        Calcula score de drift (0-100) basado en múltiples factores.

        Score = weighted average de:
        - KS test (40%): statistic normalizado
        - T-test (25%): significancia
        - Levene test (20%): significancia
        - Ljung-Box test (15%): significancia

        Args:
            report: Reporte de drift.

        Returns:
            Score de 0 (sin drift) a 100 (drift máximo).
        """
        # KS statistic (0-1 range, higher = more drift)
        ks_score = min(report.statistic * 100, 100) * 0.40

        # T-test significance (p-value inverted)
        t_test = report.tests.get("t_test")
        if t_test and t_test.p_value > 0:
            t_score = max(0, (1 - t_test.p_value) * 100) * 0.25
        else:
            t_score = 0

        # Levene test significance
        levene_test = report.tests.get("levene_test")
        if levene_test and levene_test.p_value > 0:
            levene_score = max(0, (1 - levene_test.p_value) * 100) * 0.20
        else:
            levene_score = 0

        # Ljung-Box test significance
        ljungbox_test = report.tests.get("ljungbox_test")
        if ljungbox_test and ljungbox_test.p_value > 0:
            ljungbox_score = max(0, (1 - ljungbox_test.p_value) * 100) * 0.15
        else:
            ljungbox_score = 0

        total_score = ks_score + t_score + levene_score + ljungbox_score

        return min(total_score, 100.0)

    def _calculate_avg_score(self, history: pd.DataFrame, days: int) -> float:
        """Calcula score promedio en ventana de días."""
        if history.empty:
            return 0.0

        cutoff = datetime.now() - pd.Timedelta(days=days)
        recent = history[pd.to_datetime(history["timestamp"]) >= cutoff]

        if recent.empty:
            return 0.0

        return float(recent["drift_score"].mean())

    def _fit_trend_line(self, history: pd.DataFrame) -> tuple[float, float]:
        """
        Ajusta línea de regresión lineal al histórico.

        Returns:
            (slope, r2) - Pendiente y R² de la regresión.
        """
        if len(history) < 2:
            return 0.0, 0.0

        # Create numeric time index (days from start)
        history = history.copy()
        history["timestamp"] = pd.to_datetime(history["timestamp"])
        start_time = history["timestamp"].min()
        history["days_from_start"] = (
            history["timestamp"] - start_time
        ).dt.total_seconds() / 86400

        x = history["days_from_start"].values
        y = history["drift_score"].values

        # Linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        r2 = r_value**2

        return float(slope), float(r2)

    def _detect_trend(
        self,
        slope: float,
        r2: float,
        current_score: float,
    ) -> DriftTrend:
        """
        Detecta dirección de tendencia.

        Args:
            slope: Pendiente de regresión (positivo = empeorando).
            r2: R² de la regresión (qué tan claro es el trend).
            current_score: Score actual de drift.

        Returns:
            DriftTrend detectado.
        """
        # Need strong R² to claim trend
        if r2 < 0.3:
            # Weak trend, classify by current score
            if current_score < 25:
                return DriftTrend.STABLE
            else:
                return DriftTrend.UNKNOWN

        # Strong trend detected
        if abs(slope) < 0.5:
            # Flat trend
            return DriftTrend.STABLE
        elif slope > 0:
            # Worsening (score increasing)
            return DriftTrend.WORSENING
        else:
            # Improving (score decreasing)
            return DriftTrend.IMPROVING

    def _count_consecutive_high(self, history: pd.DataFrame) -> int:
        """Cuenta días consecutivos con severidad HIGH."""
        if history.empty:
            return 0

        # Get recent records in reverse order
        recent = history.iloc[::-1]

        count = 0
        for _, row in recent.iterrows():
            if row["severity"] == DriftSeverity.HIGH.value:
                count += 1
            else:
                break

        return count

    def _find_last_stable_date(self, history: pd.DataFrame) -> Optional[datetime]:
        """Encuentra última fecha con drift NONE."""
        if history.empty:
            return None

        stable = history[history["severity"] == DriftSeverity.NONE.value]

        if stable.empty:
            return None

        return pd.to_datetime(stable["timestamp"].iloc[-1])

    def _generate_trend_recommendation(
        self,
        trend: DriftTrend,
        current_score: float,
        avg_score_30d: float,
        consecutive_high: int,
    ) -> str:
        """
        Genera recomendación basada en tendencia.

        Args:
            trend: Tendencia detectada.
            current_score: Score actual.
            avg_score_30d: Score promedio 30 días.
            consecutive_high: Días consecutivos con HIGH.

        Returns:
            Recomendación de acción.
        """
        if trend == DriftTrend.WORSENING and current_score >= 75:
            return (
                "CRITICAL: Drift empeorando rápidamente. "
                "Re-entrenamiento URGENTE requerido. "
                "Forecasts actuales probablemente no confiables."
            )

        if consecutive_high >= 5:
            return (
                "CRITICAL: Drift HIGH persistente por 5+ días. "
                "Re-entrenamiento inmediato necesario."
            )

        if trend == DriftTrend.WORSENING and avg_score_30d >= 50:
            return (
                "WARNING: Tendencia de drift empeorando. "
                "Planificar re-entrenamiento pronto (próximos 7-14 días). "
                "Monitorear performance de forecasts."
            )

        if current_score >= 60:
            return (
                "ADVISORY: Drift score elevado pero estable. "
                "Considerar re-entrenamiento si persiste por 7+ días."
            )

        if trend == DriftTrend.IMPROVING:
            return (
                "OK: Drift está mejorando. "
                "Continuar monitoreo regular. Re-entrenamiento no urgente."
            )

        if trend == DriftTrend.STABLE and current_score < 30:
            return (
                "OK: Drift estable y bajo. "
                "Modelos actuales funcionando bien. Continuar monitoreo."
            )

        return (
            "MONITORING: Tendencia no clara o drift moderado. "
            "Continuar vigilancia, evaluar en 7 días."
        )

    def _create_empty_report(self) -> DriftTrendReport:
        """Crea reporte vacío cuando no hay datos suficientes."""
        return DriftTrendReport(
            trend=DriftTrend.UNKNOWN,
            current_score=0.0,
            avg_score_30d=0.0,
            avg_score_90d=0.0,
            trend_slope=0.0,
            trend_r2=0.0,
            consecutive_high=0,
            last_stable_date=None,
            recommendation="Datos insuficientes para análisis de tendencia",
            timestamp=datetime.now(),
        )


__all__ = [
    "DriftTrendAnalyzer",
    "DriftTrendReport",
    "DriftTrend",
]
