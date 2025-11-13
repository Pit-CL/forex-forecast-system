#!/usr/bin/env python3
"""
Walk-Forward Validation CLI Tool.

Ejecuta validación walk-forward para evaluar performance de modelos
de forecasting en condiciones realistas.

Usage:
    python scripts/validate_model.py --horizon 7 --mode expanding --folds 5
    python scripts/validate_model.py --horizon 15 --mode rolling --folds 3
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timedelta

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from forex_core.data.loader import DataLoader
from forex_core.mlops.validation import ValidationMode, WalkForwardValidator

app = typer.Typer(help="Walk-Forward Validation Tool")
console = Console()


def create_simple_forecaster(horizon_days: int):
    """
    Create a simple forecaster function for validation.

    NOTE: In production, this should use the actual forecaster pipeline.
    For now, we'll use a simple naive forecast (last value + small drift).
    """

    def forecaster_func(bundle, horizon):
        """Simple naive forecaster for testing."""
        from forex_core.data.models import ForecastPackage, ForecastPoint

        import numpy as np

        # Get last value
        last_value = bundle.usdclp_series.iloc[-1]

        # Simple drift based on recent trend
        recent_values = bundle.usdclp_series.tail(30).values
        drift = (recent_values[-1] - recent_values[0]) / len(recent_values)

        # Generate naive forecast
        forecast_points = []
        for i in range(horizon):
            mean = last_value + drift * (i + 1)
            std_dev = mean * 0.01  # Assume 1% std dev
            ci80_width = std_dev * 1.28  # 80% CI (±1.28σ)
            ci95_width = std_dev * 1.96  # 95% CI (±1.96σ)

            point = ForecastPoint(
                date=datetime.now() + timedelta(days=i + 1),
                mean=mean,
                ci80_low=mean - ci80_width,
                ci80_high=mean + ci80_width,
                ci95_low=mean - ci95_width,
                ci95_high=mean + ci95_width,
                std_dev=std_dev,
            )
            forecast_points.append(point)

        return ForecastPackage(
            series=forecast_points,
            methodology="Naive drift forecaster (recent 30-day trend)",
            error_metrics={"rmse": 0.0, "mae": 0.0, "mape": 0.0},  # Placeholder
            residual_vol=last_value * 0.01,  # Assume 1% volatility
        )

    return forecaster_func


@app.command()
def validate(
    horizon: int = typer.Option(7, "--horizon", "-h", help="Forecast horizon in days"),
    mode: str = typer.Option(
        "expanding",
        "--mode",
        "-m",
        help="Validation mode: expanding or rolling",
    ),
    folds: int = typer.Option(
        5, "--folds", "-f", help="Maximum number of folds to execute"
    ),
    initial_train: int = typer.Option(
        365, "--initial-train", help="Initial training window in days"
    ),
    test_days: int = typer.Option(30, "--test-days", help="Test window size in days"),
    step_days: int = typer.Option(
        30, "--step-days", help="Step size between folds in days"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
):
    """
    Run walk-forward validation for a forecasting model.

    Example:
        python scripts/validate_model.py --horizon 7 --mode expanding --folds 5
    """
    console.print("\n[bold cyan]Walk-Forward Validation[/bold cyan]")
    console.print(f"Horizon: {horizon} days")
    console.print(f"Mode: {mode}")
    console.print(f"Max folds: {folds}")
    console.print(f"Initial training: {initial_train} days")
    console.print(f"Test window: {test_days} days")
    console.print(f"Step size: {step_days} days\n")

    # Configure logging
    if not verbose:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    # Load data
    console.print("[yellow]Loading historical data...[/yellow]")
    try:
        data_loader = DataLoader()

        # Try to load from warehouse first (faster)
        warehouse_path = Path("data/warehouse/usdclp_daily.parquet")
        if warehouse_path.exists():
            import pandas as pd

            df = pd.read_parquet(warehouse_path)
            series = df["value"]
            console.print(f"✓ Loaded {len(series)} observations from warehouse")
        else:
            # Load fresh data
            bundle = data_loader.load()
            series = bundle.usdclp_series
            console.print(f"✓ Loaded {len(series)} observations")

    except Exception as e:
        console.print(f"[red]✗ Failed to load data: {e}[/red]")
        raise typer.Exit(1)

    # Validate mode
    try:
        validation_mode = ValidationMode(mode)
    except ValueError:
        console.print(f"[red]✗ Invalid mode: {mode}[/red]")
        console.print("Valid modes: expanding, rolling")
        raise typer.Exit(1)

    # Create forecaster
    console.print("\n[yellow]Initializing forecaster...[/yellow]")
    forecaster = create_simple_forecaster(horizon)
    console.print("✓ Forecaster ready (using naive drift model)")

    # Initialize validator
    console.print("\n[yellow]Initializing validator...[/yellow]")
    validator = WalkForwardValidator(
        forecaster_func=forecaster,
        horizon_days=horizon,
        initial_train_days=initial_train,
        test_days=test_days,
        step_days=step_days,
        mode=validation_mode,
    )
    console.print("✓ Validator initialized")

    # Run validation
    console.print("\n[bold yellow]Running validation...[/bold yellow]")
    console.print("This may take a few minutes...\n")

    try:
        report = validator.validate(series, max_folds=folds)
    except Exception as e:
        console.print(f"[red]✗ Validation failed: {e}[/red]")
        import traceback

        traceback.print_exc()
        raise typer.Exit(1)

    # Display results
    console.print("\n[bold green]Validation Complete![/bold green]\n")

    # Summary table
    summary_table = Table(title="Validation Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Horizon", f"{horizon} days")
    summary_table.add_row("Mode", mode)
    summary_table.add_row("Folds Executed", str(report.n_folds))
    summary_table.add_row("Duration", f"{report.total_duration_seconds:.1f}s")
    summary_table.add_row("Avg RMSE", f"{report.avg_rmse:.2f}")
    summary_table.add_row("Avg MAE", f"{report.avg_mae:.2f}")
    summary_table.add_row("Avg MAPE", f"{report.avg_mape:.2f}%")
    summary_table.add_row("Avg CI95 Coverage", f"{report.avg_ci95_coverage:.1%}")
    summary_table.add_row("Avg Bias", f"{report.avg_bias:+.2f}")
    summary_table.add_row("Std RMSE", f"{report.std_rmse:.2f}")
    summary_table.add_row("Best Fold", f"#{report.best_fold}")
    summary_table.add_row("Worst Fold", f"#{report.worst_fold}")

    acceptable = report.is_acceptable()
    status = "[green]✓ ACCEPTABLE[/green]" if acceptable else "[red]✗ NEEDS IMPROVEMENT[/red]"
    summary_table.add_row("Status", status)

    console.print(summary_table)

    # Fold-level results
    console.print("\n")
    fold_table = Table(title="Per-Fold Results")
    fold_table.add_column("Fold", style="cyan")
    fold_table.add_column("Train Period", style="dim")
    fold_table.add_column("Test Period", style="dim")
    fold_table.add_column("RMSE", style="yellow")
    fold_table.add_column("MAE", style="yellow")
    fold_table.add_column("MAPE", style="yellow")
    fold_table.add_column("CI95", style="green")

    for metrics in report.fold_metrics:
        fold_table.add_row(
            str(metrics.fold),
            f"{metrics.train_start.date()} to {metrics.train_end.date()}",
            f"{metrics.test_start.date()} to {metrics.test_end.date()}",
            f"{metrics.rmse:.2f}",
            f"{metrics.mae:.2f}",
            f"{metrics.mape:.2f}%",
            f"{metrics.ci95_coverage:.1%}",
        )

    console.print(fold_table)

    # Save report
    console.print("\n[yellow]Saving validation report...[/yellow]")
    try:
        filepath = validator.save_report(report)
        console.print(f"✓ Report saved to: {filepath}")
    except Exception as e:
        console.print(f"[red]✗ Failed to save report: {e}[/red]")

    console.print("\n[bold green]Done![/bold green]\n")


@app.command()
def list_reports(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of reports to show"),
):
    """List recent validation reports."""
    console.print("\n[bold cyan]Recent Validation Reports[/bold cyan]\n")

    reports_dir = Path("data/validation_reports")

    if not reports_dir.exists():
        console.print("[yellow]No validation reports found[/yellow]")
        return

    # Find all report files
    summary_files = sorted(
        reports_dir.glob("summary_*.parquet"), key=lambda p: p.stat().st_mtime, reverse=True
    )

    if not summary_files:
        console.print("[yellow]No validation reports found[/yellow]")
        return

    # Display table
    table = Table()
    table.add_column("Date", style="cyan")
    table.add_column("Horizon", style="green")
    table.add_column("Mode", style="blue")
    table.add_column("Folds", style="yellow")
    table.add_column("RMSE", style="yellow")
    table.add_column("MAPE", style="yellow")
    table.add_column("Status", style="green")

    import pandas as pd

    for filepath in summary_files[:limit]:
        try:
            df = pd.read_parquet(filepath)
            row = df.iloc[0]

            timestamp = pd.to_datetime(row["timestamp"]).strftime("%Y-%m-%d %H:%M")
            acceptable = row.get("is_acceptable", False)
            status = "✓" if acceptable else "✗"

            table.add_row(
                timestamp,
                row["horizon"],
                row["mode"],
                str(row["n_folds"]),
                f"{row['avg_rmse']:.2f}",
                f"{row['avg_mape']:.2f}%",
                status,
            )
        except Exception as e:
            logger.warning(f"Failed to read {filepath}: {e}")

    console.print(table)
    console.print()


if __name__ == "__main__":
    app()
