#!/usr/bin/env python3
"""
MLflow Experiment Dashboard - CLI viewer for forecast experiments.

This script provides a simple terminal dashboard to view and compare
MLflow experiments across all forecast horizons.

Usage:
    python scripts/mlflow_dashboard.py
    python scripts/mlflow_dashboard.py --experiment forecaster_7d
    python scripts/mlflow_dashboard.py --limit 10
"""

import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import box

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forex_core.mlops.mlflow_config import is_mlflow_available

if not is_mlflow_available():
    print("ERROR: MLflow not installed. Install with: pip install mlflow>=2.16")
    sys.exit(1)

import mlflow
from forex_core.mlops import MLflowConfig

app = typer.Typer(help="MLflow experiment dashboard for forex forecasting")
console = Console()


@app.command()
def dashboard(
    experiment: Optional[str] = typer.Option(
        None,
        "--experiment",
        "-e",
        help="Show specific experiment only (e.g., 'forecaster_7d')",
    ),
    limit: int = typer.Option(
        5,
        "--limit",
        "-n",
        help="Number of recent runs to show per experiment",
    ),
) -> None:
    """
    Display dashboard of MLflow experiments.

    Shows recent runs with key metrics for each forecasting horizon.
    """
    config = MLflowConfig()
    mlflow.set_tracking_uri(config.tracking_uri)

    # Determine which experiments to show
    if experiment:
        experiments = [experiment]
    else:
        experiments = ["forecaster_7d", "forecaster_15d", "forecaster_30d", "forecaster_90d"]

    console.print("\n")
    console.rule("[bold cyan]MLFLOW EXPERIMENT DASHBOARD[/bold cyan]", style="cyan")
    console.print(f"\nTracking URI: {config.tracking_uri}", style="dim")
    console.print(f"Showing {limit} most recent runs per experiment\n")

    for exp_name in experiments:
        try:
            show_experiment_table(exp_name, limit)
        except Exception as e:
            console.print(f"\n[red]Error loading {exp_name}:[/red] {e}\n")

    console.print("")


def show_experiment_table(experiment_name: str, limit: int) -> None:
    """Display table of runs for a single experiment."""
    console.print(f"\n[bold]{experiment_name.upper()}[/bold]")

    # Get experiment
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        console.print(f"  [yellow]Experiment not found (no runs yet)[/yellow]")
        return

    # Search runs
    runs = mlflow.search_runs(
        experiment_ids=[experiment.experiment_id],
        order_by=["start_time DESC"],
        max_results=limit,
    )

    if runs.empty:
        console.print(f"  [yellow]No runs found[/yellow]")
        return

    # Create table
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Run ID", style="dim", width=10)
    table.add_column("Timestamp", style="blue", width=16)
    table.add_column("RMSE", justify="right", style="green")
    table.add_column("MAE", justify="right", style="green")
    table.add_column("MAPE", justify="right", style="green")
    table.add_column("Dir. Acc.", justify="right", style="yellow")
    table.add_column("Status", justify="center", width=10)

    # Extract horizon from experiment name (e.g., "forecaster_7d" -> "7d")
    horizon = experiment_name.split("_")[-1] if "_" in experiment_name else "7d"

    # Add rows
    for _, run in runs.iterrows():
        run_id_short = run["run_id"][:8] + "..."

        # Format timestamp
        timestamp = run["start_time"].strftime("%Y-%m-%d %H:%M")

        # Get metrics (handle missing values)
        rmse = run.get(f"metrics.{horizon}_rmse", float("nan"))
        mae = run.get(f"metrics.{horizon}_mae", float("nan"))
        mape = run.get(f"metrics.{horizon}_mape", float("nan"))
        dir_acc = run.get(f"metrics.{horizon}_directional_accuracy", float("nan"))

        # Format metrics
        rmse_str = f"{rmse:.4f}" if not pd.isna(rmse) else "N/A"
        mae_str = f"{mae:.4f}" if not pd.isna(mae) else "N/A"
        mape_str = f"{mape:.2f}%" if not pd.isna(mape) else "N/A"
        dir_acc_str = f"{dir_acc:.1%}" if not pd.isna(dir_acc) else "N/A"

        # Status
        status = run.get("status", "UNKNOWN")
        status_style = "green" if status == "FINISHED" else "red"
        status_str = f"[{status_style}]{status}[/{status_style}]"

        table.add_row(
            run_id_short,
            timestamp,
            rmse_str,
            mae_str,
            mape_str,
            dir_acc_str,
            status_str,
        )

    console.print(table)


