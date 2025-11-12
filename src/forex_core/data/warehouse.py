"""
Time-series data warehouse with Parquet storage.

Provides persistent storage for time-series data with automatic:
- Deduplication (keeps latest values)
- Timezone normalization
- Parquet compression
- Upsert semantics (merge new data with existing)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger

from forex_core.config import Settings


class Warehouse:
    """
    Time-series data warehouse using Parquet files.

    Stores and retrieves time-series data with automatic deduplication,
    timezone handling, and efficient Parquet compression. Each series
    is stored in a separate file.

    Attributes:
        settings: Application settings.
        base_dir: Root directory for warehouse files.

    Example:
        >>> from forex_core.config import get_settings
        >>> warehouse = Warehouse(get_settings())
        >>>
        >>> # Store series
        >>> series = pd.Series([100, 101, 102], index=pd.date_range("2025-01-01", periods=3))
        >>> stored = warehouse.upsert_series("usdclp_daily", series)
        >>>
        >>> # Load series
        >>> loaded = warehouse.load_series("usdclp_daily")
        >>> print(loaded.tail())
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize warehouse.

        Args:
            settings: Application settings with warehouse_dir path.

        Example:
            >>> from forex_core.config import get_settings
            >>> warehouse = Warehouse(get_settings())
        """
        self.settings = settings
        self.base_dir = Path(settings.warehouse_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Warehouse initialized at {self.base_dir}")

    def _path(self, name: str) -> Path:
        """
        Generate file path for a named series.

        Args:
            name: Series identifier. Forward slashes converted to underscores.

        Returns:
            Path to Parquet file.

        Example:
            >>> path = warehouse._path("data/usdclp")
            >>> print(path)
            /path/to/warehouse/data_usdclp.parquet
        """
        safe_name = name.replace("/", "_")
        return self.base_dir / f"{safe_name}.parquet"

    def upsert_series(self, name: str, series: pd.Series) -> pd.Series:
        """
        Merge new data into warehouse and return combined series.

        Implements upsert semantics:
        1. Load existing data (if any)
        2. Combine with new data
        3. Remove duplicates (keep latest)
        4. Sort by date
        5. Save back to warehouse

        Automatically handles:
        - Timezone conversion to UTC
        - Missing values (dropped)
        - Duplicate timestamps (keeps last)

        Args:
            name: Series identifier for storage.
            series: New data to merge. Index must be DatetimeIndex.

        Returns:
            Combined series with all historical + new data.

        Example:
            >>> # First insert
            >>> s1 = pd.Series([100, 101], index=pd.date_range("2025-01-01", periods=2))
            >>> result = warehouse.upsert_series("test", s1)
            >>> print(len(result))
            2
            >>>
            >>> # Second insert (overlapping dates)
            >>> s2 = pd.Series([101.5, 102], index=pd.date_range("2025-01-02", periods=2))
            >>> result = warehouse.upsert_series("test", s2)
            >>> print(len(result))  # 3 unique dates
            3
            >>> print(result.iloc[1])  # 2025-01-02 value from s2 (latest)
            101.5
        """
        # Normalize timezone
        series = series.dropna()
        if hasattr(series.index, "tz") and series.index.tz is not None:
            series = series.tz_convert("UTC").tz_localize(None)

        path = self._path(name)

        # Load existing data if present
        if path.exists():
            logger.debug(f"Loading existing data for {name}")
            existing = pd.read_parquet(path)
            existing.index = pd.to_datetime(existing.index)
            combined = pd.concat([existing.iloc[:, 0], series])
        else:
            logger.debug(f"Creating new warehouse entry for {name}")
            combined = series

        # Deduplicate and sort
        combined = combined[~combined.index.duplicated(keep="last")].sort_index()

        # Save to Parquet
        combined.to_frame(name="value").to_parquet(path)
        logger.info(
            f"Warehouse upsert: {name} ({len(combined)} rows, "
            f"{len(series)} new, path={path.name})"
        )

        return combined

    def load_series(self, name: str) -> Optional[pd.Series]:
        """
        Load time series from warehouse.

        Args:
            name: Series identifier.

        Returns:
            pandas Series with datetime index, or None if not found.

        Example:
            >>> series = warehouse.load_series("usdclp_daily")
            >>> if series is not None:
            ...     print(f"Loaded {len(series)} data points")
            ...     print(f"Range: {series.index[0]} to {series.index[-1]}")
            >>> else:
            ...     print("Series not found")
        """
        path = self._path(name)
        if not path.exists():
            logger.warning(f"Series not found in warehouse: {name}")
            return None

        logger.debug(f"Loading series from warehouse: {name}")
        df = pd.read_parquet(path)
        df.index = pd.to_datetime(df.index)
        series = df["value"].sort_index()

        logger.info(f"Loaded {name} from warehouse ({len(series)} rows)")
        return series

    def delete_series(self, name: str) -> bool:
        """
        Delete a series from the warehouse.

        Args:
            name: Series identifier.

        Returns:
            True if deleted, False if not found.

        Example:
            >>> if warehouse.delete_series("old_data"):
            ...     print("Deleted successfully")
        """
        path = self._path(name)
        if path.exists():
            path.unlink()
            logger.info(f"Deleted warehouse series: {name}")
            return True
        logger.warning(f"Cannot delete, series not found: {name}")
        return False

    def list_series(self) -> list[str]:
        """
        List all series stored in warehouse.

        Returns:
            List of series names (without .parquet extension).

        Example:
            >>> all_series = warehouse.list_series()
            >>> print(f"Warehouse contains {len(all_series)} series:")
            >>> for name in sorted(all_series):
            ...     print(f"  - {name}")
        """
        series_names = [
            p.stem for p in self.base_dir.glob("*.parquet")
        ]
        logger.debug(f"Warehouse contains {len(series_names)} series")
        return series_names


__all__ = ["Warehouse"]
