"""
NewsAPI client for news sentiment analysis.

Fetches recent news articles related to forex, commodities, and economic
policy. Includes basic sentiment classification.

Requires API key from https://newsapi.org/
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

import httpx
from loguru import logger

from forex_core.config import Settings
from forex_core.data.models import NewsHeadline


class NewsApiClient:
    """
    HTTP client for NewsAPI.org with sentiment analysis.

    Fetches recent news articles and performs basic keyword-based
    sentiment classification (Positive, Negative, Neutral).

    Example:
        >>> from forex_core.config import get_settings
        >>> settings = get_settings()
        >>> client = NewsApiClient(settings)
        >>> headlines = client.fetch_latest(hours=24, source_id=1)
        >>> for news in headlines[:5]:
        ...     print(f"[{news.sentiment}] {news.title}")
        [Negative] Copper prices fall on demand concerns
        [Positive] Central bank maintains stable policy rate
    """

    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self, settings: Settings) -> None:
        """
        Initialize NewsAPI client.

        Args:
            settings: Application settings with news_api_key.

        Raises:
            ValueError: If NEWS_API_KEY is not configured.

        Example:
            >>> settings = get_settings()
            >>> client = NewsApiClient(settings)
        """
        if not settings.news_api_key:
            raise ValueError("Missing NEWS_API_KEY for NewsAPI access.")
        self.settings = settings

    def fetch_latest(
        self,
        query: Optional[str] = None,
        *,
        hours: int = 48,
        source_id: int = 0,
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
            ...     query="Banco Central Chile OR copper",
            ...     hours=24,
            ...     source_id=5
            ... )
            >>> negative_news = [h for h in headlines if h.sentiment == "Negativo"]
            >>> print(f"Found {len(negative_news)} negative headlines")
        """
        window_start = datetime.utcnow() - timedelta(hours=hours)
        params = {
            "q": query or self.settings.news_query,
            "from": window_start.isoformat(timespec="seconds"),
            "sortBy": "publishedAt",
            "language": "es",
            "pageSize": 25,
        }

        logger.debug(f"Fetching news: query='{params['q']}', hours={hours}")
        response = httpx.get(
            self.BASE_URL,
            params=params,
            headers={
                "Authorization": f"Bearer {self.settings.news_api_key}",
                "User-Agent": "forex-forecast-system/1.0",
            },
            timeout=20,
            proxy=self.settings.proxy,
        )
        response.raise_for_status()
        data = response.json()

        headlines: List[NewsHeadline] = []
        for article in data.get("articles", []):
            published = datetime.fromisoformat(
                article["publishedAt"].replace("Z", "+00:00")
            )
            sentiment = self._naive_sentiment(article.get("title", ""))

            headlines.append(
                NewsHeadline(
                    title=article.get("title", "").strip(),
                    url=article.get("url", ""),
                    published_at=published,
                    source=article.get("source", {}).get("name", "NewsAPI"),
                    sentiment=sentiment,
                    source_id=source_id,
                )
            )

        logger.info(f"Fetched {len(headlines)} news headlines")
        return headlines

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
        )

        if any(term in lowered for term in negatives):
            return "Negativo"
        if any(term in lowered for term in positives):
            return "Positivo"
        return "Neutral"


__all__ = ["NewsApiClient"]
