"""
Yahoo Finance API client.

Fetches market data from Yahoo Finance including:
- Stock prices
- Indices (DXY, VIX, S&P 500)
- ETFs (EEM for emerging markets)
- Currency futures
- Commodities

No API key required.
"""

from __future__ import annotations

from typing import Optional

import httpx
import pandas as pd
from loguru import logger

from forex_core.config import Settings


class YahooClient:
    """
    HTTP client for Yahoo Finance chart API.

    Fetches historical price data for stocks, indices, ETFs, and other
    financial instruments. Returns data as pandas Series.

    Attributes:
        settings: Application settings.
        BASE_URL: Template URL for Yahoo Finance chart API.

    Example:
        >>> from forex_core.config import get_settings
        >>> client = YahooClient(get_settings())
        >>> dxy = client.fetch_series("DX=F", range_window="1y")
        >>> print(dxy.tail())
        2025-11-08    106.234
        2025-11-09    106.189
        2025-11-10    106.345
        2025-11-11    106.421
        2025-11-12    106.512
        Name: DX=F, dtype: float64
    """

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    def __init__(self, settings: Settings) -> None:
        """
        Initialize Yahoo Finance client.

        Args:
            settings: Application settings.

        Example:
            >>> settings = get_settings()
            >>> client = YahooClient(settings)
        """
        self.settings = settings

    def fetch_series(
        self, symbol: str, *, range_window: str = "5y"
    ) -> pd.Series:
        """
        Fetch historical price series for a symbol.

        Args:
            symbol: Yahoo Finance ticker symbol. Examples:
                - "DX=F" for Dollar Index futures
                - "^VIX" for VIX volatility index
                - "EEM" for iShares MSCI Emerging Markets ETF
                - "AAPL" for Apple stock
            range_window: Time range string. Options:
                - "1d", "5d", "1mo", "3mo", "6mo"
                - "1y", "2y", "5y", "10y"
                - "ytd", "max"
                Default: "5y"

        Returns:
            pandas Series with close prices. Index is timezone-aware datetime
            normalized to midnight in configured timezone. NaN values dropped.

        Raises:
            httpx.HTTPStatusError: If API request fails.
            KeyError: If symbol not found.

        Example:
            >>> # Fetch 10 years of DXY data
            >>> dxy = client.fetch_series("DX=F", range_window="10y")
            >>> print(f"Points: {len(dxy)}, Latest: {dxy.iloc[-1]:.2f}")
            Points: 2518, Latest: 106.51
            >>>
            >>> # Fetch VIX volatility index
            >>> vix = client.fetch_series("^VIX", range_window="1y")
            >>> print(f"VIX average: {vix.mean():.2f}")
            VIX average: 18.45
        """
        url = self.BASE_URL.format(symbol=symbol)
        params = {"range": range_window, "interval": "1d"}

        logger.debug(f"Fetching Yahoo Finance: {symbol} ({range_window})")
        response = httpx.get(
            url,
            params=params,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
            proxy=self.settings.proxy,
        )
        response.raise_for_status()

        payload = response.json()
        result = payload["chart"]["result"][0]

        timestamps = pd.to_datetime(result["timestamp"], unit="s")
        closes = result["indicators"]["quote"][0]["close"]

        series = pd.Series(closes, index=timestamps).dropna()

        # Normalize to midnight in configured timezone
        series.index = (
            series.index.tz_localize("UTC")
            .tz_convert(self.settings.report_timezone)
            .normalize()
            .tz_localize(None)
        )
        series.name = symbol

        logger.info(f"Fetched {len(series)} data points for {symbol}")
        return series


__all__ = ["YahooClient"]
