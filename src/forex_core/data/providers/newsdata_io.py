"""
NewsData.io client for news sentiment analysis.

Fallback news provider with 200 requests/day free tier.
API Documentation: https://newsdata.io/documentation

Requires API key from https://newsdata.io/
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

import httpx
from loguru import logger

from forex_core.config import Settings
from forex_core.data.models import NewsHeadline


class NewsDataIOClient:
    """
    HTTP client for NewsData.io API with sentiment analysis.

    Free tier: 200 requests/day
    Features: Multi-language support, country filtering, category filtering

    Example:
        >>> from forex_core.config import get_settings
        >>> settings = get_settings()
        >>> client = NewsDataIOClient(settings)
        >>> headlines = client.fetch_latest(hours=24, source_id=2)
        >>> for news in headlines[:5]:
        ...     print(f"[{news.sentiment}] {news.title}")
        [Negative] Copper prices fall on demand concerns
        [Positive] Central bank maintains stable policy rate
    """

    BASE_URL = "https://newsdata.io/api/1/news"

    def __init__(self, settings: Settings) -> None:
        """
        Initialize NewsData.io client.

        Args:
            settings: Application settings with newsdata_api_key.

        Raises:
            ValueError: If NEWSDATA_API_KEY is not configured.

        Example:
            >>> settings = get_settings()
            >>> client = NewsDataIOClient(settings)
        """
        if not settings.newsdata_api_key:
            raise ValueError("Missing NEWSDATA_API_KEY for NewsData.io access.")
        self.settings = settings
        self.api_key = settings.newsdata_api_key

    def fetch_latest(
        self,
        query: Optional[str] = None,
        *,
        hours: int = 48,
        source_id: int = 2,
    ) -> List[NewsHeadline]:
        """
        Fetch recent news articles with sentiment analysis.

        Args:
            query: Search query string. If None, uses configured default query.
            hours: Hours of history to fetch. Default: 48.
            source_id: Source registry ID (will be updated by caller).

        Returns:
            List of NewsHeadline objects with sentiment classification.

        Raises:
            httpx.HTTPStatusError: If API request fails.

        Example:
            >>> # Fetch Chile-related news from last 24 hours
            >>> headlines = client.fetch_latest(
            ...     query="Chile economy copper",
            ...     hours=24,
            ...     source_id=2
            ... )
            >>> negative_news = [h for h in headlines if h.sentiment == "Negativo"]
            >>> print(f"Found {len(negative_news)} negative headlines")
        """
        # NewsData.io uses simpler query format (keywords separated by space or comma)
        search_query = query or self._default_query()

        params = {
            "apikey": self.api_key,
            "q": search_query,
            "language": "es",  # Spanish
            "country": "cl",   # Chile focus
            "size": 10,        # Max 10 results per request (free tier)
        }

        logger.debug(f"Fetching NewsData.io: query='{search_query}', hours={hours}")

        try:
            response = httpx.get(
                self.BASE_URL,
                params=params,
                headers={
                    "User-Agent": "forex-forecast-system/1.0",
                },
                timeout=20,
                proxy=self.settings.proxy,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "success":
                logger.warning(f"NewsData.io API returned non-success status: {data.get('status')}")
                return []

            headlines: List[NewsHeadline] = []
            for article in data.get("results", []):
                # Parse publication date
                pub_date_str = article.get("pubDate")
                if not pub_date_str:
                    continue

                try:
                    # NewsData.io format: "2025-11-13 20:00:00"
                    published = datetime.fromisoformat(pub_date_str.replace(" ", "T"))
                except (ValueError, AttributeError):
                    logger.warning(f"Could not parse date: {pub_date_str}")
                    published = datetime.utcnow()

                # Filter by time window
                cutoff = datetime.utcnow() - timedelta(hours=hours)
                if published < cutoff:
                    continue

                title = article.get("title", "").strip()
                if not title:
                    continue

                sentiment = self._naive_sentiment(title)

                headlines.append(
                    NewsHeadline(
                        title=title,
                        url=article.get("link", ""),
                        published_at=published,
                        source=article.get("source_id", "NewsData.io"),
                        sentiment=sentiment,
                        source_id=source_id,
                    )
                )

            logger.info(f"Fetched {len(headlines)} news headlines from NewsData.io")
            return headlines

        except httpx.HTTPStatusError as e:
            logger.error(f"NewsData.io API error: {e}")
            raise
        except Exception as e:
            logger.error(f"NewsData.io unexpected error: {e}")
            return []

    def _default_query(self) -> str:
        """
        Get default search query for Chilean economic news.

        Returns:
            Default query string for NewsData.io format.
        """
        # NewsData.io uses simpler query format
        return "Chile economy Banco Central copper USD CLP peso"

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
            "cae",
            "riesgo",
            "tensión",
            "déficit",
            "contracción",
            "baja",
            "incertidumbre",
            "crisis",
            "recesión",
            "deterioro",
            "caída",
            "desplome",
            "preocupación",
        )
        positives = (
            "sube",
            "mejora",
            "resiliente",
            "crece",
            "avance",
            "expansión",
            "fortalece",
            "optimismo",
            "recuperación",
            "aumento",
            "alza",
            "repunte",
        )

        if any(term in lowered for term in negatives):
            return "Negativo"
        if any(term in lowered for term in positives):
            return "Positivo"
        return "Neutral"


__all__ = ["NewsDataIOClient"]
