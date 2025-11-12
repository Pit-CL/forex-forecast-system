"""
Base HTTP client with retry logic and error handling.

This module provides the foundational HTTP client class used by all data providers.
It includes automatic retry with exponential backoff, timeout handling, and
proxy support.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from loguru import logger
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential


class BaseHTTPClient:
    """
    Base HTTP client with automatic retries and standardized error handling.

    Provides GET requests with exponential backoff retry logic, configurable
    timeouts, and proxy support. All data providers inherit from this class.

    Attributes:
        base_url: Base URL for API endpoints.
        _client: Internal httpx.Client instance.

    Example:
        >>> client = BaseHTTPClient(
        ...     "https://api.example.com",
        ...     timeout=30.0,
        ...     proxy={"http://": "http://proxy:8080"}
        ... )
        >>> data = client.fetch_json("/endpoint", params={"key": "value"})
        >>> client.close()
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 15.0,
        proxy: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Initialize HTTP client with base configuration.

        Args:
            base_url: Base URL for all requests (trailing slash removed).
            timeout: Request timeout in seconds. Default: 15.0.
            proxy: Optional proxy configuration dict.
            headers: Optional custom headers. If None, uses defaults.

        Example:
            >>> client = BaseHTTPClient(
            ...     "https://api.example.com/v1",
            ...     timeout=30,
            ...     headers={"Authorization": "Bearer token"}
            ... )
        """
        self.base_url = str(base_url).rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers=headers
            or {
                "User-Agent": "forex-forecast-system/1.0 (+github.com/yourusername/forex-forecast-system)",
                "Accept": "application/json, text/html;q=0.8",
                "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
            },
            proxy=proxy,
        )

    def close(self) -> None:
        """
        Close the HTTP client and release resources.

        Should be called when done with the client, or use context manager.

        Example:
            >>> client = BaseHTTPClient("https://api.example.com")
            >>> try:
            ...     data = client.fetch_json("/data")
            ... finally:
            ...     client.close()
        """
        self._client.close()

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """
        Perform GET request with automatic retry logic.

        Retries up to 3 times with exponential backoff (1s, 2s, 4s, max 10s).
        Raises HTTPStatusError on 4xx/5xx responses after all retries exhausted.

        Args:
            url: URL path (relative to base_url) or absolute URL.
            **kwargs: Additional arguments passed to httpx.Client.get().

        Returns:
            httpx.Response object with successful response.

        Raises:
            httpx.HTTPStatusError: If response status is 4xx or 5xx after retries.
            httpx.TimeoutException: If request times out after retries.
            RetryError: If max retry attempts exceeded.

        Example:
            >>> response = client.get("/api/data", params={"id": 123})
            >>> print(response.status_code)
            200
        """
        response = self._client.get(url, **kwargs)
        response.raise_for_status()
        return response

    def fetch_json(
        self, path: str = "", *, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Fetch and parse JSON from endpoint.

        Convenience method that performs GET request and parses JSON response.

        Args:
            path: URL path relative to base_url. Default: "" (root).
            params: Optional query parameters.

        Returns:
            Parsed JSON data (dict, list, or primitive).

        Raises:
            httpx.HTTPStatusError: On HTTP errors.
            json.JSONDecodeError: If response is not valid JSON.

        Example:
            >>> data = client.fetch_json("/api/rates", params={"currency": "USD"})
            >>> print(data["rate"])
            1.25
        """
        response = self.get(path, params=params)
        return response.json()

    def fetch_text(
        self, path: str = "", *, params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Fetch raw text from endpoint.

        Useful for HTML scraping or non-JSON APIs.

        Args:
            path: URL path relative to base_url. Default: "" (root).
            params: Optional query parameters.

        Returns:
            Raw response text.

        Raises:
            httpx.HTTPStatusError: On HTTP errors.

        Example:
            >>> html = client.fetch_text("/page")
            >>> print(len(html))
            5432
        """
        response = self.get(path, params=params)
        return response.text


__all__ = ["BaseHTTPClient"]
