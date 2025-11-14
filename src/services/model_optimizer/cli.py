"""
CLI Interface for Model Optimizer.

Provides command-line interface for running optimization pipeline:
- run: Execute optimization
- rollback: Rollback to previous config
- status: Check optimization status
- history: Show optimization history

Example:
    $ python -m services.model_optimizer.cli run --horizon 7d
    $ python -m services.model_optimizer.cli run --all
    $ python -m services.model_optimizer.cli rollback --horizon 7d
    $ python -m services.model_optimizer.cli history --horizon 7d
"""

from pathlib import Path
from typing import Optional

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from forex_core.optimization.deployment import ConfigDeploymentManager

from .pipeline import ModelOptimizationPipeline, run_optimization_for_all_horizons

app = typer.Typer(
    name="model-optimizer",
    help="Automated model optimization pipeline",
)

console = Console()


@app.command()
def run(
    horizon: Optional[str] = typer.Option(
        None,
        "--horizon",
        "-h",
        help="Forecast horizon to optimize (7d, 15d, 30d, 90d)",
    ),
    all_horizons: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Optimize all horizons",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-d",
        help="Run validation without deployment",
    ),
    data_dir: Path = typer.Option(
        Path("data"),
        "--data-dir",
        help="Data directory",
    ),
    config_dir: Path = typer.Option(
        Path("configs"),
        "--config-dir",
        help="Config directory",
    ),
):
    """
    Run optimization pipeline.

    Examples:
        $ python -m services.model_optimizer.cli run --horizon 7d
        $ python -m services.model_optimizer.cli run --all
        $ python -m services.model_optimizer.cli run --all --dry-run
    """
    if not horizon and not all_horizons:
        console.print("[red]Error: Specify --horizon or --all[/red]")
        raise typer.Exit(1)

    if horizon and all_horizons:
        console.print("[red]Error: Cannot specify both --horizon and --all[/red]")
        raise typer.Exit(1)

    # Setup logging
    logger.add(
        "logs/model_optimizer.log",
        rotation="10 MB",
        retention="30 days",
        level="INFO",
    )

    if dry_run:
        console.print("[yellow]DRY RUN MODE - No deployment will occur[/yellow]\n")

    if all_horizons:
        console.print("[bold]Running optimization for all horizons[/bold]\n")
        results = run_optimization_for_all_horizons(
            data_dir=data_dir,
            config_dir=config_dir,
            dry_run=dry_run,
        )

        # Display summary table
        table = Table(title="Optimization Results")
        table.add_column("Horizon", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Deployed", style="yellow")
        table.add_column("Summary", style="white")

        for hz, result in results.items():
            status = "✅" if result.success else "❌"
            deployed = "✅" if result.deployed else "❌"
            table.add_row(hz, status, deployed, result.summary)

        console.print(table)

        # Exit code
        failed = sum(1 for r in results.values() if not r.success)
        if failed > 0:
            console.print(f"\n[red]{failed} horizons failed[/red]")
            raise typer.Exit(1)

    else:
        console.print(f"[bold]Running optimization for {horizon}[/bold]\n")

        pipeline = ModelOptimizationPipeline(
            horizon=horizon,
            data_dir=data_dir,
            config_dir=config_dir,
            dry_run=dry_run,
        )

        result = pipeline.run()

        # Display result
        if result.success:
            console.print(f"\n[green]✅ SUCCESS[/green]")
        else:
            console.print(f"\n[red]❌ FAILED[/red]")

        console.print(f"Summary: {result.summary}")

        if result.deployed:
            console.print(f"[green]Config deployed successfully![/green]")
        elif result.validated and not result.deployed:
            console.print(f"[yellow]Validation passed but deployment skipped (dry run)[/yellow]")
        elif not result.triggered:
            console.print(f"[blue]No optimization needed[/blue]")

        if not result.success:
            raise typer.Exit(1)


@app.command()
def rollback(
    horizon: str = typer.Argument(..., help="Horizon to rollback (7d, 15d, 30d, 90d)"),
    config_dir: Path = typer.Option(
        Path("configs"),
        "--config-dir",
        help="Config directory",
    ),
):
    """
    Rollback to previous configuration.

    Example:
        $ python -m services.model_optimizer.cli rollback 7d
    """
    console.print(f"[yellow]Rolling back {horizon} to previous config...[/yellow]")

    manager = ConfigDeploymentManager(config_dir=config_dir)

    success = manager.rollback(horizon)

    if success:
        console.print(f"[green]✅ Rollback successful for {horizon}[/green]")
    else:
        console.print(f"[red]❌ Rollback failed for {horizon}[/red]")
        raise typer.Exit(1)


@app.command()
def status(
    config_dir: Path = typer.Option(
        Path("configs"),
        "--config-dir",
        help="Config directory",
    ),
):
    """
    Show current configuration status.

    Example:
        $ python -m services.model_optimizer.cli status
    """
    console.print("[bold]Current Configuration Status[/bold]\n")

    manager = ConfigDeploymentManager(config_dir=config_dir)
    horizons = ["7d", "15d", "30d", "90d"]

    table = Table(title="Current Configs")
    table.add_column("Horizon", style="cyan")
    table.add_column("Context Length", style="green")
    table.add_column("Num Samples", style="yellow")
    table.add_column("Temperature", style="blue")
    table.add_column("RMSE", style="red")
    table.add_column("Last Updated", style="white")

    for horizon in horizons:
        config = manager.get_current_config(horizon)

        if config is None:
            table.add_row(
                horizon,
                "N/A",
                "N/A",
                "N/A",
                "N/A",
                "No config",
            )
        else:
            table.add_row(
                horizon,
                f"{config.context_length}d",
                str(config.num_samples),
                f"{config.temperature:.1f}",
                f"{config.validation_rmse:.2f}",
                config.timestamp.strftime("%Y-%m-%d %H:%M"),
            )

    console.print(table)


@app.command()
def history(
    horizon: Optional[str] = typer.Option(
        None,
        "--horizon",
        "-h",
        help="Filter by horizon",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Number of records to show",
    ),
    data_dir: Path = typer.Option(
        Path("data"),
        "--data-dir",
        help="Data directory",
    ),
):
    """
    Show optimization history.

    Example:
        $ python -m services.model_optimizer.cli history
        $ python -m services.model_optimizer.cli history --horizon 7d
        $ python -m services.model_optimizer.cli history --limit 20
    """
    import pandas as pd

    history_path = data_dir / "optimization_history" / "history.parquet"

    if not history_path.exists():
        console.print("[yellow]No optimization history found[/yellow]")
        return

    history = pd.read_parquet(history_path)

    if horizon:
        history = history[history["horizon"] == horizon]

    # Sort by date descending
    history = history.sort_values("optimization_date", ascending=False)

    # Limit
    history = history.head(limit)

    if len(history) == 0:
        console.print("[yellow]No history records found[/yellow]")
        return

    # Display table
    table = Table(title=f"Optimization History (last {limit})")
    table.add_column("Date", style="cyan")
    table.add_column("Horizon", style="green")
    table.add_column("Triggered By", style="yellow")
    table.add_column("Success", style="white")

    for _, row in history.iterrows():
        date_str = pd.to_datetime(row["optimization_date"]).strftime("%Y-%m-%d %H:%M")
        success = "✅" if row["success"] else "❌"

        table.add_row(
            date_str,
            row["horizon"],
            row["triggered_by"],
            success,
        )

    console.print(table)


if __name__ == "__main__":
    app()
