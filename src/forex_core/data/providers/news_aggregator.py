"""
Multi-source news aggregator with automatic fallback.

This module provides a resilient news fetching system that tries multiple
sources in order and gracefully handles failures. It ensures the forecasting
pipeline never fails due to news API unavailability.

Fallback chain:
1. NewsAPI.org (100 requests/day)
2. NewsData.io (200 requests/day)
3. RSS Feeds (unlimited, always available)
4. Empty list (non-blocking - forecast continues without news)

Features:
- Automatic fallback on any error (429, timeout, network, etc.)
- Exponential backoff retry logic
- Request caching to reduce API usage
- Comprehensive logging for troubleshooting
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional
import time

from loguru import logger

from forex_core.config import Settings
from forex_core.data.models import NewsHeadline
from forex_core.data.providers.newswire import NewsApiClient
from forex_core.data.providers.newsdata_io import NewsDataIOClient
from forex_core.data.providers.rss_news import RSSNewsClient


class NewsAggregator:
    """
    Multi-source news aggregator with automatic fallback.

    Tries multiple news sources in order until one succeeds.
    Never fails - always returns a list (possibly empty).

    Example:
        >>> from forex_core.config import get_settings
        >>> settings = get_settings()
        >>> aggregator = NewsAggregator(settings)
        >>> headlines = aggregator.fetch_latest(hours=24)
        >>> print(f"Fetched {len(headlines)} headlines")
        Fetched 15 headlines
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize news aggregator with all available sources.

        Args:
            settings: Application settings with API keys.

        Example:
            >>> settings = get_settings()
            >>> aggregator = NewsAggregator(settings)
        """
        self.settings = settings
        self._init_providers()
        self._cache: Optional[tuple[List[NewsHeadline], datetime]] = None
        self._cache_ttl_hours = 6  # Cache for 6 hours

    def _init_providers(self) -> None:
        """Initialize all available news providers."""
        self.providers = []

        # Provider 1: NewsAPI.org (primary)
        try:
            if self.settings.news_api_key:
                self.providers.append(
                    ("NewsAPI.org", NewsApiClient(self.settings), 1)
                )
                logger.info("NewsAPI.org provider initialized")
            else:
                logger.warning("NEWS_API_KEY not configured, skipping NewsAPI.org")
        except Exception as e:
            logger.warning(f"Failed to initialize NewsAPI.org: {e}")

        # Provider 2: NewsData.io (fallback)
        try:
            if self.settings.newsdata_api_key:
                self.providers.append(
                    ("NewsData.io", NewsDataIOClient(self.settings), 2)
                )
                logger.info("NewsData.io provider initialized")
            else:
                logger.warning("NEWSDATA_API_KEY not configured, skipping NewsData.io")
        except Exception as e:
            logger.warning(f"Failed to initialize NewsData.io: {e}")

        # Provider 3: RSS Feeds (always available, no API key)
        try:
            self.providers.append(
                ("RSS Feeds", RSSNewsClient(), 3)
            )
            logger.info("RSS Feeds provider initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize RSS Feeds: {e}")

        if not self.providers:
            logger.warning(
                "No news providers available! Forecasts will run without news data."
            )

    def fetch_latest(
        self,
        query: Optional[str] = None,
        *,
        hours: int = 48,
        max_retries: int = 2,
        use_cache: bool = True,
    ) -> List[NewsHeadline]:
        """
        Fetch latest news with automatic fallback across multiple sources.

        Tries each provider in sequence until one succeeds. If all fail,
        returns empty list (non-blocking).

        Args:
            query: Search query string. If None, uses configured default.
            hours: Hours of history to fetch. Default: 48.
            max_retries: Maximum retry attempts per provider. Default: 2.
            use_cache: Whether to use cached results if available. Default: True.

        Returns:
            List of NewsHeadline objects. Empty list if all sources fail.

        Example:
            >>> aggregator = NewsAggregator(settings)
            >>> headlines = aggregator.fetch_latest(hours=24)
            >>> if headlines:
            ...     print(f"Got {len(headlines)} headlines")
            ... else:
            ...     print("No news available, continuing without")
        """
        # Check cache first
        if use_cache and self._is_cache_valid():
            logger.info(f"Using cached news data ({len(self._cache[0])} headlines)")
            return self._cache[0]

        if not self.providers:
            logger.warning("No news providers available, returning empty list")
            return []

        # Try each provider in sequence
        for provider_name, provider, source_id in self.providers:
            logger.info(f"Attempting to fetch news from {provider_name}...")

            headlines = self._fetch_with_retry(
                provider=provider,
                provider_name=provider_name,
                source_id=source_id,
                query=query,
                hours=hours,
                max_retries=max_retries,
            )

            if headlines:
                logger.info(
                    f"✓ Successfully fetched {len(headlines)} headlines from {provider_name}"
                )
                # Cache successful result
                self._cache = (headlines, datetime.utcnow())
                return headlines
            else:
                logger.warning(f"✗ {provider_name} returned no headlines, trying next provider...")

        # All providers failed
        logger.warning(
            "⚠️  All news providers failed or returned no data. "
            "Continuing forecast without news data."
        )
        return []

    def _fetch_with_retry(
        self,
        provider: NewsApiClient | NewsDataIOClient | RSSNewsClient,
        provider_name: str,
        source_id: int,
        query: Optional[str],
        hours: int,
        max_retries: int,
    ) -> List[NewsHeadline]:
        """
        Fetch news with exponential backoff retry logic.

        Args:
            provider: News provider instance.
            provider_name: Human-readable provider name for logging.
            source_id: Source registry ID.
            query: Search query.
            hours: Hours of history.
            max_retries: Maximum retry attempts.

        Returns:
            List of headlines, or empty list on failure.
        """
        for attempt in range(max_retries + 1):
            try:
                # RSS provider doesn't accept query parameter
                if isinstance(provider, RSSNewsClient):
                    headlines = provider.fetch_latest(
                        hours=hours,
                        source_id=source_id,
                    )
                else:
                    headlines = provider.fetch_latest(
                        query=query,
                        hours=hours,
                        source_id=source_id,
                    )

                if headlines:
                    return headlines
                else:
                    logger.debug(f"{provider_name} returned no headlines")
                    return []

            except Exception as e:
                error_msg = str(e)

                # Check if it's a rate limit error
                if "429" in error_msg or "Too Many Requests" in error_msg:
                    logger.warning(
                        f"{provider_name} rate limit exceeded (429). "
                        f"Moving to next provider."
                    )
                    return []  # Don't retry on 429, move to next provider

                # For other errors, retry with exponential backoff
                if attempt < max_retries:
                    wait_time = (2 ** attempt)  # Exponential: 1s, 2s, 4s
                    logger.warning(
                        f"{provider_name} error (attempt {attempt + 1}/{max_retries + 1}): {error_msg}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"{provider_name} failed after {max_retries + 1} attempts: {error_msg}"
                    )
                    return []

        return []

    def _is_cache_valid(self) -> bool:
        """
        Check if cached news data is still valid.

        Returns:
            True if cache exists and is within TTL, False otherwise.
        """
        if self._cache is None:
            return False

        headlines, cached_at = self._cache
        age = datetime.utcnow() - cached_at
        return age < timedelta(hours=self._cache_ttl_hours)

    def clear_cache(self) -> None:
        """
        Clear cached news data.

        Useful for forcing a fresh fetch.

        Example:
            >>> aggregator.clear_cache()
            >>> headlines = aggregator.fetch_latest()  # Forces fresh fetch
        """
        self._cache = None
        logger.debug("News cache cleared")

    def get_provider_status(self) -> dict:
        """
        Get status of all configured providers.

        Returns:
            Dictionary with provider names and their availability status.

        Example:
            >>> aggregator = NewsAggregator(settings)
            >>> status = aggregator.get_provider_status()
            >>> print(status)
            {
                'NewsAPI.org': 'configured',
                'NewsData.io': 'configured',
                'RSS Feeds': 'available'
            }
        """
        status = {}
        for provider_name, _, _ in self.providers:
            status[provider_name] = "available"

        if not self.settings.news_api_key:
            status["NewsAPI.org"] = "not_configured"
        if not self.settings.newsdata_api_key:
            status["NewsData.io"] = "not_configured"

        return status


__all__ = ["NewsAggregator"]
