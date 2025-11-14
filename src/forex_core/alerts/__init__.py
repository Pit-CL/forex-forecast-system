"""
Alert systems for USD/CLP forecasting system.

This package provides market shock detection and model performance monitoring
for the autonomous forecasting system.

Modules:
    - market_shock_detector: Detects market events affecting USD/CLP
    - model_performance_alerts: Monitors model health and degradation
    - alert_email_generator: Generates alert emails with HTML and PDF
"""

from __future__ import annotations

from forex_core.alerts.alert_email_generator import (
    generate_market_shock_email,
    generate_model_performance_email,
)
from forex_core.alerts.market_shock_detector import (
    Alert,
    AlertSeverity,
    AlertType,
    MarketShockDetector,
)
from forex_core.alerts.model_performance_alerts import (
    BaselineMetrics,
    ModelAlert,
    ModelPerformanceMonitor,
)
from forex_core.alerts.model_performance_alerts import (
    AlertSeverity as ModelAlertSeverity,
)
from forex_core.alerts.model_performance_alerts import AlertType as ModelAlertType

__all__ = [
    # Market shock detection
    "Alert",
    "AlertSeverity",
    "AlertType",
    "MarketShockDetector",
    # Model performance monitoring
    "ModelPerformanceMonitor",
    "ModelAlert",
    "ModelAlertType",
    "ModelAlertSeverity",
    "BaselineMetrics",
    # Email generation
    "generate_market_shock_email",
    "generate_model_performance_email",
]
