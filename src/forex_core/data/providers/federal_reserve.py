"""
Federal Reserve website scraper.

Scrapes the Federal Reserve's FOMC calendar and Summary of Economic Projections
to extract:
- Next FOMC meeting date
- Dot plot projections (median federal funds rate forecasts)
- Links to projection materials (PDF and HTML)
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from loguru import logger

from forex_core.config import Settings

from .base import BaseHTTPClient


class FederalReserveClient(BaseHTTPClient):
    """
    Web scraper for Federal Reserve FOMC calendar and projections.

    Extracts FOMC meeting dates and dot plot median projections by
    parsing the Federal Reserve website HTML.

    Example:
        >>> from forex_core.config import get_settings
        >>> client = FederalReserveClient(get_settings())
        >>> next_meeting = client.next_meeting()
        >>> print(f"Next FOMC: {next_meeting}")
        Next FOMC: 2025-12-15 00:00:00-05:00
        >>>
        >>> dot_plot = client.dot_plot_medians()
        >>> print(dot_plot)
        {'2025': 4.5, '2026': 3.75, '2027': 3.0, 'Longer run': 2.5}
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize Federal Reserve scraper.

        Args:
            settings: Application settings with proxy configuration.

        Example:
            >>> settings = get_settings()
            >>> client = FederalReserveClient(settings)
        """
        super().__init__("https://www.federalreserve.gov", proxy=settings.proxy)
        self.settings = settings
        self._soup: Optional[BeautifulSoup] = None

    def _get_soup(self) -> BeautifulSoup:
        """
        Fetch and parse FOMC calendar page (cached).

        Returns:
            BeautifulSoup object with parsed HTML.

        Raises:
            httpx.HTTPStatusError: If page fetch fails.
        """
        if self._soup is None:
            logger.debug("Fetching FOMC calendar page")
            html = self.fetch_text("/monetarypolicy/fomccalendars.htm")
            self._soup = BeautifulSoup(html, "lxml")
        return self._soup

    def next_meeting(self) -> Optional[datetime]:
        """
        Find the next scheduled FOMC meeting date.

        Parses the FOMC calendar page to extract upcoming meeting dates
        and returns the first one in the future.

        Returns:
            Timezone-aware datetime of next meeting, or None if not found.

        Example:
            >>> next_mtg = client.next_meeting()
            >>> if next_mtg:
            ...     print(f"Next FOMC in {(next_mtg - datetime.now(next_mtg.tzinfo)).days} days")
            Next FOMC in 33 days
        """
        soup = self._get_soup()
        months = list(_calendar_months())
        meetings = []

        for panel in soup.select("div.panel"):
            heading = panel.find("h4")
            if not heading:
                continue

            # Extract year from heading
            match = re.search(r"(20\d{2})", heading.text)
            if not match:
                continue
            year = int(match.group(1))

            # Parse meeting rows
            for row in panel.select(".fomc-meeting"):
                month_el = row.select_one(".fomc-meeting__month")
                date_el = row.select_one(".fomc-meeting__date")

                if not month_el or not date_el:
                    continue

                month_name = month_el.get_text(strip=True)
                if month_name not in months:
                    continue

                day_match = re.search(r"\d{1,2}", date_el.get_text(strip=True))
                if not day_match:
                    continue

                day = int(day_match.group(0))
                dt = datetime(
                    year, months.index(month_name), day, tzinfo=self.settings.tz
                )
                meetings.append(dt)

        # Remove duplicates and sort
        meetings = sorted({m for m in meetings if m})
        now = datetime.now(self.settings.tz)

        # Return first future meeting
        for meeting in meetings:
            if meeting > now:
                logger.info(f"Next FOMC meeting: {meeting}")
                return meeting

        logger.warning("No future FOMC meetings found")
        return None

    def latest_projection_links(self) -> Tuple[str, str]:
        """
        Extract links to latest Summary of Economic Projections.

        Finds the most recent projection materials (PDF and HTML versions)
        from the FOMC calendar page.

        Returns:
            Tuple of (pdf_url, html_url).

        Raises:
            RuntimeError: If projection links not found.

        Example:
            >>> pdf_url, html_url = client.latest_projection_links()
            >>> print(pdf_url)
            https://www.federalreserve.gov/monetarypolicy/files/fomcprojtabl20250312.pdf
        """
        soup = self._get_soup()
        pdf_href = None
        html_href = None

        for anchor in soup.select('a[href*="fomcprojtabl"]'):
            href = anchor.get("href", "")
            if href.endswith(".pdf") and not pdf_href:
                pdf_href = urljoin(self.base_url, href)
            if href.endswith(".htm") and not html_href:
                html_href = urljoin(self.base_url, href)
            if pdf_href and html_href:
                break

        if not (pdf_href and html_href):
            raise RuntimeError("No projection materials links found on FOMC page.")

        logger.info(f"Found projection materials: {html_href}")
        return pdf_href, html_href

    def dot_plot_medians(self) -> Dict[str, float]:
        """
        Extract median federal funds rate projections from dot plot table.

        Scrapes the Summary of Economic Projections HTML table to extract
        the median forecast for federal funds rate by year.

        Returns:
            Dictionary mapping year/period to median rate (%).
            Example: {'2025': 4.5, '2026': 3.75, '2027': 3.0, 'Longer run': 2.5}

        Raises:
            RuntimeError: If projection table not found.
            httpx.HTTPStatusError: If projection page fetch fails.

        Example:
            >>> medians = client.dot_plot_medians()
            >>> print(f"2025 median projection: {medians['2025']}%")
            2025 median projection: 4.5%
        """
        _, html_url = self.latest_projection_links()

        logger.debug(f"Fetching projection table from {html_url}")
        html = self.fetch_text(html_url)
        soup = BeautifulSoup(html, "lxml")

        table = soup.find("table")
        if not table:
            raise RuntimeError("Projection table not found.")

        # Extract headers (years)
        header_row = table.find_all("tr")[1]
        headers = [cell.get_text(strip=True) for cell in header_row.find_all("th")][:4]

        medians = {}

        # Find Federal funds rate row
        for row in table.find_all("tr")[2:]:
            label_th = row.find("th")
            if not label_th:
                continue

            label = label_th.get_text(strip=True)
            if "Federal funds rate" in label:
                values = [
                    _clean_numeric(cell.get_text(strip=True))
                    for cell in row.find_all("td")[:4]
                ]
                medians = {headers[idx]: value for idx, value in enumerate(values)}
                logger.info(f"Extracted dot plot medians: {medians}")
                break

        return medians


def _clean_numeric(value: str) -> float:
    """
    Clean and parse numeric value from table cell.

    Handles various formatting issues:
    - Special dash characters (em-dash, en-dash)
    - Comma as decimal separator
    - Range values (takes first number)

    Args:
        value: Raw string from table cell.

    Returns:
        Parsed float value or NaN if parsing fails.

    Example:
        >>> _clean_numeric("4.5")
        4.5
        >>> _clean_numeric("4.5–5.0")
        4.5
        >>> _clean_numeric("N/A")
        nan
    """
    value = value.replace("â\x80\x93", "-").replace(",", ".")
    try:
        # Take first number from range (e.g., "4.5-5.0" -> 4.5)
        return float(value.split("-")[0])
    except ValueError:
        return float("nan")


def _calendar_months():
    """
    Get list of month names for parsing.

    Returns:
        List of month names from calendar module.
        Index 0 is empty string, indices 1-12 are month names.
    """
    from calendar import month_name

    return list(month_name)


__all__ = ["FederalReserveClient"]
