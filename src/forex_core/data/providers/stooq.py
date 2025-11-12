"""
Stooq market data client.

Fetches historical stock and forex data from Stooq.com.
Returns data in CSV format parsed to pandas DataFrame.
"""

from __future__ import annotations

from io import StringIO
from typing import Optional

import pandas as pd
from loguru import logger

from forex_core.config import Settings

from .base import BaseHTTPClient


class StooqClient(BaseHTTPClient):
    """
    HTTP client for Stooq historical data downloads.

    Fetches daily OHLCV (Open, High, Low, Close, Volume) data for stocks,
    currencies, and indices from Stooq.com.

    Example:
        >>> from forex_core.config import get_settings
        >>> client = StooqClient(get_settings())
        >>> df = client.fetch_daily_series("usdclp", limit=100)
        >>> print(df[["Close"]].tail())
                    Close
        Date
        2025-11-08  945.12
        2025-11-09  947.85
        2025-11-10  949.23
        2025-11-11  950.11
        2025-11-12  951.45
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize Stooq client.

        Args:
            settings: Application settings with stooq_base_url.

        Example:
            >>> settings = get_settings()
            >>> client = StooqClient(settings)
        """
        super().__init__(settings.stooq_base_url, proxy=settings.proxy)

    def fetch_daily_series(
        self, symbol: str, limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Fetch daily historical data for a symbol.

        Args:
            symbol: Stooq symbol (e.g., "usdclp", "aapl.us", "^spx").
            limit: Optional limit on number of most recent rows to return.

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume.
            Index is DatetimeIndex with column name "Date".

        Raises:
            httpx.HTTPStatusError: If HTTP request fails.
            pd.errors.ParserError: If CSV parsing fails.

        Example:
            >>> # Fetch last 30 days of USD/CLP
            >>> df = client.fetch_daily_series("usdclp", limit=30)
            >>> print(df.head())
                        Open    High     Low   Close  Volume
            Date
            2025-10-14  940.2  942.5  939.8  941.2      0
            2025-10-15  941.2  943.1  940.5  942.8      0
            ...
        """
        logger.debug(f"Fetching Stooq data: {symbol}")
        response = self.get(
            "",
            params={
                "s": symbol,
                "i": "d",  # Daily interval
            },
        )

        df = pd.read_csv(StringIO(response.text))
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").set_index("Date")

        if limit:
            df = df.tail(limit)
            logger.info(f"Fetched {len(df)} rows for {symbol} (limited to {limit})")
        else:
            logger.info(f"Fetched {len(df)} rows for {symbol}")

        return df


__all__ = ["StooqClient"]
