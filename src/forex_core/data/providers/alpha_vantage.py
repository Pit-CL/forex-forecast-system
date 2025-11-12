"""
Alpha Vantage API client.

Provides intraday and daily forex data from Alpha Vantage.
Supports high-frequency (1min, 5min, 15min, 30min, 60min) intraday data.

Requires API key from https://www.alphavantage.co/support/#api-key
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import httpx
import pandas as pd
from loguru import logger

from forex_core.config import Settings


class AlphaVantageClient:
    """
    HTTP client for Alpha Vantage forex API.

    Fetches intraday and daily forex exchange rate data. Automatically
    falls back to daily data if intraday API limit is reached.

    Attributes:
        settings: Application settings.
        BASE_URL: Alpha Vantage API endpoint.

    Example:
        >>> from forex_core.config import get_settings
        >>> settings = get_settings()
        >>> client = AlphaVantageClient(settings)
        >>> series = client.fetch_intraday("USD", "CLP", interval="60min")
        >>> print(series.tail())
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, settings: Settings) -> None:
        """
        Initialize Alpha Vantage API client.

        Args:
            settings: Application settings with alphavantage_api_key.

        Raises:
            ValueError: If ALPHAVANTAGE_API_KEY is not configured.

        Example:
            >>> settings = get_settings()
            >>> client = AlphaVantageClient(settings)
        """
        if not settings.alphavantage_api_key:
            raise ValueError("ALPHAVANTAGE_API_KEY es requerido para intradía.")
        self.settings = settings

    def fetch_intraday(
        self,
        *,
        from_symbol: str = "USD",
        to_symbol: str = "CLP",
        interval: str = "60min",
        output_size: str = "full",
    ) -> pd.Series:
        """
        Fetch intraday forex data.

        Automatically falls back to daily data if API rate limit reached
        or intraday data unavailable.

        Args:
            from_symbol: Source currency (e.g., "USD").
            to_symbol: Target currency (e.g., "CLP").
            interval: Time interval. Options:
                - "1min", "5min", "15min", "30min", "60min"
                Default: "60min"
            output_size: Data size. Options:
                - "compact": Last 100 data points
                - "full": Full historical data (up to 20 years)
                Default: "full"

        Returns:
            pandas Series with close prices. Index is timezone-aware datetime
            in configured timezone, sorted chronologically.

        Raises:
            httpx.HTTPStatusError: If HTTP request fails.
            RuntimeError: If API returns unexpected response format.

        Example:
            >>> # Fetch 60-minute USD/CLP data
            >>> series = client.fetch_intraday(
            ...     from_symbol="USD",
            ...     to_symbol="CLP",
            ...     interval="60min",
            ...     output_size="full"
            ... )
            >>> print(f"Data points: {len(series)}")
            >>> print(f"Latest: {series.iloc[-1]:.2f}")
        """
        params = {
            "function": "FX_INTRADAY",
            "from_symbol": from_symbol,
            "to_symbol": to_symbol,
            "interval": interval,
            "outputsize": output_size,
            "apikey": self.settings.alphavantage_api_key,
        }

        logger.debug(
            f"Fetching Alpha Vantage intraday: {from_symbol}/{to_symbol} @ {interval}"
        )
        response = httpx.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        key = f"Time Series FX ({interval})"
        if key not in data:
            information = data.get("Information")
            if information:
                logger.warning(
                    f"AlphaVantage intradía no disponible ({information}). "
                    "Usando FX_DAILY como fallback."
                )
                return self.fetch_daily(from_symbol=from_symbol, to_symbol=to_symbol)
            raise RuntimeError(f"Respuesta inesperada de AlphaVantage: {data}")

        records = data[key]
        frame = (
            pd.DataFrame.from_dict(records, orient="index")
            .rename(columns={"4. close": "close"})
            .astype(float)
        )
        frame.index = (
            pd.to_datetime(frame.index)
            .tz_localize("UTC")
            .tz_convert(self.settings.report_timezone)
        )
        series = frame["close"].sort_index()

        logger.info(
            f"Fetched {len(series)} intraday points for {from_symbol}/{to_symbol}"
        )
        return series

    def fetch_daily(
        self, *, from_symbol: str = "USD", to_symbol: str = "CLP"
    ) -> pd.Series:
        """
        Fetch daily forex data.

        Args:
            from_symbol: Source currency (e.g., "USD").
            to_symbol: Target currency (e.g., "CLP").

        Returns:
            pandas Series with daily close prices. Index is timezone-aware
            datetime in configured timezone, sorted chronologically.

        Raises:
            httpx.HTTPStatusError: If HTTP request fails.
            RuntimeError: If API returns unexpected response format.

        Example:
            >>> series = client.fetch_daily(from_symbol="USD", to_symbol="CLP")
            >>> print(series.tail())
            2025-11-08    945.12
            2025-11-09    947.85
            2025-11-10    949.23
            2025-11-11    950.11
            2025-11-12    951.45
            Name: close, dtype: float64
        """
        params = {
            "function": "FX_DAILY",
            "from_symbol": from_symbol,
            "to_symbol": to_symbol,
            "apikey": self.settings.alphavantage_api_key,
            "outputsize": "compact",
        }

        logger.debug(f"Fetching Alpha Vantage daily: {from_symbol}/{to_symbol}")
        response = httpx.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        key = "Time Series FX (Daily)"
        if key not in data:
            raise RuntimeError(f"Respuesta inesperada de AlphaVantage FX_DAILY: {data}")

        frame = (
            pd.DataFrame.from_dict(data[key], orient="index")
            .rename(columns={"4. close": "close"})
            .astype(float)
        )
        frame.index = (
            pd.to_datetime(frame.index)
            .tz_localize("UTC")
            .tz_convert(self.settings.report_timezone)
        )

        series = frame["close"].sort_index()
        logger.info(f"Fetched {len(series)} daily points for {from_symbol}/{to_symbol}")
        return series


__all__ = ["AlphaVantageClient"]
