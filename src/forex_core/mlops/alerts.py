"""
Alert Management System for Forex Forecasting.

Sistema de gestión de alertas que decide cuándo y cómo notificar
eventos significativos en el sistema de forecasting.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

from forex_core.data.loader import DataBundle
from forex_core.data.models import ForecastPackage
from forex_core.mlops.event_detector import (
    DetectedEvent,
    EventDetector,
    EventSeverity,
    get_event_summary,
)
from forex_core.mlops.monitoring import DataDriftDetector
from forex_core.mlops.tracking import PredictionTracker


@dataclass
class AlertDecision:
    """Decisión sobre si enviar alerta o no."""

    should_alert: bool
    reason: str
    events: list[DetectedEvent]
    severity: EventSeverity
    timestamp: datetime

    def get_subject_prefix(self) -> str:
        """Obtiene prefijo para email subject basado en severidad."""
        if self.severity == EventSeverity.CRITICAL:
            return "🚨"
        elif self.severity == EventSeverity.HIGH:
            return "⚠️"
        elif self.severity == EventSeverity.WARNING:
            return "📊"
        else:
            return "📈"

    def get_event_summary(self) -> str:
        """Obtiene resumen corto de eventos."""
        return get_event_summary(self.events)


class AlertManager:
    """
    Gestiona decisiones de alertas para el sistema de forecasting.

    Coordina detección de eventos y decisión de envío de alertas.
    """

    def __init__(
        self,
        data_dir: Path = Path("data"),
        change_threshold: float = 2.0,
        volatility_threshold: float = 1.5,
    ):
        """
        Initialize alert manager.

        Args:
            data_dir: Directorio de datos para tracking
            change_threshold: % mínimo de cambio para alertar
            volatility_threshold: Multiplicador de vol para alertar
        """
        self.data_dir = data_dir
        # PredictionTracker uses storage_path, not data_dir
        # It will automatically use data_dir from settings if no path is provided
        self.tracker = PredictionTracker()
        self.drift_detector = DataDriftDetector()
        self.event_detector = EventDetector(
            tracker=self.tracker,
            drift_detector=self.drift_detector,
            change_threshold=change_threshold,
            volatility_threshold=volatility_threshold,
        )

    def evaluate_alert(
        self,
        horizon: str,
        forecast: ForecastPackage,
        bundle: DataBundle,
    ) -> AlertDecision:
        """
        Evalúa si se debe enviar alerta para este forecast.

        Args:
            horizon: Horizonte del forecast (7d, 15d, etc.)
            forecast: Forecast generado
            bundle: Bundle de datos usado

        Returns:
            AlertDecision con la decisión y eventos detectados
        """
        logger.info(f"Evaluating alert conditions for {horizon}")

        # Detect all events
        events = self.event_detector.detect_events(horizon, forecast, bundle)

        # Determine if should alert
        should_alert, reason = self.event_detector.should_send_alert(events)

        # Determine overall severity
        severity = self._get_overall_severity(events)

        decision = AlertDecision(
            should_alert=should_alert,
            reason=reason,
            events=events,
            severity=severity,
            timestamp=datetime.now(),
        )

        logger.info(
            f"Alert decision for {horizon}: {should_alert} "
            f"(severity: {severity}, events: {len(events)})"
        )

        return decision

    def _get_overall_severity(self, events: list[DetectedEvent]) -> EventSeverity:
        """Determina severidad general de eventos."""
        if not events:
            return EventSeverity.INFO

        severities = [e.severity for e in events]

        if EventSeverity.CRITICAL in severities:
            return EventSeverity.CRITICAL
        elif EventSeverity.HIGH in severities:
            return EventSeverity.HIGH
        elif EventSeverity.WARNING in severities:
            return EventSeverity.WARNING
        else:
            return EventSeverity.INFO

    def generate_alert_summary(self, decision: AlertDecision, horizon: str) -> str:
        """
        Genera resumen de alerta para logs.

        Args:
            decision: Decisión de alerta
            horizon: Horizonte del forecast

        Returns:
            String con resumen formateado
        """
        lines = [
            "=" * 60,
            f"ALERT EVALUATION - {horizon}",
            "=" * 60,
            f"Timestamp: {decision.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Decision: {'SEND ALERT' if decision.should_alert else 'NO ALERT'}",
            f"Severity: {decision.severity.value.upper()}",
            f"Reason: {decision.reason}",
            "",
            f"Events detected: {len(decision.events)}",
        ]

        for i, event in enumerate(decision.events, 1):
            lines.append(f"  {i}. [{event.severity.value.upper()}] {event.event_type}")
            lines.append(f"     {event.description}")
            if event.metrics:
                lines.append(f"     Metrics: {event.metrics}")

        lines.append("=" * 60)

        return "\n".join(lines)

    def log_alert_decision(
        self, decision: AlertDecision, horizon: str, log_file: Optional[Path] = None
    ):
        """
        Registra decisión de alerta en log file.

        Args:
            decision: Decisión de alerta
            horizon: Horizonte del forecast
            log_file: Path opcional al archivo de log
        """
        if log_file is None:
            log_file = self.data_dir.parent / "logs" / f"alerts_{horizon}.log"

        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)

        summary = self.generate_alert_summary(decision, horizon)

        # Log to file
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(summary + "\n\n")

        logger.info(f"Alert decision logged to {log_file}")


def should_send_alert_for_horizon(
    horizon: str,
    forecast: ForecastPackage,
    bundle: DataBundle,
    data_dir: Path = Path("data"),
) -> tuple[bool, AlertDecision]:
    """
    Helper function para evaluar si enviar alerta.

    Args:
        horizon: Horizonte del forecast
        forecast: Forecast generado
        bundle: Bundle de datos
        data_dir: Directorio de datos

    Returns:
        (should_alert, decision) - Decisión de alerta
    """
    manager = AlertManager(data_dir=data_dir)
    decision = manager.evaluate_alert(horizon, forecast, bundle)
    manager.log_alert_decision(decision, horizon)

    return decision.should_alert, decision


__all__ = [
    "AlertManager",
    "AlertDecision",
    "should_send_alert_for_horizon",
]
