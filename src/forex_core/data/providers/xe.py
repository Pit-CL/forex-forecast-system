"""
XE.com currency converter client.

Scrapes real-time mid-market exchange rates from XE.com's currency converter.
Provides international reference rates without API key requirements.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from loguru import logger

from forex_core.config import Settings

from .base import BaseHTTPClient


class XeClient(BaseHTTPClient):
    """
    HTTP client for XE.com currency converter (web scraping).

    Fetches real-time mid-market exchange rates by scraping XE.com's
    converter page. No API key required.

    Example:
        >>> from forex_core.config import get_settings
        >>> client = XeClient(get_settings())
        >>> rate, timestamp = client.fetch_rate("USD", "CLP")
        >>> print(f"USD/CLP: {rate} as of {timestamp}")
        USD/CLP: 950.25 as of 2025-11-12 14:30:00+00:00
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize XE.com client.

        Args:
            settings: Application settings with xe_converter_url.

        Example:
            >>> settings = get_settings()
            >>> client = XeClient(settings)
        """
        super().__init__(settings.xe_converter_url, proxy=settings.proxy)

    def fetch_rate(
        self, from_currency: str = "USD", to_currency: str = "CLP"
    ) -> tuple[float, datetime]:
        """
        Fetch current exchange rate from XE.com.

        Scrapes the XE.com converter page to extract the current mid-market
        rate and its timestamp.

        Args:
            from_currency: Source currency code (ISO 4217, e.g., "USD").
            to_currency: Target currency code (ISO 4217, e.g., "CLP").

        Returns:
            Tuple of (rate, timestamp):
            - rate: Exchange rate as float
            - timestamp: Timezone-aware datetime (UTC)

        Raises:
            httpx.HTTPStatusError: If HTTP request fails.
            KeyError: If rate not found in page data.
            json.JSONDecodeError: If page structure changed.

        Example:
            >>> rate, ts = client.fetch_rate("USD", "CLP")
            >>> print(f"{from_currency}/{to_currency}: {rate:.2f}")
            USD/CLP: 950.25
            >>> print(f"Updated: {ts.isoformat()}")
            Updated: 2025-11-12T14:30:00+00:00
        """
        logger.debug(f"Fetching XE.com rate: {from_currency}/{to_currency}")
        response = self.get(
            "",
            params={"Amount": 1, "From": from_currency, "To": to_currency},
            headers={"User-Agent": "Mozilla/5.0"},
        )

        soup = BeautifulSoup(response.text, "lxml")
        script = soup.find("script", id="__NEXT_DATA__")

        if not script or not script.string:
            raise ValueError("XE.com page structure has changed - could not find data")

        data = json.loads(script.string)
        rates_payload = data["props"]["pageProps"]["initialRatesData"]
        rate = rates_payload["rates"][to_currency]
        timestamp = datetime.fromtimestamp(
            rates_payload["timestamp"] / 1000, tz=timezone.utc
        )

        logger.info(f"XE.com {from_currency}/{to_currency}: {rate:.4f} @ {timestamp}")
        return rate, timestamp


__all__ = ["XeClient"]
