"""Configuration modules for forex_core."""

from .base import Settings, get_settings
from .constants import (
    CHILE_GMT_OFFSET,
    DEFAULT_RECIPIENTS,
    HISTORICAL_LOOKBACK_DAYS_12M,
    HISTORICAL_LOOKBACK_DAYS_7D,
    LOCAL_TZ,
    PROJECTION_DAYS,
    PROJECTION_MONTHS,
    TECH_LOOKBACK_DAYS_12M,
    TECH_LOOKBACK_DAYS_7D,
    VOL_LOOKBACK_DAYS_12M,
    VOL_LOOKBACK_DAYS_7D,
    get_base_prompt,
)

__all__ = [
    # Settings
    "Settings",
    "get_settings",
    # Constants
    "LOCAL_TZ",
    "DEFAULT_RECIPIENTS",
    "PROJECTION_DAYS",
    "PROJECTION_MONTHS",
    "HISTORICAL_LOOKBACK_DAYS_7D",
    "HISTORICAL_LOOKBACK_DAYS_12M",
    "TECH_LOOKBACK_DAYS_7D",
    "TECH_LOOKBACK_DAYS_12M",
    "VOL_LOOKBACK_DAYS_7D",
    "VOL_LOOKBACK_DAYS_12M",
    "CHILE_GMT_OFFSET",
    "get_base_prompt",
]