@app.command()
def compare(
    metric: str = typer.Option(
        "rmse",
        "--metric",
        "-m",
        help="Metric to compare (rmse, mae, mape)",
    ),
) -> None:
    """
    Compare best performance across all horizons.

    Shows the best run for each forecast horizon based on specified metric.
    """
    config = MLflowConfig()
    mlflow.set_tracking_uri(config.tracking_uri)

    console.print("\n")
    console.rule(f"[bold cyan]BEST RUNS BY {metric.upper()}[/bold cyan]", style="cyan")
    console.print("")

    # Create comparison table
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Horizon", style="bold")
    table.add_column("Best RMSE", justify="right", style="green")
    table.add_column("MAE", justify="right", style="green")
    table.add_column("MAPE", justify="right", style="green")
    table.add_column("Run Date", style="blue")
    table.add_column("Run ID", style="dim")

    horizons = ["7d", "15d", "30d", "90d"]

    for horizon in horizons:
        exp_name = f"forecaster_{horizon}"

        try:
            best_run = MLflowConfig.get_best_run(
                experiment_name=exp_name,
                metric=f"{horizon}_{metric}",
                ascending=True  # Minimize error metrics
            )

            if best_run is None:
                table.add_row(
                    horizon,
                    "[dim]N/A[/dim]",
                    "[dim]N/A[/dim]",
                    "[dim]N/A[/dim]",
                    "[dim]No runs[/dim]",
                    "[dim]-[/dim]",
                )
                continue

            # Extract metrics
            metrics = best_run.data.metrics
            rmse = metrics.get(f"{horizon}_rmse", float("nan"))
            mae = metrics.get(f"{horizon}_mae", float("nan"))
            mape = metrics.get(f"{horizon}_mape", float("nan"))

            # Format
            rmse_str = f"{rmse:.4f}" if not pd.isna(rmse) else "N/A"
            mae_str = f"{mae:.4f}" if not pd.isna(mae) else "N/A"
            mape_str = f"{mape:.2f}%" if not pd.isna(mape) else "N/A"

            run_date = pd.to_datetime(best_run.info.start_time, unit='ms').strftime("%Y-%m-%d")
            run_id_short = best_run.info.run_id[:8] + "..."

            table.add_row(
                horizon,
                rmse_str,
                mae_str,
                mape_str,
                run_date,
                run_id_short,
            )

        except Exception as e:
            console.print(f"[red]Error loading {exp_name}:[/red] {e}")
            table.add_row(
                horizon,
                "[red]Error[/red]",
                "[red]Error[/red]",
                "[red]Error[/red]",
                "[red]Error[/red]",
                "[red]-[/red]",
            )

    console.print(table)
    console.print("")


@app.command()
def stats() -> None:
    """Show overall statistics for all experiments."""
    config = MLflowConfig()
    mlflow.set_tracking_uri(config.tracking_uri)

    console.print("\n")
    console.rule("[bold cyan]EXPERIMENT STATISTICS[/bold cyan]", style="cyan")
    console.print("")

    # Create stats table
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Experiment", style="bold")
    table.add_column("Total Runs", justify="right")
    table.add_column("Last Run", style="blue")
    table.add_column("Status", justify="center")

    experiments = ["forecaster_7d", "forecaster_15d", "forecaster_30d", "forecaster_90d"]

    for exp_name in experiments:
        try:
            experiment = mlflow.get_experiment_by_name(exp_name)

            if experiment is None:
                table.add_row(
                    exp_name,
                    "[dim]0[/dim]",
                    "[dim]Never[/dim]",
                    "[yellow]Not created[/yellow]",
                )
                continue

            # Count runs
            runs = mlflow.search_runs(
                experiment_ids=[experiment.experiment_id],
                order_by=["start_time DESC"],
                max_results=1,
            )

            total_runs = len(mlflow.search_runs(
                experiment_ids=[experiment.experiment_id],
            ))

            if runs.empty:
                table.add_row(
                    exp_name,
                    "0",
                    "[dim]Never[/dim]",
                    "[yellow]No runs[/yellow]",
                )
                continue

            last_run = runs.iloc[0]
            last_run_date = last_run["start_time"].strftime("%Y-%m-%d %H:%M")
            status = last_run.get("status", "UNKNOWN")
            status_style = "green" if status == "FINISHED" else "red"

            table.add_row(
                exp_name,
                str(total_runs),
                last_run_date,
                f"[{status_style}]{status}[/{status_style}]",
            )

        except Exception as e:
            console.print(f"[red]Error loading {exp_name}:[/red] {e}")
            table.add_row(
                exp_name,
                "[red]Error[/red]",
                "[red]Error[/red]",
                "[red]Error[/red]",
            )

    console.print(table)
    console.print(f"\nTracking URI: {config.tracking_uri}", style="dim")
    console.print("")


if __name__ == "__main__":
    # Import pandas here to avoid ImportError if not used
    import pandas as pd
    pd.options.mode.chained_assignment = None  # Suppress SettingWithCopyWarning

    app()
