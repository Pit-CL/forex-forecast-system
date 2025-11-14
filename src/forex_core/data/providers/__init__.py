"""
Data providers for external financial and economic APIs.

This module contains HTTP client wrappers for various data sources used
in forex forecasting. All providers support retry logic, caching, and
proper error handling.

Available Providers:
    - BaseHTTPClient: Base class with retry logic and error handling
    - MindicadorClient: Chilean Central Bank indicators
    - FredClient: Federal Reserve Economic Data
    - XeClient: XE.com forex rates
    - YahooClient: Yahoo Finance market data
    - StooqClient: Stooq historical data
    - AlphaVantageClient: Alpha Vantage intraday forex
    - FederalReserveClient: FOMC calendar and projections
    - MacroCalendarClient: Economic calendar events
    - BackupMacroCalendarClient: Fallback calendar source
    - NewsApiClient: News with sentiment analysis
    - CopperPricesClient: Copper futures prices with technical features

Example:
    >>> from forex_core.data.providers import MindicadorClient
    >>> from forex_core.config import get_settings
    >>>
    >>> settings = get_settings()
    >>> client = MindicadorClient(settings)
    >>> data = client.get_latest()
    >>> print(data["dolar"]["valor"])
"""

from __future__ import annotations

from .alpha_vantage import AlphaVantageClient
from .base import BaseHTTPClient
from .copper_prices import CopperPricesClient
from .federal_reserve import FederalReserveClient
from .fred import FredClient
from .macro_calendar import MacroCalendarClient
from .macro_calendar_backup import BackupMacroCalendarClient
from .mindicador import MindicadorClient
from .newswire import NewsApiClient
from .stooq import StooqClient
from .xe import XeClient
from .yahoo import YahooClient

__all__ = [
    "BaseHTTPClient",
    "MindicadorClient",
    "FredClient",
    "XeClient",
    "YahooClient",
    "StooqClient",
    "AlphaVantageClient",
    "FederalReserveClient",
    "MacroCalendarClient",
    "BackupMacroCalendarClient",
    "NewsApiClient",
    "CopperPricesClient",
]
