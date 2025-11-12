"""
MindicadorCL client for Chilean economic indicators.

Provides access to Chilean Central Bank data via the mindicador.cl API:
- USD/CLP exchange rate (Dólar Observado)
- TPM (Tasa Política Monetaria - monetary policy rate)
- IPC (Índice de Precios al Consumidor - consumer price index)
- Copper prices (Libra de Cobre)
- And many other Chilean economic indicators

Data is automatically cached to reduce API calls.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from loguru import logger

from forex_core.config import Settings
from forex_core.data.utils import dump_json, load_json

from .base import BaseHTTPClient


class MindicadorClient(BaseHTTPClient):
    """
    HTTP client for mindicador.cl API (Chilean Central Bank data).

    Fetches economic indicators from Chile including USD/CLP exchange rates,
    monetary policy rates, inflation, and commodity prices. Implements
    file-based caching with configurable TTL.

    Attributes:
        settings: Application settings.
        cache_dir: Directory for cached API responses.

    Example:
        >>> from forex_core.config import get_settings
        >>> client = MindicadorClient(get_settings())
        >>> data = client.get_latest()
        >>> print(data["dolar"]["valor"])
        950.25
        >>> series = client.get_indicator("dolar", year=2024)
        >>> print(len(series["serie"]))
        365
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize mindicador.cl API client.

        Args:
            settings: Application settings containing base URL and proxy config.

        Example:
            >>> from forex_core.config import get_settings
            >>> settings = get_settings()
            >>> client = MindicadorClient(settings)
        """
        super().__init__(settings.mindicador_base_url, proxy=settings.proxy)
        self.settings = settings
        self.cache_dir = Path(settings.data_dir) / "cache" / "mindicador"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_latest(self) -> Dict:
        """
        Fetch latest values for all indicators.

        Returns cached data if fresh (< 6 hours old), otherwise fetches
        from API and updates cache.

        Returns:
            Dictionary with all indicators. Structure:
            {
                "dolar": {"valor": 950.25, "fecha": "2025-11-12T..."},
                "tpm": {"valor": 5.75, "fecha": "2025-11-01T..."},
                "ipc": {"valor": 105.2, "fecha": "2025-10-31T..."},
                ...
            }

        Raises:
            httpx.HTTPStatusError: If API request fails.

        Example:
            >>> data = client.get_latest()
            >>> usdclp = data["dolar"]["valor"]
            >>> timestamp = data["dolar"]["fecha"]
            >>> print(f"USD/CLP: {usdclp} as of {timestamp}")
        """
        cache_path = self.cache_dir / "latest.json"
        if cached := load_json(cache_path):
            if self._is_fresh(cached):
                logger.debug("Using cached mindicador latest data")
                return cached["payload"]

        logger.info("Fetching latest indicators from mindicador.cl")
        payload = self.fetch_json("")
        dump_json(
            cache_path, {"fetched_at": datetime.utcnow().isoformat(), "payload": payload}
        )
        return payload

    def get_indicator(
        self, indicator: str, year: Optional[int] = None
    ) -> Dict:
        """
        Fetch historical time series for a specific indicator.

        Returns cached data if fresh (< 3 hours old), otherwise fetches
        from API and updates cache.

        Args:
            indicator: Indicator code (e.g., "dolar", "tpm", "ipc", "libra_cobre").
            year: Optional year for historical data. If None, fetches current year.

        Returns:
            Dictionary with indicator metadata and time series:
            {
                "codigo": "dolar",
                "nombre": "Dólar observado",
                "unidad_medida": "Pesos",
                "serie": [
                    {"fecha": "2024-01-01T...", "valor": 945.2},
                    {"fecha": "2024-01-02T...", "valor": 948.1},
                    ...
                ]
            }

        Raises:
            httpx.HTTPStatusError: If API request fails.

        Example:
            >>> # Get 2024 USD/CLP daily data
            >>> data = client.get_indicator("dolar", year=2024)
            >>> series = data["serie"]
            >>> print(f"Days: {len(series)}, First: {series[0]['valor']}")
            >>>
            >>> # Get current year TPM data
            >>> tpm = client.get_indicator("tpm")
        """
        url_suffix = f"/{year}" if year else ""
        cache_suffix = f"_{year}" if year else "_latest"
        cache_path = self.cache_dir / f"{indicator}{cache_suffix}.json"

        if cached := load_json(cache_path):
            if self._is_fresh(cached, hours=3):
                logger.debug(f"Using cached {indicator} data for {year or 'latest'}")
                return cached["payload"]

        logger.info(f"Fetching {indicator} from mindicador.cl (year={year or 'current'})")
        payload = self.fetch_json(f"/{indicator}{url_suffix}")
        dump_json(
            cache_path, {"fetched_at": datetime.utcnow().isoformat(), "payload": payload}
        )
        return payload

    def _is_fresh(self, cached: Dict, *, hours: int = 6) -> bool:
        """
        Check if cached data is still fresh.

        Args:
            cached: Cached data dictionary with "fetched_at" timestamp.
            hours: Maximum age in hours. Default: 6.

        Returns:
            True if cache is fresh, False if stale or invalid.

        Example:
            >>> cached = {"fetched_at": "2025-11-12T10:00:00", "payload": {...}}
            >>> client._is_fresh(cached, hours=6)
            True
        """
        fetched_at = cached.get("fetched_at")
        if not fetched_at:
            return False
        ts = datetime.fromisoformat(fetched_at)
        age_seconds = (datetime.utcnow() - ts).total_seconds()
        return age_seconds < hours * 3600


__all__ = ["MindicadorClient"]
