"""
Configuration overrides for 12-month forecaster service.

This module provides service-specific configuration that extends
the base forex_core settings with 12-month forecast parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from forex_core.config import (
    PROJECTION_MONTHS,
    HISTORICAL_LOOKBACK_DAYS_12M,
    TECH_LOOKBACK_DAYS_12M,
    VOL_LOOKBACK_DAYS_12M,
)


@dataclass(frozen=True)
class Forecaster12MConfig:
    """
    Service-specific configuration for 12-month forecaster.

    These settings override or extend the base forex_core configuration
    for long-term monthly forecasting.

    Attributes:
        horizon: Forecast horizon type (always "monthly" for this service).
        projection_months: Number of months to forecast (12).
        projection_days: Approximate number of days (365).
        frequency: Pandas frequency string for monthly data.
        historical_lookback_days: Days of historical data to use.
        tech_lookback_days: Days for technical indicator calculation.
        vol_lookback_days: Days for volatility calculation.
        report_title: Default title for generated reports.
        report_filename_prefix: Prefix for output filenames.

    Example:
        >>> config = Forecaster12MConfig()
        >>> print(config.projection_months)
        12
        >>> print(config.horizon)
        'monthly'
    """

    # Forecast horizon
    horizon: Literal["monthly"] = "monthly"
    projection_months: int = PROJECTION_MONTHS  # 12 months
    projection_days: int = 365  # Approximate year
    frequency: str = "ME"  # Month End frequency (pandas 2.2+)

    # Lookback periods
    historical_lookback_days: int = HISTORICAL_LOOKBACK_DAYS_12M  # 730 days (2 years)
    tech_lookback_days: int = TECH_LOOKBACK_DAYS_12M  # 90 days
    vol_lookback_days: int = VOL_LOOKBACK_DAYS_12M  # 90 days

    # Report configuration
    report_title: str = "Proyección USD/CLP - Próximos 12 Meses"
    report_filename_prefix: str = "Forecast_12M_USDCLP"

    # Chart configuration
    chart_title_suffix: str = "(12 meses)"

    @property
    def steps(self) -> int:
        """Number of forecast steps (monthly periods)."""
        return self.projection_months


def get_service_config() -> Forecaster12MConfig:
    """
    Get the service-specific configuration.

    Returns:
        Frozen configuration instance for 12-month forecaster.

    Example:
        >>> config = get_service_config()
        >>> assert config.horizon == "monthly"
    """
    return Forecaster12MConfig()


__all__ = ["Forecaster12MConfig", "get_service_config"]
