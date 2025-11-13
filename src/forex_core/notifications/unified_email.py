"""
Unified Email Orchestrator for USD/CLP Forecasting System.

This module orchestrates the sending of unified daily emails that consolidate
multiple forecast horizons and system health information into a single,
intelligent email based on market-optimized sending strategy.

Strategy based on USD/CLP market expert recommendations:
- Sends only when necessary (avoiding email fatigue)
- Attaches PDFs conditionally (only when they add value)
- Optimized timing for Chilean market (7:30 AM Santiago)
- Adaptive content based on day of week and market conditions

Author: Forex Forecast System
License: MIT
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set

import pandas as pd

from ..config.base import Settings
from ..utils.logging import get_logger

logger = get_logger(__name__)


class EmailFrequency(Enum):
    """Email frequency for different horizons."""
    DAILY = "daily"  # Every day
    TRIWEEKLY = "triweekly"  # Mon, Wed, Fri
    BIWEEKLY = "biweekly"  # Mon, Thu
    WEEKLY = "weekly"  # Friday only
    BIMONTHLY = "bimonthly"  # 1st and 15th
    MONTHLY = "monthly"  # First Tuesday of month


class ForecastHorizon(Enum):
    """Forecast horizons."""
    H_7D = "7d"
    H_15D = "15d"
    H_30D = "30d"
    H_90D = "90d"
    H_12M = "12m"


@dataclass
class ForecastData:
    """Data for a single forecast horizon."""
    horizon: str
    current_price: float
    forecast_price: float
    change_pct: float
    ci95_low: float
    ci95_high: float
    ci80_low: float
    ci80_high: float
    bias: str  # "ALCISTA", "BAJISTA", "NEUTRAL"
    volatility: str  # "ALTA", "MEDIA", "BAJA"
    pdf_path: Optional[Path] = None
    chart_preview: Optional[bytes] = None  # Base64 encoded chart
    top_drivers: List[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.top_drivers is None:
            self.top_drivers = []
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class SystemHealthData:
    """System health and performance data."""
    readiness_level: str  # "OPTIMAL", "READY", "CAUTIOUS", "NOT_READY"
    readiness_score: float  # 0-100
    performance_status: Dict[str, str]  # horizon -> status ("EXCELLENT", "GOOD", "DEGRADED")
    degradation_detected: bool
    degradation_details: List[str]
    recent_predictions: int
    drift_detected: bool
    drift_details: List[str]

    def has_critical_issues(self) -> bool:
        """Check if there are critical system issues."""
        return (
            self.degradation_detected or
            self.drift_detected or
            self.readiness_level == "NOT_READY" or
            any(status == "DEGRADED" for status in self.performance_status.values())
        )


@dataclass
class UnifiedEmailContent:
    """Content for unified email."""
    subject: str
    executive_summary: str
    forecasts: List[ForecastData]
    system_health: SystemHealthData
    html_body: str
    pdf_attachments: List[Path]
    priority: str  # "URGENT", "ATTENTION", "ROUTINE"
    send_date: datetime


class UnifiedEmailOrchestrator:
    """
    Orchestrates unified email sending based on market-optimized strategy.

    This class determines:
    - Which forecasts to include based on day of week
    - Whether to attach PDFs or send HTML only
    - Email priority and formatting
    - Integration of system health with forecasts

    Strategy is based on USD/CLP market patterns and corporate decision cycles.
    """

    # Sending strategy configuration (day of week -> horizons to include)
    WEEKLY_STRATEGY = {
        0: [ForecastHorizon.H_7D, ForecastHorizon.H_15D],  # Monday
        1: [],  # Tuesday (monthly 12m only)
        2: [ForecastHorizon.H_7D],  # Wednesday
        3: [ForecastHorizon.H_15D],  # Thursday
        4: [ForecastHorizon.H_7D, ForecastHorizon.H_30D],  # Friday
        5: [],  # Saturday
        6: [],  # Sunday
    }

    def __init__(
        self,
        data_dir: Path,
        settings: Settings | None = None,
    ):
        """
        Initialize the unified email orchestrator.

        Args:
            data_dir: Directory containing forecast data and predictions
            settings: System settings (auto-loaded if None)
        """
        self.data_dir = Path(data_dir)
        self.settings = settings or Settings()

        logger.info(
            "UnifiedEmailOrchestrator initialized",
            extra={"data_dir": str(self.data_dir)},
        )

    def should_send_today(
        self,
        horizon: ForecastHorizon,
        current_date: datetime | None = None,
    ) -> bool:
        """
        Determine if a forecast horizon should be included today.

        Args:
            horizon: Forecast horizon to check
            current_date: Date to check (defaults to today)

        Returns:
            True if this horizon should be included in today's email
        """
        if current_date is None:
            current_date = datetime.now()

        day_of_week = current_date.weekday()
        day_of_month = current_date.day

        # Special cases for monthly/quarterly horizons
        if horizon == ForecastHorizon.H_90D:
            # Send on 1st and 15th of month
            return day_of_month in [1, 15]

        if horizon == ForecastHorizon.H_12M:
            # Send on first Tuesday of month
            return day_of_week == 1 and 1 <= day_of_month <= 7

        # Regular weekly horizons
        horizons_today = self.WEEKLY_STRATEGY.get(day_of_week, [])
        return horizon in horizons_today

    def get_horizons_for_today(
        self,
        current_date: datetime | None = None,
    ) -> List[ForecastHorizon]:
        """
        Get list of forecast horizons to include in today's email.

        Args:
            current_date: Date to check (defaults to today)

        Returns:
            List of horizons that should be included today
        """
        if current_date is None:
            current_date = datetime.now()

        horizons = []

        for horizon in ForecastHorizon:
            if self.should_send_today(horizon, current_date):
                horizons.append(horizon)

        logger.info(
            f"Horizons for {current_date.strftime('%A, %Y-%m-%d')}: {[h.value for h in horizons]}",
        )

        return horizons

    def should_attach_pdf(
        self,
        forecast: ForecastData,
        system_health: SystemHealthData,
        current_date: datetime | None = None,
    ) -> bool:
        """
        Determine if PDF should be attached for this forecast.

        PDFs are attached only when they add significant value:
        - Significant price changes (>1.5%)
        - Critical system alerts
        - Friday (weekly summary)
        - Monthly/quarterly reports (always PDF)

        Args:
            forecast: Forecast data to evaluate
            system_health: System health status
            current_date: Date to check (defaults to today)

        Returns:
            True if PDF should be attached
        """
        if current_date is None:
            current_date = datetime.now()

        day_of_week = current_date.weekday()

        # Always attach PDF for longer horizons
        if forecast.horizon in ["30d", "90d", "12m"]:
            return True

        # Always attach on Friday (weekly summary)
        if day_of_week == 4:  # Friday
            return True

        # Attach if significant price change
        if abs(forecast.change_pct) > 1.5:
            logger.info(
                f"Attaching PDF for {forecast.horizon}: significant change {forecast.change_pct:+.1f}%",
            )
            return True

        # Attach if critical system issues
        if system_health.has_critical_issues():
            logger.info(
                f"Attaching PDF for {forecast.horizon}: critical system issues detected",
            )
            return True

        # Attach if extreme volatility
        if forecast.volatility == "ALTA":
            logger.info(
                f"Attaching PDF for {forecast.horizon}: high volatility",
            )
            return True

        # Otherwise, HTML only
        logger.debug(
            f"No PDF attachment for {forecast.horizon}: routine conditions",
        )
        return False

    def determine_email_priority(
        self,
        forecasts: List[ForecastData],
        system_health: SystemHealthData,
    ) -> str:
        """
        Determine email priority based on content.

        Args:
            forecasts: List of forecast data
            system_health: System health status

        Returns:
            Priority level: "URGENT", "ATTENTION", or "ROUTINE"
        """
        # Critical system failure or extreme market movement
        if system_health.readiness_level == "NOT_READY":
            return "URGENT"

        for forecast in forecasts:
            if abs(forecast.change_pct) > 3.0:
                return "URGENT"

        # Degradation or significant changes
        if system_health.has_critical_issues():
            return "ATTENTION"

        for forecast in forecasts:
            if abs(forecast.change_pct) > 1.5:
                return "ATTENTION"

        # Normal operation
        return "ROUTINE"

    def generate_subject_line(
        self,
        forecasts: List[ForecastData],
        system_health: SystemHealthData,
        priority: str,
        current_date: datetime | None = None,
    ) -> str:
        """
        Generate dynamic subject line for email.

        Args:
            forecasts: List of forecast data
            system_health: System health status
            priority: Email priority level
            current_date: Date for subject (defaults to today)

        Returns:
            Subject line string
        """
        if current_date is None:
            current_date = datetime.now()

        date_str = current_date.strftime("%Y-%m-%d")

        # Priority prefix
        if priority == "URGENT":
            prefix = "🚨 URGENTE"
        elif priority == "ATTENTION":
            prefix = "⚠️ ATENCIÓN"
        else:
            prefix = "📊"

        # Get primary forecast (7d or first available)
        primary_forecast = None
        for fc in forecasts:
            if fc.horizon == "7d":
                primary_forecast = fc
                break

        if primary_forecast is None and forecasts:
            primary_forecast = forecasts[0]

        # Build subject
        if primary_forecast:
            subject = (
                f"{prefix} USD/CLP {primary_forecast.horizon}: "
                f"${primary_forecast.current_price:.0f} → ${primary_forecast.forecast_price:.0f} "
                f"({primary_forecast.change_pct:+.1f}%) | {primary_forecast.bias}"
            )
        else:
            subject = f"{prefix} USD/CLP System Report - {date_str}"

        # Add system health if critical
        if system_health.has_critical_issues():
            subject += f" | System: {system_health.readiness_level}"

        return subject

    def load_forecast_data(
        self,
        horizon: str,
        forecast_date: datetime | None = None,
    ) -> Optional[ForecastData]:
        """
        Load forecast data for a specific horizon.

        Args:
            horizon: Forecast horizon ("7d", "15d", etc.)
            forecast_date: Date of forecast (defaults to today)

        Returns:
            ForecastData if available, None otherwise
        """
        if forecast_date is None:
            forecast_date = datetime.now()

        try:
            from ..mlops.tracking import PredictionTracker

            # Initialize tracker
            predictions_path = self.data_dir / "predictions" / "predictions.parquet"

            if not predictions_path.exists():
                logger.warning(f"Predictions file not found: {predictions_path}")
                return None

            tracker = PredictionTracker(storage_path=predictions_path)

            # Load predictions for this horizon
            df = pd.read_parquet(predictions_path)

            # Filter by horizon
            horizon_df = df[df["horizon"] == horizon].copy()

            if horizon_df.empty:
                logger.warning(f"No predictions found for horizon {horizon}")
                return None

            # Get most recent forecast
            horizon_df = horizon_df.sort_values("forecast_date", ascending=False)
            latest = horizon_df.iloc[0]

            # Calculate current price (last actual or forecast)
            current_price = float(latest.get("actual", latest["forecast_mean"]))

            # Get forecast values
            forecast_price = float(latest["forecast_mean"])
            ci95_low = float(latest.get("ci95_low", forecast_price * 0.95))
            ci95_high = float(latest.get("ci95_high", forecast_price * 1.05))
            ci80_low = float(latest.get("ci80_low", forecast_price * 0.98))
            ci80_high = float(latest.get("ci80_high", forecast_price * 1.02))

            # Calculate change percentage
            change_pct = ((forecast_price - current_price) / current_price) * 100

            # Determine bias
            if change_pct > 0.3:
                bias = "ALCISTA"
            elif change_pct < -0.3:
                bias = "BAJISTA"
            else:
                bias = "NEUTRAL"

            # Determine volatility (based on CI width)
            ci_width = ((ci95_high - ci95_low) / forecast_price) * 100
            if ci_width > 5:
                volatility = "ALTA"
            elif ci_width > 2:
                volatility = "MEDIA"
            else:
                volatility = "BAJA"

            # Find PDF path if exists
            pdf_dir = self.data_dir.parent / "reports"
            pdf_pattern = f"*{horizon}*.pdf"
            pdf_files = list(pdf_dir.glob(pdf_pattern))
            pdf_path = pdf_files[0] if pdf_files else None

            # Create ForecastData
            forecast_data = ForecastData(
                horizon=horizon,
                current_price=current_price,
                forecast_price=forecast_price,
                change_pct=change_pct,
                ci95_low=ci95_low,
                ci95_high=ci95_high,
                ci80_low=ci80_low,
                ci80_high=ci80_high,
                bias=bias,
                volatility=volatility,
                pdf_path=pdf_path,
                timestamp=pd.Timestamp(latest["forecast_date"]),
            )

            logger.info(
                f"Loaded forecast data for {horizon}: "
                f"${current_price:.0f} → ${forecast_price:.0f} ({change_pct:+.1f}%)",
            )

            return forecast_data

        except Exception as e:
            logger.error(
                f"Error loading forecast data for {horizon}: {e}",
                exc_info=True,
            )
            return None

    def load_system_health(self) -> SystemHealthData:
        """
        Load current system health data.

        Returns:
            SystemHealthData with current metrics
        """
        try:
            from ..mlops.readiness import ChronosReadinessChecker
            from ..mlops.performance_monitor import PerformanceMonitor

            # Initialize checkers
            readiness_checker = ChronosReadinessChecker(data_dir=self.data_dir)
            performance_monitor = PerformanceMonitor(data_dir=self.data_dir)

            # Get readiness assessment
            readiness_report = readiness_checker.assess()

            # Get performance status for all horizons
            performance_reports = performance_monitor.check_all_horizons()

            # Build performance status dict
            performance_status = {}
            degradation_detected = False
            degradation_details = []

            for horizon, report in performance_reports.items():
                # Map PerformanceStatus to string
                if report.status.value == "excellent":
                    performance_status[horizon] = "EXCELLENT"
                elif report.status.value == "good":
                    performance_status[horizon] = "GOOD"
                elif report.status.value == "degraded":
                    performance_status[horizon] = "DEGRADED"
                    degradation_detected = True
                    degradation_details.append(
                        f"{horizon}: {report.recommendation}"
                    )
                else:
                    performance_status[horizon] = "UNKNOWN"

            # Count recent predictions
            predictions_path = self.data_dir / "predictions" / "predictions.parquet"
            recent_predictions = 0

            if predictions_path.exists():
                df = pd.read_parquet(predictions_path)
                # Count predictions in last 7 days
                cutoff = pd.Timestamp.now() - pd.Timedelta(days=7)
                recent_df = df[df["forecast_date"] > cutoff]
                recent_predictions = len(recent_df)

            # Check drift detection (if available)
            drift_detected = False
            drift_details = []

            # TODO: Integrate with drift detector when available
            # For now, check if drift is mentioned in degradation details

            return SystemHealthData(
                readiness_level=readiness_report.level.value.upper(),
                readiness_score=readiness_report.score,
                performance_status=performance_status,
                degradation_detected=degradation_detected,
                degradation_details=degradation_details,
                recent_predictions=recent_predictions,
                drift_detected=drift_detected,
                drift_details=drift_details,
            )

        except Exception as e:
            logger.error(
                f"Error loading system health: {e}",
                exc_info=True,
            )

            # Return safe defaults on error
            return SystemHealthData(
                readiness_level="UNKNOWN",
                readiness_score=50.0,
                performance_status={
                    "7d": "UNKNOWN",
                    "15d": "UNKNOWN",
                    "30d": "UNKNOWN",
                    "90d": "UNKNOWN",
                },
                degradation_detected=False,
                degradation_details=["Error loading system health"],
                recent_predictions=0,
                drift_detected=False,
                drift_details=[],
            )

    def should_send_email_today(
        self,
        current_date: datetime | None = None,
    ) -> bool:
        """
        Determine if any email should be sent today.

        Args:
            current_date: Date to check (defaults to today)

        Returns:
            True if email should be sent today
        """
        horizons = self.get_horizons_for_today(current_date)
        return len(horizons) > 0

    def get_email_send_time(
        self,
        current_date: datetime | None = None,
    ) -> datetime:
        """
        Get optimal send time for today's email.

        Standard time: 7:30 AM Santiago
        Special cases: 8:00 AM for monthly reports

        Args:
            current_date: Date to get time for (defaults to today)

        Returns:
            Datetime with optimal send time
        """
        if current_date is None:
            current_date = datetime.now()

        # Check if monthly report day (first Tuesday)
        day_of_week = current_date.weekday()
        day_of_month = current_date.day

        if day_of_week == 1 and 1 <= day_of_month <= 7:
            # First Tuesday - send at 8:00 AM
            send_hour = 8
            send_minute = 0
        elif day_of_month in [1, 15]:
            # Quarterly report days - send at 8:00 AM
            send_hour = 8
            send_minute = 0
        else:
            # Regular days - send at 7:30 AM
            send_hour = 7
            send_minute = 30

        return current_date.replace(
            hour=send_hour,
            minute=send_minute,
            second=0,
            microsecond=0,
        )


__all__ = [
    "UnifiedEmailOrchestrator",
    "UnifiedEmailContent",
    "ForecastData",
    "SystemHealthData",
    "EmailFrequency",
    "ForecastHorizon",
]
