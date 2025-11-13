"""
File locking utilities for safe concurrent file access.

This module provides context managers for file locking to prevent
data corruption when multiple processes/threads write to the same file.

Uses portalocker for cross-platform file locking (fcntl on Unix, msvcrt on Windows).

Example:
    >>> from forex_core.utils.file_lock import ParquetFileLock
    >>> import pandas as pd
    >>>
    >>> # Safe concurrent write to parquet
    >>> with ParquetFileLock("data/predictions.parquet") as lock:
    ...     # Read existing data
    ...     df_old = pd.read_parquet("data/predictions.parquet")
    ...     # Append new data
    ...     df_new = pd.concat([df_old, new_records])
    ...     # Write back
    ...     df_new.to_parquet("data/predictions.parquet", index=False)
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from loguru import logger

try:
    import portalocker
    PORTALOCKER_AVAILABLE = True
except ImportError:
    PORTALOCKER_AVAILABLE = False
    logger.warning(
        "portalocker not installed. File locking disabled. "
        "Install with: pip install portalocker"
    )


class FileLock:
    """
    Context manager for file locking.

    Uses portalocker for cross-platform file locking. Falls back to
    threading.Lock if portalocker is not available (less safe for
    multi-process scenarios).

    Attributes:
        lock_path: Path to the lock file.
        timeout: Maximum time to wait for lock (seconds).
        retry_interval: Time between retry attempts (seconds).

    Example:
        >>> with FileLock("/tmp/data.lock", timeout=10.0) as lock:
        ...     # Critical section - exclusive access guaranteed
        ...     with open("data.txt", "a") as f:
        ...         f.write("new data\n")
    """

    def __init__(
        self,
        lock_path: Path | str,
        timeout: float = 30.0,
        retry_interval: float = 0.1,
    ):
        """
        Initialize file lock.

        Args:
            lock_path: Path to lock file (typically <data_file>.lock).
            timeout: Maximum seconds to wait for lock.
            retry_interval: Seconds between retry attempts.
        """
        self.lock_path = Path(lock_path)
        self.timeout = timeout
        self.retry_interval = retry_interval
        self._lock_file: Optional = None

    def __enter__(self):
        """Acquire the lock."""
        if not PORTALOCKER_AVAILABLE:
            # Fallback: use threading lock (not safe for multi-process)
            import threading
            self._fallback_lock = threading.Lock()
            self._fallback_lock.acquire()
            logger.warning(
                f"Using threading.Lock (not multi-process safe) for {self.lock_path}"
            )
            return self

        # Ensure lock file directory exists
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)

        start_time = time.time()

        while True:
            try:
                # Try to acquire exclusive lock
                self._lock_file = open(self.lock_path, "w")
                portalocker.lock(
                    self._lock_file,
                    portalocker.LOCK_EX | portalocker.LOCK_NB  # Non-blocking
                )
                logger.debug(f"Acquired lock: {self.lock_path}")
                return self

            except (portalocker.LockException, BlockingIOError):
                # Lock held by another process
                elapsed = time.time() - start_time

                if elapsed >= self.timeout:
                    if self._lock_file:
                        self._lock_file.close()
                    raise TimeoutError(
                        f"Failed to acquire lock on {self.lock_path} "
                        f"after {self.timeout}s"
                    )

                # Wait and retry
                time.sleep(self.retry_interval)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release the lock."""
        if not PORTALOCKER_AVAILABLE:
            self._fallback_lock.release()
            return False

        if self._lock_file:
            try:
                portalocker.unlock(self._lock_file)
                self._lock_file.close()
                logger.debug(f"Released lock: {self.lock_path}")
            except Exception as e:
                logger.error(f"Failed to release lock {self.lock_path}: {e}")

            # Optionally remove lock file
            try:
                if self.lock_path.exists():
                    self.lock_path.unlink()
            except Exception:
                pass  # Ignore cleanup errors

        return False  # Don't suppress exceptions


@contextmanager
def ParquetFileLock(
    parquet_path: Path | str,
    timeout: float = 30.0
) -> Generator[FileLock, None, None]:
    """
    Context manager for locking parquet file writes.

    Creates a lock file at <parquet_path>.lock and ensures exclusive access.

    Args:
        parquet_path: Path to parquet file.
        timeout: Maximum seconds to wait for lock.

    Yields:
        FileLock instance.

    Example:
        >>> import pandas as pd
        >>> from forex_core.utils.file_lock import ParquetFileLock
        >>>
        >>> # Safe concurrent append to parquet
        >>> with ParquetFileLock("data/predictions.parquet"):
        ...     df = pd.read_parquet("data/predictions.parquet")
        ...     new_row = pd.DataFrame([{...}])
        ...     df = pd.concat([df, new_row])
        ...     df.to_parquet("data/predictions.parquet", index=False)

    Notes:
        - Lock file is automatically created/removed
        - Timeout raises TimeoutError if lock cannot be acquired
        - Works across processes (not just threads)
        - Cross-platform (Unix fcntl, Windows msvcrt)

    Raises:
        TimeoutError: If lock cannot be acquired within timeout.
    """
    lock_path = Path(f"{parquet_path}.lock")

    with FileLock(lock_path, timeout=timeout) as lock:
        yield lock


__all__ = [
    "FileLock",
    "ParquetFileLock",
]
