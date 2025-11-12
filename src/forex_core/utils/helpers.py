"""
General utility helper functions.

This module provides common utility functions for:
- Mathematical calculations (percent_change, format_decimal)
- File operations (ensure_parent, load_json, dump_json)
- Data formatting (to_markdown_table, sanitize_filename)
- Time utilities (timestamp_now)
- Collection utilities (chunk, word_count)

All functions are pure/stateless where possible for easy testing.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd
from slugify import slugify  # type: ignore


def percent_change(new: float, old: float) -> float:
    """
    Calculate percentage change between two values.

    Args:
        new: The new value.
        old: The old (reference) value.

    Returns:
        Percentage change as a float. Returns 0.0 if old value is 0.

    Example:
        >>> percent_change(110, 100)
        10.0
        >>> percent_change(90, 100)
        -10.0
        >>> percent_change(100, 0)
        0.0
    """
    if old == 0:
        return 0.0
    return (new - old) / old * 100


def format_decimal(value: float, digits: int = 2) -> float:
    """
    Round a float to a specified number of decimal places.

    Args:
        value: The value to round.
        digits: Number of decimal places (default: 2).

    Returns:
        Rounded float value.

    Example:
        >>> format_decimal(3.14159, 2)
        3.14
        >>> format_decimal(3.14159, 4)
        3.1416
    """
    return round(value, digits)


def ensure_parent(path: Path) -> None:
    """
    Ensure that the parent directory of a file path exists.

    Creates all necessary parent directories if they don't exist.
    Safe to call multiple times (idempotent).

    Args:
        path: Path to a file (not directory). The parent will be created.

    Example:
        >>> ensure_parent(Path("./data/cache/results.json"))
        # Creates ./data/cache/ if it doesn't exist
    """
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Any:
    """
    Load JSON data from a file.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed JSON data, or None if file doesn't exist.

    Example:
        >>> data = load_json(Path("config.json"))
        >>> if data:
        ...     print(data["version"])
    """
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return None


def dump_json(path: Path, payload: Any) -> None:
    """
    Write data to a JSON file with pretty formatting.

    Creates parent directories if they don't exist.
    Uses ensure_ascii=False for proper UTF-8 encoding.

    Args:
        path: Destination file path.
        payload: Data to serialize (must be JSON-serializable).

    Example:
        >>> data = {"forecast": [900, 905, 910]}
        >>> dump_json(Path("./output/forecast.json"), data)
    """
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)


def to_markdown_table(frame: pd.DataFrame) -> str:
    """
    Convert a pandas DataFrame to a Markdown table.

    Args:
        frame: DataFrame to convert.

    Returns:
        Markdown-formatted table as a string.

    Example:
        >>> df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        >>> print(to_markdown_table(df))
        | A | B |
        |---|---|
        | 1 | 3 |
        | 2 | 4 |
    """
    return frame.to_markdown(index=False)


def timestamp_now(tz: str = "UTC") -> datetime:
    """
    Get the current timestamp with timezone awareness.

    Note: The tz parameter is accepted for backwards compatibility but currently
    not used. The function returns the current time in the system's timezone.

    Args:
        tz: Timezone name (currently unused, defaults to "UTC").

    Returns:
        Timezone-aware datetime object representing current time.

    Example:
        >>> now = timestamp_now()
        >>> print(now.isoformat())
        2025-11-12T14:30:00-04:00
    """
    return datetime.now().astimezone()


def sanitize_filename(value: str) -> str:
    """
    Convert a string to a safe filename.

    Converts to lowercase, replaces spaces with hyphens, removes special characters.

    Args:
        value: String to sanitize.

    Returns:
        Sanitized filename-safe string.

    Example:
        >>> sanitize_filename("USD/CLP Forecast 2025!")
        'usd-clp-forecast-2025'
        >>> sanitize_filename("Report (Final).pdf")
        'report-final-pdf'
    """
    return slugify(value, lowercase=True, separator="-")


def word_count(text: str) -> int:
    """
    Count words in a text string.

    Words are defined as whitespace-separated tokens.

    Args:
        text: Text to count words in.

    Returns:
        Number of words.

    Example:
        >>> word_count("The quick brown fox")
        4
        >>> word_count("   Extra   spaces   ")
        2
    """
    return len(text.split())


def chunk(iterable: Sequence[Any], size: int) -> Iterable[Sequence[Any]]:
    """
    Split a sequence into chunks of specified size.

    Args:
        iterable: Sequence to split (list, tuple, string, etc.).
        size: Maximum size of each chunk.

    Yields:
        Chunks of the original sequence.

    Example:
        >>> list(chunk([1, 2, 3, 4, 5], 2))
        [[1, 2], [3, 4], [5]]
        >>> list(chunk("ABCDEFG", 3))
        ['ABC', 'DEF', 'G']
    """
    for idx in range(0, len(iterable), size):
        yield iterable[idx : idx + size]


__all__ = [
    "percent_change",
    "format_decimal",
    "ensure_parent",
    "load_json",
    "dump_json",
    "to_markdown_table",
    "timestamp_now",
    "sanitize_filename",
    "word_count",
    "chunk",
]
