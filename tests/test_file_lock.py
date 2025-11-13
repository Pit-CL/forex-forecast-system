"""
Test file locking for concurrent Parquet writes.

This test simulates multiple processes/threads writing to the same
Parquet file concurrently and verifies data integrity.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from forex_core.utils.file_lock import ParquetFileLock


def concurrent_writer(writer_id: int, parquet_path: Path, iterations: int) -> int:
    """
    Simulate concurrent writes to parquet file.

    Args:
        writer_id: ID of this writer (for data uniqueness).
        parquet_path: Path to shared parquet file.
        iterations: Number of writes to perform.

    Returns:
        Number of successful writes.
    """
    success_count = 0

    for i in range(iterations):
        try:
            # Simulate some work before write
            time.sleep(0.001)

            with ParquetFileLock(parquet_path, timeout=10.0):
                # Read existing data
                if parquet_path.exists():
                    df = pd.read_parquet(parquet_path)
                else:
                    df = pd.DataFrame(columns=["writer_id", "iteration", "value"])

                # Append new record
                new_record = pd.DataFrame([{
                    "writer_id": writer_id,
                    "iteration": i,
                    "value": writer_id * 1000 + i,
                }])

                df = pd.concat([df, new_record], ignore_index=True)

                # Write back
                df.to_parquet(parquet_path, index=False)

                success_count += 1

        except Exception as e:
            print(f"Writer {writer_id}, iteration {i} failed: {e}")

    return success_count


def test_concurrent_writes():
    """Test that concurrent writes don't corrupt data."""
    # Create temp file
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        parquet_path = Path(tmp.name)

    try:
        # Configuration
        n_writers = 5
        iterations_per_writer = 10
        expected_records = n_writers * iterations_per_writer

        print(f"\nTesting concurrent writes:")
        print(f"  Writers: {n_writers}")
        print(f"  Iterations per writer: {iterations_per_writer}")
        print(f"  Expected total records: {expected_records}\n")

        # Run concurrent writers
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=n_writers) as executor:
            futures = [
                executor.submit(concurrent_writer, writer_id, parquet_path, iterations_per_writer)
                for writer_id in range(n_writers)
            ]

            # Wait for completion
            total_success = 0
            for future in as_completed(futures):
                total_success += future.result()

        elapsed = time.time() - start_time

        # Verify results
        df = pd.read_parquet(parquet_path)
        actual_records = len(df)

        print(f"\nResults:")
        print(f"  Elapsed time: {elapsed:.2f}s")
        print(f"  Successful writes: {total_success}/{expected_records}")
        print(f"  Records in file: {actual_records}/{expected_records}")

        # Check for duplicates
        duplicates = df.duplicated(subset=["writer_id", "iteration"]).sum()
        print(f"  Duplicate records: {duplicates}")

        # Check for missing records
        missing = expected_records - actual_records
        print(f"  Missing records: {missing}")

        # Verification
        if actual_records == expected_records and duplicates == 0:
            print("\n✅ TEST PASSED - File locking working correctly!")
            return True
        else:
            print("\n❌ TEST FAILED - Data corruption detected!")
            print(f"Expected {expected_records} unique records, got {actual_records} with {duplicates} duplicates")
            return False

    finally:
        # Cleanup
        if parquet_path.exists():
            parquet_path.unlink()
        lock_file = Path(f"{parquet_path}.lock")
        if lock_file.exists():
            lock_file.unlink()


if __name__ == "__main__":
    success = test_concurrent_writes()
    sys.exit(0 if success else 1)
