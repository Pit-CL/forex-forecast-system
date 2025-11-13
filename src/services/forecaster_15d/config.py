"""
Configuration overrides for 15-day forecaster service.

This module provides service-specific configuration that extends
the base forex_core settings with 15-day forecast parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from forex_core.config import (
    PROJECTION_DAYS_15D,
    HISTORICAL_LOOKBACK_DAYS_15D,
    TECH_LOOKBACK_DAYS_15D,
    VOL_LOOKBACK_DAYS_15D,
)


@dataclass(frozen=True)
class Forecaster15DConfig:
    """
    Service-specific configuration for 15-day forecaster.

    These settings override or extend the base forex_core configuration
    for bi-weekly forecasting (executed on day 1 and 15 of each month).

    Attributes:
        horizon: Forecast horizon type (always "daily" for this service).
        projection_days: Number of days to forecast (15).
        frequency: Pandas frequency string for daily data.
        historical_lookback_days: Days of historical data to use.
        tech_lookback_days: Days for technical indicator calculation.
        vol_lookback_days: Days for volatility calculation.
        report_title: Default title for generated reports.
        report_filename_prefix: Prefix for output filenames.

    Example:
        >>> config = Forecaster15DConfig()
        >>> print(config.projection_days)
        15
        >>> print(config.horizon)
        'daily'
    """

    # Forecast horizon
    horizon: Literal["daily"] = "daily"
    projection_days: int = PROJECTION_DAYS_15D  # 15 days
    frequency: str = "D"  # Daily frequency

    # Lookback periods (recommended by usdclp agent)
    historical_lookback_days: int = HISTORICAL_LOOKBACK_DAYS_15D  # 240 days (~8 months)
    tech_lookback_days: int = TECH_LOOKBACK_DAYS_15D  # 90 days (~3 months)
    vol_lookback_days: int = VOL_LOOKBACK_DAYS_15D  # 45 days (~1.5 months)

    # Report configuration
    report_title: str = "Proyección USD/CLP - Próximos 15 Días"
    report_filename_prefix: str = "Forecast_15D_USDCLP"

    # Chart configuration
    chart_title_suffix: str = "(15 días)"

    @property
    def steps(self) -> int:
        """Number of forecast steps (same as projection_days for daily)."""
        return self.projection_days

    @property
    def horizon_code(self) -> str:
        """Horizon code for reporting and interpretations (e.g., '15d')."""
        return "15d"


def get_service_config() -> Forecaster15DConfig:
    """
    Get the service-specific configuration.

    Returns:
        Frozen configuration instance for 15-day forecaster.

    Example:
        >>> config = get_service_config()
        >>> assert config.horizon == "daily"
    """
    return Forecaster15DConfig()


__all__ = ["Forecaster15DConfig", "get_service_config"]
