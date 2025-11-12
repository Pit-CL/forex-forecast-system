"""
Application constants.

This module defines constants used across the forex forecasting system.
Includes timezone settings, email recipients, forecast horizons, and lookback periods.

The constants are parameterized to support both 7-day and 12-month forecast horizons.
"""

from __future__ import annotations

from typing import Literal
from zoneinfo import ZoneInfo

# Timezone configuration
LOCAL_TZ = ZoneInfo("America/Santiago")
CHILE_GMT_OFFSET = -4  # Used for conversions when tz database unavailable

# Default email recipients for reports
DEFAULT_RECIPIENTS = ("rafael@cavara.cl", "valentina@cavara.cl")

# Forecast horizons
PROJECTION_DAYS = 7  # Short-term forecast: 7 days
PROJECTION_MONTHS = 12  # Long-term forecast: 12 months

# Historical lookback periods (days)
HISTORICAL_LOOKBACK_DAYS_7D = 120  # ~4 months for 7-day forecasts
HISTORICAL_LOOKBACK_DAYS_12M = 365 * 3  # 3 years for 12-month forecasts

# Technical analysis lookback periods (days)
TECH_LOOKBACK_DAYS_7D = 60  # ~2 months for 7-day forecasts
TECH_LOOKBACK_DAYS_12M = 120  # ~4 months for 12-month forecasts

# Volatility calculation lookback periods (days)
VOL_LOOKBACK_DAYS_7D = 30  # 1 month for 7-day forecasts
VOL_LOOKBACK_DAYS_12M = 120  # ~4 months for 12-month forecasts

# Base prompts for AI analysis
BASE_PROMPT_7D = """Actúa como analista cuantitativo especializado en mercados de divisas emergentes. Genera una proyección técnica del tipo de cambio USD/CLP para los próximos 7 días calendario (incluyendo fines de semana) con los requisitos entregados por negocio."""

BASE_PROMPT_12M = """Actúa como analista cuantitativo especializado en mercados de divisas emergentes. Genera una proyección técnica del tipo de cambio USD/CLP para los próximos 12 meses (horizonte mensual) con los requisitos entregados por negocio."""


def get_base_prompt(horizon: Literal["7d", "12m"] = "7d") -> str:
    """
    Get the base prompt for AI analysis based on forecast horizon.

    Args:
        horizon: Forecast horizon - "7d" for 7-day or "12m" for 12-month.

    Returns:
        Base prompt string for the specified horizon.

    Example:
        >>> prompt = get_base_prompt("7d")
        >>> print("7 días" in prompt)
        True
        >>> prompt = get_base_prompt("12m")
        >>> print("12 meses" in prompt)
        True
    """
    if horizon == "12m":
        return BASE_PROMPT_12M
    return BASE_PROMPT_7D


__all__ = [
    "LOCAL_TZ",
    "CHILE_GMT_OFFSET",
    "DEFAULT_RECIPIENTS",
    "PROJECTION_DAYS",
    "PROJECTION_MONTHS",
    "HISTORICAL_LOOKBACK_DAYS_7D",
    "HISTORICAL_LOOKBACK_DAYS_12M",
    "TECH_LOOKBACK_DAYS_7D",
    "TECH_LOOKBACK_DAYS_12M",
    "VOL_LOOKBACK_DAYS_7D",
    "VOL_LOOKBACK_DAYS_12M",
    "BASE_PROMPT_7D",
    "BASE_PROMPT_12M",
    "get_base_prompt",
]
