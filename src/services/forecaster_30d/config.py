"""
Configuration overrides for 30-day forecaster service.

This module provides service-specific configuration that extends
the base forex_core settings with 30-day forecast parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from forex_core.config import (
    PROJECTION_DAYS_30D,
    HISTORICAL_LOOKBACK_DAYS_30D,
    TECH_LOOKBACK_DAYS_30D,
    VOL_LOOKBACK_DAYS_30D,
)


@dataclass(frozen=True)
class Forecaster30DConfig:
    """
    Service-specific configuration for 30-day forecaster.

    These settings override or extend the base forex_core configuration
    for monthly forecasting (executed on day 1 of each month).

    Attributes:
        horizon: Forecast horizon type (always "daily" for this service).
        projection_days: Number of days to forecast (30).
        frequency: Pandas frequency string for daily data.
        historical_lookback_days: Days of historical data to use.
        tech_lookback_days: Days for technical indicator calculation.
        vol_lookback_days: Days for volatility calculation.
        report_title: Default title for generated reports.
        report_filename_prefix: Prefix for output filenames.

    Example:
        >>> config = Forecaster30DConfig()
        >>> print(config.projection_days)
        30
        >>> print(config.horizon)
        'daily'
    """

    # Forecast horizon
    horizon: Literal["daily"] = "daily"
    projection_days: int = PROJECTION_DAYS_30D  # 30 days
    frequency: str = "D"  # Daily frequency

    # Lookback periods (recommended by usdclp agent)
    historical_lookback_days: int = HISTORICAL_LOOKBACK_DAYS_30D  # 540 days (~18 months)
    tech_lookback_days: int = TECH_LOOKBACK_DAYS_30D  # 120 days (~4 months)
    vol_lookback_days: int = VOL_LOOKBACK_DAYS_30D  # 60 days (2 months)

    # Report configuration
    report_title: str = "Proyección USD/CLP - Próximos 30 Días"
    report_filename_prefix: str = "Forecast_30D_USDCLP"

    # Chart configuration
    chart_title_suffix: str = "(30 días)"

    @property
    def steps(self) -> int:
        """Number of forecast steps (same as projection_days for daily)."""
        return self.projection_days


def get_service_config() -> Forecaster30DConfig:
    """
    Get the service-specific configuration.

    Returns:
        Frozen configuration instance for 30-day forecaster.

    Example:
        >>> config = get_service_config()
        >>> assert config.horizon == "daily"
    """
    return Forecaster30DConfig()


__all__ = ["Forecaster30DConfig", "get_service_config"]
