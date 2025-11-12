"""
Backup macro calendar client.

Secondary data source for macroeconomic events to mitigate rate limits
or primary source failures. Uses alternative CDN mirror.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Sequence

import httpx
from loguru import logger

from forex_core.config import Settings
from forex_core.data.models import MacroEvent


class BackupMacroCalendarClient:
    """
    Backup HTTP client for macroeconomic calendar events.

    Alternative data source for economic calendar when primary source
    (ForexFactory) is unavailable due to rate limits or downtime.

    Example:
        >>> from forex_core.config import get_settings
        >>> client = BackupMacroCalendarClient(get_settings())
        >>> events = client.upcoming_events(
        ...     countries=("USD", "EUR"),
        ...     days=7,
        ...     source_id=2
        ... )
        >>> print(f"Backup source provided {len(events)} events")
    """

    ALT_URL = "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.json"

    def __init__(self, settings: Settings) -> None:
        """
        Initialize backup calendar client.

        Args:
            settings: Application settings with proxy configuration.

        Example:
            >>> settings = get_settings()
            >>> client = BackupMacroCalendarClient(settings)
        """
        self.settings = settings

    def upcoming_events(
        self, *, countries: Sequence[str], days: int, source_id: int
    ) -> List[MacroEvent]:
        """
        Fetch upcoming events from backup source.

        Args:
            countries: Sequence of ISO-3 country codes.
            days: Number of days ahead to fetch.
            source_id: Source registry ID for tracking.

        Returns:
            List of MacroEvent objects. Returns empty list on errors.

        Example:
            >>> events = client.upcoming_events(
            ...     countries=("USD", "CNY"),
            ...     days=7,
            ...     source_id=3
            ... )
            >>> for event in events:
            ...     if event.impact == "High":
            ...         print(f"{event.datetime}: {event.title}")
        """
        try:
            logger.debug(f"Fetching backup calendar from {self.ALT_URL}")
            response = httpx.get(
                self.ALT_URL,
                headers={"User-Agent": "forex-forecast-system/1.0"},
                timeout=15,
                proxy=self.settings.proxy,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning(f"Backup calendar also failed: {exc}")
            return []

        payload = response.json()
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=days)
        events: List[MacroEvent] = []

        for item in payload:
            country = item.get("country")
            if country not in countries:
                continue

            raw_date = item.get("date")
            if not raw_date:
                continue

            dt = datetime.fromisoformat(raw_date)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            if not (now <= dt <= cutoff):
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

        logger.info(f"Backup calendar provided {len(events)} events")
        return events


__all__ = ["BackupMacroCalendarClient"]
