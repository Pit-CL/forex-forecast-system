"""
Data management module for forex-forecast-system.

This module provides comprehensive data collection, caching, and management
capabilities for forex forecasting. It includes:

- Data providers: Multiple external API clients for financial and economic data
- Warehouse: Time-series data storage and versioning with Parquet
- Loader: Unified data loading and orchestration
- Registry: Source tracking and citation management

Providers:
    - MindicadorClient: Chilean Central Bank indicators (USD/CLP, copper, TPM)
    - FredClient: Federal Reserve Economic Data
    - XeClient: XE.com real-time forex rates
    - YahooClient: Yahoo Finance market data
    - StooqClient: Stooq historical data
    - AlphaVantageClient: Intraday forex data
    - FederalReserveClient: FOMC calendar and dot plot projections
    - MacroCalendarClient: Economic calendar events
    - BackupMacroCalendarClient: Fallback calendar source
    - NewsApiClient: News sentiment analysis

Example:
    >>> from forex_core.data import DataLoader
    >>> from forex_core.config import get_settings
    >>>
    >>> settings = get_settings()
    >>> loader = DataLoader(settings)
    >>> bundle = loader.load()
    >>>
    >>> print(f"USD/CLP: {bundle.indicators['usdclp_spot'].value}")
    >>> print(f"Sources: {len(bundle.sources)}")
"""

from __future__ import annotations

from .loader import DataBundle, DataLoader
from .models import (
    ForecastPackage,
    ForecastPoint,
    Indicator,
    MacroEvent,
    NewsHeadline,
)
from .registry import Source, SourceRegistry
from .warehouse import Warehouse

__all__ = [
    # Main orchestrator
    "DataLoader",
    "DataBundle",
    # Storage and tracking
    "Warehouse",
    "SourceRegistry",
    "Source",
    # Data models
    "Indicator",
    "MacroEvent",
    "NewsHeadline",
    "ForecastPoint",
    "ForecastPackage",
]
