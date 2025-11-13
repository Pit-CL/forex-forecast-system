"""
Input validation and sanitization utilities.

This module provides functions to validate and sanitize user inputs
to prevent security vulnerabilities like path traversal, injection attacks,
and resource exhaustion.

Security Features:
- Path traversal prevention (blocks ../, absolute paths, etc.)
- Whitelist-based validation for constrained inputs
- Length limits to prevent DoS
- Type validation with proper error messages

Example:
    >>> from forex_core.utils.validators import validate_horizon, sanitize_path
    >>>
    >>> # Validate horizon parameter
    >>> horizon = validate_horizon("7d")  # OK
    >>> horizon = validate_horizon("../etc/passwd")  # Raises ValueError
    >>>
    >>> # Sanitize file paths
    >>> safe_path = sanitize_path("data/predictions.parquet", base_dir="data")
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


class ValidationError(ValueError):
    """Raised when input validation fails."""
    pass


def validate_horizon(horizon: str, allow_none: bool = False) -> Optional[str]:
    """
    Validate forecast horizon parameter.

    Only allows whitelisted horizon values to prevent path traversal attacks.

    Args:
        horizon: Horizon value to validate ("7d", "15d", "30d", "90d", or None).
        allow_none: Whether to allow None as a valid value.

    Returns:
        Validated horizon string, or None if allow_none=True and horizon is None.

    Raises:
        ValidationError: If horizon is invalid.

    Example:
        >>> validate_horizon("7d")
        '7d'
        >>> validate_horizon("../etc/passwd")
        ValidationError: Invalid horizon: ../etc/passwd

    Security:
        - Whitelist-only approach (not blacklist)
        - Prevents path traversal attacks
        - Prevents injection attacks
    """
    if horizon is None:
        if allow_none:
            return None
        raise ValidationError("Horizon cannot be None")

    # Whitelist of valid horizons
    VALID_HORIZONS = {"7d", "15d", "30d", "90d"}

    if horizon not in VALID_HORIZONS:
        raise ValidationError(
            f"Invalid horizon: {horizon}. "
            f"Must be one of: {', '.join(sorted(VALID_HORIZONS))}"
        )

    return horizon


def validate_severity(severity: str, allow_none: bool = False) -> Optional[str]:
    """
    Validate severity parameter for alert filtering.

    Args:
        severity: Severity value to validate.
        allow_none: Whether to allow None as a valid value.

    Returns:
        Validated severity string (lowercase), or None.

    Raises:
        ValidationError: If severity is invalid.

    Example:
        >>> validate_severity("HIGH")
        'high'
        >>> validate_severity("invalid")
        ValidationError: Invalid severity
    """
    if severity is None:
        if allow_none:
            return None
        raise ValidationError("Severity cannot be None")

    # Whitelist of valid severities
    VALID_SEVERITIES = {"low", "medium", "high", "critical"}

    severity_lower = severity.lower()

    if severity_lower not in VALID_SEVERITIES:
        raise ValidationError(
            f"Invalid severity: {severity}. "
            f"Must be one of: {', '.join(sorted(VALID_SEVERITIES))}"
        )

    return severity_lower


def validate_positive_integer(
    value: int,
    min_value: int = 1,
    max_value: Optional[int] = None,
    param_name: str = "value"
) -> int:
    """
    Validate that a value is a positive integer within bounds.

    Args:
        value: Integer to validate.
        min_value: Minimum allowed value (inclusive).
        max_value: Maximum allowed value (inclusive), or None for no limit.
        param_name: Parameter name for error messages.

    Returns:
        Validated integer.

    Raises:
        ValidationError: If value is invalid.

    Example:
        >>> validate_positive_integer(5, min_value=1, max_value=10)
        5
        >>> validate_positive_integer(100, min_value=1, max_value=50)
        ValidationError: days must be between 1 and 50
    """
    if not isinstance(value, int):
        raise ValidationError(f"{param_name} must be an integer, got {type(value).__name__}")

    if value < min_value:
        raise ValidationError(f"{param_name} must be >= {min_value}, got {value}")

    if max_value is not None and value > max_value:
        raise ValidationError(f"{param_name} must be <= {max_value}, got {value}")

    return value


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename to prevent path traversal and injection attacks.

    Removes or replaces dangerous characters:
    - Path separators (/, \)
    - Parent directory references (..)
    - Hidden file markers (leading .)
    - Control characters
    - Shell metacharacters

    Args:
        filename: Filename to sanitize.
        max_length: Maximum allowed filename length.

    Returns:
        Sanitized filename.

    Raises:
        ValidationError: If filename is invalid or dangerous.

    Example:
        >>> sanitize_filename("report.pdf")
        'report.pdf'
        >>> sanitize_filename("../../../etc/passwd")
        ValidationError: Filename contains path traversal
        >>> sanitize_filename("file;rm -rf /")  # doctest: +SKIP
        ValidationError: Filename contains dangerous characters

    Security:
        - Blocks path traversal (../)
        - Blocks absolute paths (/, \)
        - Blocks hidden files (.)
        - Blocks shell metacharacters
        - Enforces length limits
    """
    if not filename or not isinstance(filename, str):
        raise ValidationError("Filename must be a non-empty string")

    # Check length
    if len(filename) > max_length:
        raise ValidationError(f"Filename too long (max {max_length} characters)")

    # Block path traversal
    if ".." in filename:
        raise ValidationError("Filename contains path traversal pattern (..)")

    # Block path separators
    if "/" in filename or "\\" in filename:
        raise ValidationError("Filename contains path separators")

    # Block absolute paths
    if filename.startswith("/") or (len(filename) > 1 and filename[1] == ":"):
        raise ValidationError("Filename must be relative")

    # Block hidden files (starting with .)
    if filename.startswith("."):
        raise ValidationError("Hidden filenames not allowed")

    # Block shell metacharacters and control characters
    dangerous_chars = set(";|&$`<>()[]{}*?!\\'\"\n\r\t\x00")
    if any(c in dangerous_chars for c in filename):
        raise ValidationError("Filename contains dangerous characters")

    # Only allow alphanumeric, dash, underscore, and period
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
        raise ValidationError(
            "Filename must contain only alphanumeric characters, "
            "dashes, underscores, and periods"
        )

    return filename


