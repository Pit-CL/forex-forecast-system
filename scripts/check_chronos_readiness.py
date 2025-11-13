#!/usr/bin/env python3
"""
Check if system is ready to enable Chronos foundation model.

Usage:
    python scripts/check_chronos_readiness.py [--data-dir DATA_DIR]

Examples:
    # Check readiness using default data directory
    python scripts/check_chronos_readiness.py

    # Check specific data directory
    python scripts/check_chronos_readiness.py --data-dir /app/data

    # Run from Docker container
    docker exec usdclp-forecaster-7d python /app/scripts/check_chronos_readiness.py
"""

import sys
from pathlib import Path

import typer

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forex_core.mlops.readiness import (
    ChronosReadinessChecker,
    ReadinessLevel,
    generate_readiness_report_cli,
)

app = typer.Typer(help="Chronos Readiness Checker CLI")


@app.command()
def check(
    data_dir: Path = typer.Option(
        Path("data"),
        help="Path to data directory containing predictions",
    ),
    min_predictions: int = typer.Option(
        50,
        help="Minimum predictions needed per horizon",
    ),
    min_days: int = typer.Option(
        7,
        help="Minimum days system must be operating",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output results as JSON",
    ),
):
    """
    Check if system is ready to enable Chronos.

    Validates multiple criteria including:
    - Prediction tracking data availability
    - Drift detection functionality
    - System stability
    - Operation time
    - Performance baselines
    """
    if not data_dir.exists():
        typer.secho(
            f"Error: Data directory not found: {data_dir}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    if json_output:
        # JSON output for programmatic consumption
        checker = ChronosReadinessChecker(
            data_dir=data_dir,
            min_predictions=min_predictions,
            min_days_operating=min_days,
        )
        report = checker.assess()

        import json

        output = {
            "level": report.level.value,
            "score": report.score,
            "ready": report.level
            in [ReadinessLevel.READY, ReadinessLevel.OPTIMAL],
            "timestamp": report.timestamp.isoformat(),
            "checks": [
                {
                    "name": check.check_name,
                    "passed": check.passed,
                    "score": check.score,
                    "message": check.message,
                    "critical": check.critical,
                }
                for check in report.checks
            ],
            "recommendation": report.recommendation,
        }

        print(json.dumps(output, indent=2))

    else:
        # Human-readable output
        generate_readiness_report_cli(data_dir)

    # Exit with appropriate code
    checker = ChronosReadinessChecker(
        data_dir=data_dir,
        min_predictions=min_predictions,
        min_days_operating=min_days,
    )
    report = checker.assess()

    if report.level in [ReadinessLevel.READY, ReadinessLevel.OPTIMAL]:
        raise typer.Exit(code=0)  # Success
    elif report.level == ReadinessLevel.CAUTIOUS:
        raise typer.Exit(code=2)  # Warning
    else:
        raise typer.Exit(code=1)  # Not ready


@app.command()
def auto_enable(
    data_dir: Path = typer.Option(
        Path("data"),
        help="Path to data directory",
    ),
    config_file: Path = typer.Option(
        Path(".env"),
        help="Path to .env config file to update",
    ),
    dry_run: bool = typer.Option(
        False,
        help="Show what would be changed without modifying files",
    ),
):
    """
    Automatically enable Chronos if system is ready.

    Checks readiness and updates configuration if READY or OPTIMAL.
    Useful for automated deployment pipelines.

    Returns:
        Exit code 0 if enabled, 1 if not ready, 2 if dry run.
    """
    checker = ChronosReadinessChecker(data_dir=data_dir)
    report = checker.assess()

    # Display report
    generate_readiness_report_cli(data_dir)

    if report.level not in [ReadinessLevel.READY, ReadinessLevel.OPTIMAL]:
        typer.secho(
            "\n❌ System not ready - Chronos NOT enabled",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    # System is ready
    if dry_run:
        typer.secho(
            "\n✓ System is ready! (DRY RUN - no changes made)",
            fg=typer.colors.GREEN,
        )
        typer.echo(
            f"\nWould update {config_file} to set ENABLE_CHRONOS=true"
        )
        raise typer.Exit(code=2)

    # Update config
    try:
        if not config_file.exists():
            typer.secho(
                f"\n⚠ Config file not found: {config_file}",
                fg=typer.colors.YELLOW,
            )
            typer.echo("Create .env file manually with ENABLE_CHRONOS=true")
            raise typer.Exit(code=1)

        # Read current config
        lines = config_file.read_text().splitlines()

        # Update or add ENABLE_CHRONOS
        updated = False
        new_lines = []
        for line in lines:
            if line.startswith("ENABLE_CHRONOS="):
                new_lines.append("ENABLE_CHRONOS=true")
                updated = True
            else:
                new_lines.append(line)

        if not updated:
            # Add new line
            new_lines.append("ENABLE_CHRONOS=true")

        # Write back
        config_file.write_text("\n".join(new_lines) + "\n")

        typer.secho(
            f"\n✅ Chronos enabled! Updated {config_file}",
            fg=typer.colors.GREEN,
        )
        typer.echo("\n⚠ Restart services for changes to take effect:")
        typer.echo("   docker compose restart forecaster-7d")

        raise typer.Exit(code=0)

    except Exception as e:
        typer.secho(
            f"\n❌ Error updating config: {e}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
