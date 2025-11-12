"""
Utility functions for data management.

This module provides helper functions for JSON caching, file I/O,
and data formatting used by data providers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import pandas as pd


def load_json(path: Path) -> Optional[Any]:
    """
    Load JSON data from file if it exists.

    Args:
        path: Path to JSON file.

    Returns:
        Parsed JSON data or None if file doesn't exist.

    Example:
        >>> data = load_json(Path("cache/data.json"))
        >>> if data:
        ...     print(data["timestamp"])
    """
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return None


def dump_json(path: Path, payload: Any) -> None:
    """
    Write JSON data to file with pretty formatting.

    Creates parent directories if they don't exist. Uses UTF-8 encoding
    and handles datetime/other non-serializable objects with str().

    Args:
        path: Destination file path.
        payload: Data to serialize to JSON.

    Example:
        >>> dump_json(
        ...     Path("cache/data.json"),
        ...     {"timestamp": datetime.now(), "value": 123}
        ... )
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)


def ensure_parent(path: Path) -> None:
    """
    Create parent directories for a file path if they don't exist.

    Args:
        path: File path whose parent directories should be created.

    Example:
        >>> ensure_parent(Path("data/cache/provider/file.json"))
        >>> # data/cache/provider/ now exists
    """
    path.parent.mkdir(parents=True, exist_ok=True)


def percent_change(new: float, old: float) -> float:
    """
    Calculate percentage change between two values.

    Args:
        new: New value.
        old: Old value.

    Returns:
        Percentage change. Returns 0.0 if old value is 0.

    Example:
        >>> percent_change(105, 100)
        5.0
        >>> percent_change(95, 100)
        -5.0
    """
    if old == 0:
        return 0.0
    return (new - old) / old * 100


def to_markdown_table(frame: pd.DataFrame) -> str:
    """
    Convert DataFrame to markdown table format.

    Args:
        frame: DataFrame to convert.

    Returns:
        Markdown-formatted table string.

    Example:
        >>> df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        >>> print(to_markdown_table(df))
        | col1 | col2 |
        |------|------|
        | 1    | 3    |
        | 2    | 4    |
    """
    return frame.to_markdown(index=False)


__all__ = [
    "load_json",
    "dump_json",
    "ensure_parent",
    "percent_change",
    "to_markdown_table",
]
