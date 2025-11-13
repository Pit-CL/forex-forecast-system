"""
Configuration overrides for 7-day forecaster service.

This module provides service-specific configuration that extends
the base forex_core settings with 7-day forecast parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from forex_core.config import (
    PROJECTION_DAYS,
    HISTORICAL_LOOKBACK_DAYS_7D,
    TECH_LOOKBACK_DAYS_7D,
    VOL_LOOKBACK_DAYS_7D,
)


@dataclass(frozen=True)
class Forecaster7DConfig:
    """
    Service-specific configuration for 7-day forecaster.

    These settings override or extend the base forex_core configuration
    for short-term daily forecasting.

    Attributes:
        horizon: Forecast horizon type (always "daily" for this service).
        projection_days: Number of days to forecast (7).
        frequency: Pandas frequency string for daily data.
        historical_lookback_days: Days of historical data to use.
        tech_lookback_days: Days for technical indicator calculation.
        vol_lookback_days: Days for volatility calculation.
        report_title: Default title for generated reports.
        report_filename_prefix: Prefix for output filenames.

    Example:
        >>> config = Forecaster7DConfig()
        >>> print(config.projection_days)
        7
        >>> print(config.horizon)
        'daily'
    """

    # Forecast horizon
    horizon: Literal["daily"] = "daily"
    projection_days: int = PROJECTION_DAYS  # 7 days
    frequency: str = "D"  # Daily frequency

    # Lookback periods
    historical_lookback_days: int = HISTORICAL_LOOKBACK_DAYS_7D  # 180 days
    tech_lookback_days: int = TECH_LOOKBACK_DAYS_7D  # 30 days
    vol_lookback_days: int = VOL_LOOKBACK_DAYS_7D  # 30 days

    # Report configuration
    report_title: str = "Proyección USD/CLP - Próximos 7 Días"
    report_filename_prefix: str = "Forecast_7D_USDCLP"

    # Chart configuration
    chart_title_suffix: str = "(7 días)"

    @property
    def steps(self) -> int:
        """Number of forecast steps (same as projection_days for daily)."""
        return self.projection_days

    @property
    def horizon_code(self) -> str:
        """Horizon code for reporting and interpretations (e.g., '7d')."""
        return "7d"


def get_service_config() -> Forecaster7DConfig:
    """
    Get the service-specific configuration.

    Returns:
        Frozen configuration instance for 7-day forecaster.

    Example:
        >>> config = get_service_config()
        >>> assert config.horizon == "daily"
    """
    return Forecaster7DConfig()


__all__ = ["Forecaster7DConfig", "get_service_config"]
