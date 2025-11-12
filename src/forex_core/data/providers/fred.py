"""
FRED (Federal Reserve Economic Data) API client.

Provides access to thousands of economic time series from the St. Louis Fed,
including:
- Federal Funds rate
- GDP data
- Inflation indicators
- Labor market data
- International trade data

Requires FRED API key from https://fred.stlouisfed.org/docs/api/api_key.html
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
from loguru import logger

from forex_core.config import Settings

from .base import BaseHTTPClient


class FredClient(BaseHTTPClient):
    """
    HTTP client for FRED (Federal Reserve Economic Data) API.

    Fetches economic time series data from the Federal Reserve Economic Database.
    Returns data as pandas DataFrames for easy analysis.

    Attributes:
        api_key: FRED API key.
        BASE: Base URL for FRED API.

    Example:
        >>> from forex_core.config import get_settings
        >>> settings = get_settings()
        >>> client = FredClient(settings)
        >>> df = client.get_series("DFEDTARU")  # Fed Funds Upper Target
        >>> print(df.tail())
    """

    BASE = "https://api.stlouisfed.org"

    def __init__(self, settings: Settings) -> None:
        """
        Initialize FRED API client.

        Args:
            settings: Application settings with fred_api_key.

        Raises:
            ValueError: If FRED_API_KEY is not configured.

        Example:
            >>> settings = get_settings()
            >>> client = FredClient(settings)
        """
        if not settings.fred_api_key:
            raise ValueError("FRED_API_KEY environment variable is required.")
        super().__init__(self.BASE, proxy=settings.proxy)
        self.api_key = settings.fred_api_key

    def get_series(
        self,
        series_id: str,
        *,
        observation_start: Optional[date] = None,
        observation_end: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        Fetch time series data for a FRED series.

        Args:
            series_id: FRED series identifier (e.g., "DFEDTARU", "GDP", "CPIAUCSL").
            observation_start: Optional start date for data range.
            observation_end: Optional end date for data range.

        Returns:
            DataFrame with datetime index and single column named after series_id.
            Missing values and non-numeric data are automatically dropped.

        Raises:
            httpx.HTTPStatusError: If API request fails.
            KeyError: If series_id not found.

        Example:
            >>> from datetime import date, timedelta
            >>> start = date.today() - timedelta(days=365)
            >>> df = client.get_series("DFEDTARU", observation_start=start)
            >>> print(df.head())
                        DFEDTARU
            date
            2024-11-12      5.50
            2024-11-13      5.50
            ...
        """
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
        }
        if observation_start:
            params["observation_start"] = observation_start.isoformat()
        if observation_end:
            params["observation_end"] = observation_end.isoformat()

        logger.debug(f"Fetching FRED series: {series_id}")
        response = self.fetch_json("/fred/series/observations", params=params)
        observations = response.get("observations", [])

        df = pd.DataFrame(observations)
        if df.empty:
            logger.warning(f"FRED series {series_id} returned no data")
            return df

        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["value"]).set_index("date")
        df.rename(columns={"value": series_id}, inplace=True)

        logger.info(f"Fetched {len(df)} observations for FRED:{series_id}")
        return df[[series_id]]


__all__ = ["FredClient"]
