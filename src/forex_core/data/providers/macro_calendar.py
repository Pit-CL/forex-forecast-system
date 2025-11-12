"""
Macro economic calendar client.

Fetches upcoming macroeconomic events (GDP releases, employment data,
central bank meetings, etc.) from ForexFactory or similar calendar APIs.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Sequence

import httpx
from loguru import logger

from forex_core.config import Settings
from forex_core.data.models import MacroEvent


class MacroCalendarClient:
    """
    HTTP client for macroeconomic calendar events.

    Fetches scheduled economic releases and events that may impact
    forex markets. Filters by country and date range.

    Example:
        >>> from forex_core.config import get_settings
        >>> client = MacroCalendarClient(get_settings())
        >>> events = client.upcoming_events(
        ...     countries=("USD", "EUR", "CNY"),
        ...     days=7,
        ...     source_id=1
        ... )
        >>> for event in events[:3]:
        ...     print(f"{event.datetime}: {event.title} ({event.impact})")
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize macro calendar client.

        Args:
            settings: Application settings with macro_events_url.

        Example:
            >>> settings = get_settings()
            >>> client = MacroCalendarClient(settings)
        """
        self.settings = settings
        self.target_url = str(settings.macro_events_url)

    def fetch_events(self) -> List[dict]:
        """
        Fetch raw calendar events from API.

        Returns:
            List of event dictionaries. Returns empty list on HTTP errors.

        Example:
            >>> raw_events = client.fetch_events()
            >>> print(f"Fetched {len(raw_events)} events")
        """
        try:
            logger.debug(f"Fetching macro calendar from {self.target_url}")
            response = httpx.get(
                self.target_url,
                headers={
                    "User-Agent": "forex-forecast-system/1.0",
                    "Accept": "application/json",
                },
                timeout=15,
                proxy=self.settings.proxy,
            )
            response.raise_for_status()
            events = response.json()
            logger.info(f"Fetched {len(events)} macro events from calendar")
            return events
        except httpx.HTTPStatusError as exc:
            logger.warning(
                f"No se pudo obtener el calendario macro ({exc}). Continuaré sin eventos."
            )
            return []

    def upcoming_events(
        self, *, countries: Sequence[str], days: int = 7, source_id: int
    ) -> List[MacroEvent]:
        """
        Fetch and filter upcoming macroeconomic events.

        Filters events by:
        - Country codes
        - Date range (now to now + days)

        Args:
            countries: Sequence of ISO-3 country codes (e.g., ("USD", "EUR", "CNY")).
            days: Number of days ahead to fetch. Default: 7.
            source_id: Source registry ID for tracking.

        Returns:
            List of MacroEvent objects, sorted by datetime.

        Example:
            >>> events = client.upcoming_events(
            ...     countries=("USD", "CAD"),
            ...     days=14,
            ...     source_id=5
            ... )
            >>> high_impact = [e for e in events if e.impact == "High"]
            >>> print(f"Found {len(high_impact)} high-impact events")
        """
        raw = self.fetch_events()
        cutoff_start = datetime.now(timezone.utc)
        cutoff_end = cutoff_start + timedelta(days=days)
        events: List[MacroEvent] = []

        for item in raw:
            country = item.get("country")
            if country not in countries:
                continue

            # Parse datetime
            dt = datetime.fromisoformat(item["date"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            # Filter by date range
            if not (cutoff_start <= dt <= cutoff_end):
                continue

            events.append(
                MacroEvent(
                    title=item.get("title", "").strip(),
                    country=country,
                    datetime=dt,
                    impact=item.get("impact", "Low"),
                    actual=item.get("actual"),
                    forecast=item.get("forecast"),
                    previous=item.get("previous"),
                    source_id=source_id,
                )
            )

        events_sorted = sorted(events, key=lambda ev: ev.datetime)
        logger.info(
            f"Filtered to {len(events_sorted)} events for {countries} "
            f"over next {days} days"
        )
        return events_sorted


__all__ = ["MacroCalendarClient"]
