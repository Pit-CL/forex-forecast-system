"""
Event Detection System for Forex Forecasting.

Detecta eventos significativos que justifican enviar alertas:
- Cambios significativos en el forecast
- Drift en los datos
- Alta volatilidad
- Eventos económicos importantes
- Cambios de régimen de riesgo
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger

from forex_core.data.models import DataBundle, ForecastPackage
from forex_core.mlops.monitoring import DataDriftDetector, DriftReport
from forex_core.mlops.tracking import PredictionTracker


class EventSeverity(str, Enum):
    """Severidad del evento detectado."""

    INFO = "info"  # Informativo, no requiere acción
    WARNING = "warning"  # Atención, monitorear
    HIGH = "high"  # Importante, revisar
    CRITICAL = "critical"  # Urgente, requiere acción


@dataclass
class DetectedEvent:
    """Evento detectado que justifica envío de alerta."""

    event_type: str  # Tipo de evento
    severity: EventSeverity  # Severidad
    description: str  # Descripción humana
    metrics: dict  # Métricas asociadas
    timestamp: datetime  # Cuándo se detectó

    def should_alert(self) -> bool:
        """Determina si este evento justifica enviar alerta."""
        return self.severity in [EventSeverity.HIGH, EventSeverity.CRITICAL]


class EventDetector:
    """
    Detecta eventos significativos en el sistema de forecasting.

    Analiza múltiples dimensiones para determinar si se debe enviar
    una alerta fuera del schedule regular.
    """

    def __init__(
        self,
        tracker: PredictionTracker,
        drift_detector: DataDriftDetector,
        change_threshold: float = 2.0,  # % cambio en forecast
        volatility_threshold: float = 1.5,  # multiplicador vs histórica
    ):
        """
        Initialize event detector.

        Args:
            tracker: Prediction tracker para histórico
            drift_detector: Detector de drift en datos
            change_threshold: % mínimo de cambio para alertar
            volatility_threshold: Multiplicador de vol para alertar
        """
        self.tracker = tracker
        self.drift_detector = drift_detector
        self.change_threshold = change_threshold
        self.volatility_threshold = volatility_threshold

    def detect_events(
        self,
        horizon: str,
        current_forecast: ForecastPackage,
        bundle: DataBundle,
    ) -> list[DetectedEvent]:
        """
        Detecta todos los eventos relevantes.

        Args:
            horizon: Horizonte del forecast (7d, 15d, etc.)
            current_forecast: Forecast actual
            bundle: Bundle de datos usado

        Returns:
            Lista de eventos detectados
        """
        events = []

        # 1. Check forecast change
        forecast_change_event = self._check_forecast_change(horizon, current_forecast)
        if forecast_change_event:
            events.append(forecast_change_event)

        # 2. Check drift
        drift_event = self._check_drift(bundle.usdclp_series)
        if drift_event:
            events.append(drift_event)

        # 3. Check volatility
        volatility_event = self._check_volatility(bundle.usdclp_series)
        if volatility_event:
            events.append(volatility_event)

        # 4. Check economic events
        economic_event = self._check_economic_events()
        if economic_event:
            events.append(economic_event)

        # 5. Check regime change
        regime_event = self._check_regime_change(bundle)
        if regime_event:
            events.append(regime_event)

        logger.info(f"Detected {len(events)} events for {horizon}")
        return events

    def _check_forecast_change(
        self, horizon: str, current_forecast: ForecastPackage
    ) -> Optional[DetectedEvent]:
        """Detecta cambios significativos en el forecast."""
        try:
            # Get last forecast
            last_prediction = self.tracker.get_latest_prediction(horizon)

            if last_prediction is None:
                return None

            # Calculate change
            current_value = current_forecast.mean_forecast[0]  # First day
            last_value = last_prediction["prediction"]

            change_pct = abs((current_value - last_value) / last_value) * 100

            if change_pct >= self.change_threshold:
                severity = (
                    EventSeverity.HIGH if change_pct >= 3.0 else EventSeverity.WARNING
                )

                direction = "alza" if current_value > last_value else "baja"

                return DetectedEvent(
                    event_type="FORECAST_CHANGE",
                    severity=severity,
                    description=f"Cambio significativo en forecast: {direction} de {change_pct:.1f}%",
                    metrics={
                        "current": current_value,
                        "previous": last_value,
                        "change_pct": change_pct,
                        "direction": direction,
                    },
                    timestamp=datetime.now(),
                )

        except Exception as e:
            logger.warning(f"Error checking forecast change: {e}")

        return None

    def _check_drift(self, series: pd.Series) -> Optional[DetectedEvent]:
        """Detecta drift en los datos."""
        try:
            report = self.drift_detector.generate_drift_report(series)

            if report.has_significant_drift():
                # Count significant drifts
                drift_count = sum(
                    [
                        report.ks_test.is_significant,
                        report.t_test.is_significant,
                        report.levene_test.is_significant,
                    ]
                )

                severity = (
                    EventSeverity.HIGH if drift_count >= 2 else EventSeverity.WARNING
                )

                drift_types = []
                if report.ks_test.is_significant:
                    drift_types.append("distribución")
                if report.t_test.is_significant:
                    drift_types.append("media")
                if report.levene_test.is_significant:
                    drift_types.append("varianza")

                return DetectedEvent(
                    event_type="DATA_DRIFT",
                    severity=severity,
                    description=f"Drift detectado en {', '.join(drift_types)}",
                    metrics={
                        "ks_pvalue": report.ks_test.p_value,
                        "t_pvalue": report.t_test.p_value,
                        "levene_pvalue": report.levene_test.p_value,
                        "drift_count": drift_count,
                    },
                    timestamp=datetime.now(),
                )

        except Exception as e:
            logger.warning(f"Error checking drift: {e}")

        return None

    def _check_volatility(self, series: pd.Series) -> Optional[DetectedEvent]:
        """Detecta alta volatilidad."""
        try:
            # Calculate recent volatility (last 7 days)
            recent_returns = series.pct_change().dropna().tail(7)
            recent_vol = recent_returns.std() * (252**0.5)  # Annualized

            # Calculate historical volatility (last 90 days)
            hist_returns = series.pct_change().dropna().tail(90)
            hist_vol = hist_returns.std() * (252**0.5)

            vol_ratio = recent_vol / hist_vol

            if vol_ratio >= self.volatility_threshold:
                severity = (
                    EventSeverity.HIGH if vol_ratio >= 2.0 else EventSeverity.WARNING
                )

                return DetectedEvent(
                    event_type="HIGH_VOLATILITY",
                    severity=severity,
                    description=f"Volatilidad elevada: {vol_ratio:.1f}x la histórica",
                    metrics={
                        "recent_vol": recent_vol,
                        "historical_vol": hist_vol,
                        "ratio": vol_ratio,
                    },
                    timestamp=datetime.now(),
                )

        except Exception as e:
            logger.warning(f"Error checking volatility: {e}")

        return None

    def _check_economic_events(self) -> Optional[DetectedEvent]:
        """Detecta eventos económicos importantes próximos."""
        try:
            today = datetime.now()

            # BCCh meetings (3rd Tuesday of month)
            # Approximate - in production would use calendar API
            days_until_tuesday = (1 - today.weekday()) % 7
            next_tuesday = today + timedelta(days=days_until_tuesday)

            # Check if it's 3rd week of month (days 15-21)
            if 15 <= next_tuesday.day <= 21 and days_until_tuesday <= 2:
                return DetectedEvent(
                    event_type="ECONOMIC_EVENT",
                    severity=EventSeverity.INFO,
                    description=f"Reunión BCCh próxima ({next_tuesday.strftime('%d-%b')})",
                    metrics={"event_date": next_tuesday.isoformat(), "days_until": days_until_tuesday},
                    timestamp=datetime.now(),
                )

        except Exception as e:
            logger.warning(f"Error checking economic events: {e}")

        return None

    def _check_regime_change(self, bundle: DataBundle) -> Optional[DetectedEvent]:
        """Detecta cambios en el régimen de riesgo."""
        try:
            # Get current regime from bundle
            if hasattr(bundle, "risk_regime"):
                current_regime = bundle.risk_regime

                # Check if regime changed from last check
                # This would require storing last regime somewhere
                # For now, just return INFO if regime is not neutral

                if current_regime and current_regime != "NEUTRAL":
                    return DetectedEvent(
                        event_type="REGIME_CHANGE",
                        severity=EventSeverity.INFO,
                        description=f"Régimen actual: {current_regime}",
                        metrics={"regime": current_regime},
                        timestamp=datetime.now(),
                    )

        except Exception as e:
            logger.warning(f"Error checking regime: {e}")

        return None

    def should_send_alert(self, events: list[DetectedEvent]) -> tuple[bool, str]:
        """
        Determina si se debe enviar alerta basado en eventos detectados.

        Args:
            events: Lista de eventos detectados

        Returns:
            (should_alert, reason) - Si enviar y por qué
        """
        if not events:
            return False, "No events detected"

        # Check for any high/critical events
        high_severity_events = [
            e for e in events if e.severity in [EventSeverity.HIGH, EventSeverity.CRITICAL]
        ]

        if high_severity_events:
            reasons = [e.description for e in high_severity_events]
            return True, "; ".join(reasons)

        # Check for multiple warning events
        warning_events = [e for e in events if e.severity == EventSeverity.WARNING]
        if len(warning_events) >= 2:
            reasons = [e.description for e in warning_events]
            return True, f"Múltiples señales: {'; '.join(reasons)}"

        return False, "Events below alert threshold"


def get_event_summary(events: list[DetectedEvent]) -> str:
    """
    Genera resumen de eventos para email subject.

    Args:
        events: Eventos detectados

    Returns:
        String corto para subject line
    """
    if not events:
        return "Sin novedades"

    # Prioritize by severity
    critical = [e for e in events if e.severity == EventSeverity.CRITICAL]
    high = [e for e in events if e.severity == EventSeverity.HIGH]
    warning = [e for e in events if e.severity == EventSeverity.WARNING]

    if critical:
        return f"⚠️ {critical[0].event_type.replace('_', ' ').title()}"
    elif high:
        return f"📊 {high[0].event_type.replace('_', ' ').title()}"
    elif warning:
        return f"ℹ️ {warning[0].event_type.replace('_', ' ').title()}"
    else:
        return "📈 Update regular"


__all__ = [
    "EventDetector",
    "DetectedEvent",
    "EventSeverity",
    "get_event_summary",
]