def sanitize_path(
    path: str | Path,
    base_dir: str | Path,
    allow_create: bool = False
) -> Path:
    """
    Sanitize and validate a file path to prevent traversal attacks.

    Ensures the resolved path is within the base directory.

    Args:
        path: Path to sanitize (relative to base_dir).
        base_dir: Base directory that path must be within.
        allow_create: Whether to allow paths that don't exist yet.

    Returns:
        Resolved, validated Path object.

    Raises:
        ValidationError: If path is dangerous or outside base_dir.

    Example:
        >>> sanitize_path("data/predictions.parquet", base_dir="data")
        PosixPath('/abs/path/to/data/predictions.parquet')
        >>> sanitize_path("../etc/passwd", base_dir="data")
        ValidationError: Path escapes base directory

    Security:
        - Resolves symlinks
        - Checks path is within base_dir
        - Blocks path traversal attacks
        - Validates path exists (unless allow_create=True)
    """
    try:
        # Convert to Path objects
        path = Path(path)
        base_dir = Path(base_dir).resolve()

        # Resolve the full path (follows symlinks, resolves ..)
        # If path doesn't exist, resolve as much as possible
        try:
            resolved_path = path.resolve()
        except Exception:
            # If resolution fails, try relative resolution
            resolved_path = (base_dir / path).resolve()

        # Ensure path is within base_dir
        try:
            resolved_path.relative_to(base_dir)
        except ValueError:
            raise ValidationError(
                f"Path escapes base directory: {path} not in {base_dir}"
            )

        # Check existence if required
        if not allow_create and not resolved_path.exists():
            raise ValidationError(f"Path does not exist: {resolved_path}")

        return resolved_path

    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Invalid path: {e}")


__all__ = [
    "ValidationError",
    "validate_horizon",
    "validate_severity",
    "validate_positive_integer",
    "sanitize_filename",
    "sanitize_path",
]
