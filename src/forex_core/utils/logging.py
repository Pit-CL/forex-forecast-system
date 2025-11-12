"""
Logging utilities using loguru.

This module provides a centralized logging configuration for the forex_core library.
It uses loguru for structured logging with customizable sinks and formats.

Example:
    >>> from forex_core.utils import configure_logging, logger
    >>> configure_logging(log_path=Path("./logs/app.log"), level="DEBUG")
    >>> logger.info("Application started")
    >>> logger.error("An error occurred", error_code="E001")
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from loguru import logger


def get_logger(name: str = None):
    """
    Get a logger instance.

    Args:
        name: Logger name (currently unused, provided for compatibility)

    Returns:
        loguru logger instance
    """
    return logger


def configure_logging(
    log_path: Optional[Path] = None,
    level: str = "INFO",
    format_string: Optional[str] = None,
    rotation: str = "5 MB",
    retention: int = 7,
    backtrace: bool = False,
    diagnose: bool = False,
) -> None:
    """
    Configure loguru logging sinks with console and optional file output.

    This function sets up structured logging with colored console output and optional
    file rotation. It removes any existing handlers before adding new ones.

    Args:
        log_path: Path to the log file. If None, only console logging is enabled.
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        format_string: Custom format string. If None, uses default format.
        rotation: File rotation strategy (e.g., "5 MB", "1 day", "00:00").
        retention: Number of rotated files to keep (days for time-based rotation).
        backtrace: Whether to display full exception traceback.
        diagnose: Whether to display variables in exception traceback.

    Example:
        >>> configure_logging(
        ...     log_path=Path("./logs/forecaster.log"),
        ...     level="DEBUG",
        ...     rotation="10 MB",
        ...     retention=14
        ... )
    """
    # Remove any existing handlers
    logger.remove()

    # Default format with colors and metadata
    if format_string is None:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )

    # Add console sink
    logger.add(
        sys.stderr,
        level=level.upper(),
        format=format_string,
        backtrace=backtrace,
        diagnose=diagnose,
    )

    # Add file sink if path provided
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_path,
            rotation=rotation,
            retention=retention,
            level=level.upper(),
            enqueue=True,  # Async writing for better performance
            backtrace=backtrace,
            diagnose=diagnose,
        )
        logger.debug(f"File logging enabled: {log_path}")


__all__ = ["configure_logging", "logger"]
