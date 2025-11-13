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
PROJECTION_DAYS_7D = 7  # Short-term forecast: 7 days
PROJECTION_DAYS_15D = 15  # Bi-weekly forecast: 15 days
PROJECTION_DAYS_30D = 30  # Monthly forecast: 30 days
PROJECTION_DAYS_90D = 90  # Quarterly forecast: 90 days
PROJECTION_MONTHS = 12  # Long-term forecast: 12 months

# Backward compatibility
PROJECTION_DAYS = PROJECTION_DAYS_7D

# Historical lookback periods (days)
HISTORICAL_LOOKBACK_DAYS_7D = 120  # ~4 months for 7-day forecasts
HISTORICAL_LOOKBACK_DAYS_15D = 240  # ~8 months for 15-day forecasts
HISTORICAL_LOOKBACK_DAYS_30D = 540  # ~18 months for 30-day forecasts
HISTORICAL_LOOKBACK_DAYS_90D = 1095  # 3 years for 90-day forecasts
HISTORICAL_LOOKBACK_DAYS_12M = 365 * 3  # 3 years for 12-month forecasts

# Technical analysis lookback periods (days)
TECH_LOOKBACK_DAYS_7D = 60  # ~2 months for 7-day forecasts
TECH_LOOKBACK_DAYS_15D = 90  # ~3 months for 15-day forecasts
TECH_LOOKBACK_DAYS_30D = 120  # ~4 months for 30-day forecasts
TECH_LOOKBACK_DAYS_90D = 180  # ~6 months for 90-day forecasts
TECH_LOOKBACK_DAYS_12M = 120  # ~4 months for 12-month forecasts

# Volatility calculation lookback periods (days)
VOL_LOOKBACK_DAYS_7D = 30  # 1 month for 7-day forecasts
VOL_LOOKBACK_DAYS_15D = 45  # ~1.5 months for 15-day forecasts
VOL_LOOKBACK_DAYS_30D = 60  # 2 months for 30-day forecasts
VOL_LOOKBACK_DAYS_90D = 120  # 4 months for 90-day forecasts
VOL_LOOKBACK_DAYS_12M = 120  # ~4 months for 12-month forecasts

# Base prompts for AI analysis
BASE_PROMPT_7D = """Actúa como analista cuantitativo especializado en mercados de divisas emergentes. Genera una proyección técnica del tipo de cambio USD/CLP para los próximos 7 días calendario (incluyendo fines de semana) con los requisitos entregados por negocio."""

BASE_PROMPT_15D = """Actúa como analista cuantitativo especializado en mercados de divisas emergentes. Genera una proyección técnica del tipo de cambio USD/CLP para los próximos 15 días calendario con los requisitos entregados por negocio."""

BASE_PROMPT_30D = """Actúa como analista cuantitativo especializado en mercados de divisas emergentes. Genera una proyección técnica del tipo de cambio USD/CLP para los próximos 30 días calendario con los requisitos entregados por negocio."""

BASE_PROMPT_90D = """Actúa como analista cuantitativo especializado en mercados de divisas emergentes. Genera una proyección técnica del tipo de cambio USD/CLP para los próximos 90 días calendario (horizonte trimestral) con los requisitos entregados por negocio."""

BASE_PROMPT_12M = """Actúa como analista cuantitativo especializado en mercados de divisas emergentes. Genera una proyección técnica del tipo de cambio USD/CLP para los próximos 12 meses (horizonte mensual) con los requisitos entregados por negocio."""


def get_base_prompt(horizon: Literal["7d", "15d", "30d", "90d", "12m"] = "7d") -> str:
    """
    Get the base prompt for AI analysis based on forecast horizon.

    Args:
        horizon: Forecast horizon - "7d", "15d", "30d", "90d", or "12m".

    Returns:
        Base prompt string for the specified horizon.

    Example:
        >>> prompt = get_base_prompt("7d")
        >>> print("7 días" in prompt)
        True
        >>> prompt = get_base_prompt("15d")
        >>> print("15 días" in prompt)
        True
        >>> prompt = get_base_prompt("30d")
        >>> print("30 días" in prompt)
        True
        >>> prompt = get_base_prompt("90d")
        >>> print("90 días" in prompt)
        True
        >>> prompt = get_base_prompt("12m")
        >>> print("12 meses" in prompt)
        True
    """
    prompts = {
        "7d": BASE_PROMPT_7D,
        "15d": BASE_PROMPT_15D,
        "30d": BASE_PROMPT_30D,
        "90d": BASE_PROMPT_90D,
        "12m": BASE_PROMPT_12M,
    }
    return prompts.get(horizon, BASE_PROMPT_7D)


__all__ = [
    "LOCAL_TZ",
    "CHILE_GMT_OFFSET",
    "DEFAULT_RECIPIENTS",
    "PROJECTION_DAYS",
    "PROJECTION_DAYS_7D",
    "PROJECTION_DAYS_15D",
    "PROJECTION_DAYS_30D",
    "PROJECTION_DAYS_90D",
    "PROJECTION_MONTHS",
    "HISTORICAL_LOOKBACK_DAYS_7D",
    "HISTORICAL_LOOKBACK_DAYS_15D",
    "HISTORICAL_LOOKBACK_DAYS_30D",
    "HISTORICAL_LOOKBACK_DAYS_90D",
    "HISTORICAL_LOOKBACK_DAYS_12M",
    "TECH_LOOKBACK_DAYS_7D",
    "TECH_LOOKBACK_DAYS_15D",
    "TECH_LOOKBACK_DAYS_30D",
    "TECH_LOOKBACK_DAYS_90D",
    "TECH_LOOKBACK_DAYS_12M",
    "VOL_LOOKBACK_DAYS_7D",
    "VOL_LOOKBACK_DAYS_15D",
    "VOL_LOOKBACK_DAYS_30D",
    "VOL_LOOKBACK_DAYS_90D",
    "VOL_LOOKBACK_DAYS_12M",
    "BASE_PROMPT_7D",
    "BASE_PROMPT_15D",
    "BASE_PROMPT_30D",
    "BASE_PROMPT_90D",
    "BASE_PROMPT_12M",
    "get_base_prompt",
]
