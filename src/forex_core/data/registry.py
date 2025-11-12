"""
Source tracking and citation registry.

Maintains a registry of all data sources used in forecasting with metadata
for documentation, auditing, and citation purposes.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger


@dataclass
class Source:
    """
    Data source record with metadata.

    Attributes:
        idx: Unique source ID (1-indexed).
        category: Source category (e.g., "Datos de mercado", "Pronósticos institucionales").
        name: Human-readable source name.
        url: Source URL for verification.
        timestamp: When data was fetched.
        note: Additional context or description.

    Example:
        >>> source = Source(
        ...     idx=1,
        ...     category="Datos de mercado",
        ...     name="MindicadorCL - USD/CLP",
        ...     url="https://mindicador.cl/api/dolar",
        ...     timestamp=datetime.now(),
        ...     note="Banco Central de Chile"
        ... )
    """

    idx: int
    category: str
    name: str
    url: str
    timestamp: datetime
    note: str


class SourceRegistry:
    """
    Registry for tracking all data sources used in a forecast.

    Maintains a list of sources with unique IDs for citation purposes.
    Supports markdown export for report generation.

    Example:
        >>> from datetime import datetime
        >>> registry = SourceRegistry()
        >>>
        >>> # Add sources
        >>> id1 = registry.add(
        ...     category="Datos de mercado",
        ...     name="MindicadorCL - USD/CLP",
        ...     url="https://mindicador.cl/api/dolar",
        ...     timestamp=datetime.now(),
        ...     note="Tipo de cambio oficial"
        ... )
        >>>
        >>> # Use in report
        >>> print(f"USD/CLP spot rate {registry.cite(id1)}: 950.25")
        USD/CLP spot rate [1]: 950.25
        >>>
        >>> # Export for documentation
        >>> print(registry.as_markdown())
    """

    def __init__(self) -> None:
        """
        Initialize empty source registry.

        Example:
            >>> registry = SourceRegistry()
            >>> print(len(registry))
            0
        """
        self._sources: List[Source] = []
        logger.debug("Initialized empty source registry")

    def add(
        self,
        *,
        category: str,
        name: str,
        url: str,
        timestamp: datetime,
        note: str,
    ) -> int:
        """
        Add a new data source to the registry.

        Args:
            category: Source category for grouping.
            name: Human-readable source name.
            url: URL to the data source.
            timestamp: When the data was fetched.
            note: Additional context or description.

        Returns:
            Unique source ID (1-indexed integer).

        Example:
            >>> source_id = registry.add(
            ...     category="Datos de mercado",
            ...     name="Yahoo Finance - DXY",
            ...     url="https://finance.yahoo.com/quote/DX=F",
            ...     timestamp=datetime.now(),
            ...     note="Dollar Index futures"
            ... )
            >>> print(f"Source ID: {source_id}")
            Source ID: 1
        """
        idx = len(self._sources) + 1
        self._sources.append(
            Source(
                idx=idx,
                category=category,
                name=name,
                url=url,
                timestamp=timestamp,
                note=note,
            )
        )
        logger.debug(f"Added source [{idx}]: {name}")
        return idx

    def cite(self, idx: int) -> str:
        """
        Generate citation reference for a source ID.

        Args:
            idx: Source ID.

        Returns:
            Citation string in format "[N]".

        Example:
            >>> registry.cite(5)
            '[5]'
        """
        return f"[{idx}]"

    def get(self, idx: int) -> Optional[Source]:
        """
        Retrieve source by ID.

        Args:
            idx: Source ID (1-indexed).

        Returns:
            Source object or None if not found.

        Example:
            >>> source = registry.get(1)
            >>> if source:
            ...     print(f"{source.name}: {source.url}")
        """
        for source in self._sources:
            if source.idx == idx:
                return source
        return None

    def latest_timestamp(self) -> Optional[datetime]:
        """
        Get the most recent data timestamp across all sources.

        Returns:
            Latest timestamp, or None if registry is empty.

        Example:
            >>> latest = registry.latest_timestamp()
            >>> if latest:
            ...     print(f"Data as of: {latest.isoformat()}")
        """
        if not self._sources:
            return None
        return max(source.timestamp for source in self._sources)

    def as_markdown(self) -> str:
        """
        Export registry as markdown-formatted source list.

        Groups sources by category and formats as nested bullet list
        with citations.

        Returns:
            Markdown string with all sources.

        Example:
            >>> markdown = registry.as_markdown()
            >>> print(markdown)
            - **Datos de mercado**
              - [1] MindicadorCL - USD/CLP (2025-11-12T14:30) - https://... — Oficial BCCh
              - [2] Yahoo Finance - DXY (2025-11-12T14:25) - https://... — Dollar Index
            - **Pronósticos institucionales**
              - [3] Federal Reserve SEP (2025-11-12T14:00) - https://... — Dot plot medians
        """
        grouped: Dict[str, List[Source]] = defaultdict(list)
        for source in self._sources:
            grouped[source.category].append(source)

        lines: List[str] = []
        for category, items in grouped.items():
            lines.append(f"- **{category}**")
            for source in sorted(items, key=lambda x: x.idx):
                timestamp_str = source.timestamp.isoformat(timespec="minutes")
                lines.append(
                    f"  - [{source.idx}] {source.name} ({timestamp_str}) - "
                    f"{source.url} — {source.note}"
                )

        result = "\n".join(lines)
        logger.debug(f"Exported {len(self._sources)} sources to markdown")
        return result

    def __len__(self) -> int:
        """
        Get number of sources in registry.

        Returns:
            Count of registered sources.

        Example:
            >>> print(f"Registry contains {len(registry)} sources")
            Registry contains 12 sources
        """
        return len(self._sources)

    def __repr__(self) -> str:
        """String representation of registry."""
        return f"SourceRegistry(sources={len(self._sources)})"


__all__ = ["Source", "SourceRegistry"]
