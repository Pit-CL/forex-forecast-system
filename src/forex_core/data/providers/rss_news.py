"""
RSS Feed client for news sentiment analysis.

Fallback news provider using public RSS feeds (no API limits).
Always available as last resort when all paid APIs fail.

No API key required - parses public RSS feeds.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

# Use defusedxml to prevent XXE (XML External Entity) attacks
import defusedxml.ElementTree as ET

import httpx
from loguru import logger

from forex_core.data.models import NewsHeadline


class RSSNewsClient:
    """
    RSS Feed client for news headlines.

    Free forever, no API limits. Used as last-resort fallback.
    Parses RSS feeds from major Chilean and economic news sources.

    Example:
        >>> client = RSSNewsClient()
        >>> headlines = client.fetch_latest(hours=24, source_id=3)
        >>> for news in headlines[:5]:
        ...     print(f"[{news.sentiment}] {news.title}")
        [Negative] Copper prices fall on demand concerns
        [Positive] Central bank maintains stable policy rate
    """

    # Public RSS feeds (no authentication required)
    RSS_FEEDS = [
        # Chilean Financial & Economic News
        "https://www.df.cl/rss/",  # Diario Financiero (primary financial source)
        "https://www.latercera.com/feed/",  # La Tercera (general + economic)
        "https://www.emol.com/rss/economia.xml",  # Emol Economía
        "https://www.biobiochile.cl/lista/economia/rss",  # BioBio Economía

        # Additional Chilean Economic Sources
        "https://www.pulso.cl/feed/",  # Pulso (business & finance)
        "https://www.elmostrador.cl/mercados/feed/",  # El Mostrador Mercados
        "https://www.cnnchile.com/feed/",  # CNN Chile (economic coverage)
    ]

    def __init__(self) -> None:
        """Initialize RSS client (no API key needed)."""
        pass

    def fetch_latest(
        self,
        *,
        hours: int = 48,
        source_id: int = 3,
    ) -> List[NewsHeadline]:
        """
        Fetch recent news articles from RSS feeds.

        Args:
            hours: Hours of history to fetch. Default: 48.
            source_id: Source registry ID (will be updated by caller).

        Returns:
            List of NewsHeadline objects with sentiment classification.

        Example:
            >>> client = RSSNewsClient()
            >>> headlines = client.fetch_latest(hours=24, source_id=3)
            >>> economic_news = [h for h in headlines if 'economía' in h.title.lower()]
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        all_headlines: List[NewsHeadline] = []

        for feed_url in self.RSS_FEEDS:
            try:
                headlines = self._fetch_feed(feed_url, cutoff, source_id)
                all_headlines.extend(headlines)
            except Exception as e:
                logger.warning(f"Failed to fetch RSS feed {feed_url}: {e}")
                continue

        # Filter for Chilean economic keywords
        filtered = self._filter_relevant(all_headlines)

        logger.info(f"Fetched {len(filtered)} relevant news headlines from RSS feeds")
        return filtered[:25]  # Limit to 25 most recent

    def _fetch_feed(
        self,
        feed_url: str,
        cutoff: datetime,
        source_id: int,
    ) -> List[NewsHeadline]:
        """
        Fetch and parse a single RSS feed.

        Args:
            feed_url: URL of RSS feed.
            cutoff: Only return articles after this datetime.
            source_id: Source registry ID.

        Returns:
            List of NewsHeadline objects.
        """
        try:
            response = httpx.get(
                feed_url,
                timeout=15,
                headers={"User-Agent": "forex-forecast-system/1.0"},
            )
            response.raise_for_status()

            root = ET.fromstring(response.content)
            headlines: List[NewsHeadline] = []

            # Parse RSS format
            for item in root.findall(".//item"):
                title_elem = item.find("title")
                link_elem = item.find("link")
                pub_date_elem = item.find("pubDate")

                if title_elem is None or title_elem.text is None:
                    continue

                title = title_elem.text.strip()
                url = link_elem.text.strip() if link_elem is not None and link_elem.text else ""

                # Parse publication date (RSS format)
                published = self._parse_rss_date(pub_date_elem)
                if published < cutoff:
                    continue

                sentiment = self._naive_sentiment(title)
                source_name = self._extract_source_name(feed_url)

                headlines.append(
                    NewsHeadline(
                        title=title,
                        url=url,
                        published_at=published,
                        source=source_name,
                        sentiment=sentiment,
                        source_id=source_id,
                    )
                )

            return headlines

        except ET.ParseError as e:
            logger.warning(f"Failed to parse RSS XML from {feed_url}: {e}")
            return []
        except Exception as e:
            logger.warning(f"Error fetching RSS feed {feed_url}: {e}")
            return []

    def _parse_rss_date(self, pub_date_elem) -> datetime:
        """
        Parse RSS pubDate element.

        Supports multiple date formats used by different RSS feeds.

        Args:
            pub_date_elem: XML element containing publication date.

        Returns:
            Parsed datetime object, or current time if parsing fails.
        """
        if pub_date_elem is None or pub_date_elem.text is None:
            return datetime.utcnow()

        date_str = pub_date_elem.text.strip()

        # Try common RSS date formats
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 822
            "%a, %d %b %Y %H:%M:%S GMT",
            "%Y-%m-%dT%H:%M:%S%z",       # ISO 8601
            "%Y-%m-%d %H:%M:%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        logger.debug(f"Could not parse RSS date: {date_str}")
        return datetime.utcnow()

    def _extract_source_name(self, feed_url: str) -> str:
        """
        Extract source name from feed URL.

        Args:
            feed_url: URL of RSS feed.

        Returns:
            Human-readable source name.
        """
        if "df.cl" in feed_url:
            return "Diario Financiero"
        elif "latercera" in feed_url:
            return "La Tercera"
        elif "emol" in feed_url:
            return "Emol"
        elif "biobio" in feed_url:
            return "BioBioChile"
        elif "pulso" in feed_url:
            return "Pulso"
        elif "elmostrador" in feed_url:
            return "El Mostrador"
        elif "cnn" in feed_url:
            return "CNN Chile"
        else:
            return "RSS Feed"

    def _filter_relevant(self, headlines: List[NewsHeadline]) -> List[NewsHeadline]:
        """
        Filter headlines for Chilean economic relevance.

        Args:
            headlines: All fetched headlines.

        Returns:
            Filtered list of relevant headlines.
        """
        keywords = {
            # Foreign Exchange & Currency
            "dólar", "peso", "tipo de cambio", "usd", "clp", "divisa", "forex",

            # Central Bank & Monetary Policy
            "banco central", "bccch", "bch", "tpm", "política monetaria", "rpm",
            "rosanna costa", "consejo banco central",

            # Inflation & Economic Indicators
            "inflación", "ipc", "índice de precios", "ine", "imacec", "pib",
            "crecimiento", "recesión", "actividad económica",

            # Commodities (Chile-specific)
            "cobre", "copper", "codelco", "cochilco", "minería", "litio",
            "molibdeno", "celulosa", "salmón",

            # Fiscal Policy
            "hacienda", "ministerio de hacienda", "fisco", "déficit fiscal",
            "presupuesto", "marcel", "deuda pública",

            # International Factors
            "fed", "fomc", "tasas", "interés", "reserva federal",

            # Trade & Balance
            "comercio", "exportación", "importación", "balanza", "aduanas",
            "svs", "cmf", "afp",
        }

        relevant = []
        for headline in headlines:
            title_lower = headline.title.lower()
            if any(kw in title_lower for kw in keywords):
                relevant.append(headline)

        return relevant

    def _naive_sentiment(self, title: str) -> str:
        """
        Classify sentiment using keyword matching.

        Simple rule-based sentiment classifier using Spanish keywords.
        Not machine learning-based, suitable for basic directional signals.

        Args:
            title: Article headline text.

        Returns:
            Sentiment classification: "Negativo", "Positivo", or "Neutral".

        Example:
            >>> client._naive_sentiment("Economía cae por tercer mes")
            'Negativo'
            >>> client._naive_sentiment("Crecimiento sube a máximo histórico")
            'Positivo'
            >>> client._naive_sentiment("Banco Central publica informe")
            'Neutral'
        """
        lowered = title.lower()

        negatives = (
            "cae", "riesgo", "tensión", "déficit", "contracción", "baja",
            "incertidumbre", "crisis", "recesión", "deterioro", "caída",
            "desplome", "preocupación", "temor", "alerta",
        )
        positives = (
            "sube", "mejora", "resiliente", "crece", "avance", "expansión",
            "fortalece", "optimismo", "recuperación", "aumento", "alza",
            "repunte", "robusto", "sólido",
        )

        if any(term in lowered for term in negatives):
            return "Negativo"
        if any(term in lowered for term in positives):
            return "Positivo"
        return "Neutral"


__all__ = ["RSSNewsClient"]
