"""
Command-line interface for 90-day forecaster service.

This module provides a CLI using Typer for running forecasts,
validation, and backtesting operations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from forex_core.config import get_settings
from forex_core.data import DataLoader
from forex_core.utils.logging import logger, configure_logging

from .config import get_service_config
from .pipeline import run_forecast_pipeline, validate_forecast

app = typer.Typer(
    name="forecaster-90d",
    help="90-day USD/CLP forex forecasting service",
    add_completion=False,
)
console = Console()


@app.command()
def run(
    skip_email: bool = typer.Option(
        False,
        "--skip-email",
        help="Skip email delivery of the report",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Custom output directory for reports",
        exists=False,
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        "-l",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    ),
    log_file: Optional[Path] = typer.Option(
        None,
        "--log-file",
        help="Path to log file (default: logs/forecaster_90d.log)",
    ),
) -> None:
    """
    Run the 90-day forecast pipeline.

    This command executes the complete forecasting workflow:
    - Load data from multiple sources
    - Generate 90-day ensemble forecast
    - Create visualization charts
    - Build PDF report
    - Send email notification (optional)

    Examples:
        # Run full pipeline with email
        $ python -m services.forecaster_90d.cli run

        # Run without email
        $ python -m services.forecaster_90d.cli run --skip-email

        # Custom output directory and debug logging
        $ python -m services.forecaster_90d.cli run -o ./my_reports -l DEBUG
    """
    # Configure logging
    if log_file is None:
        log_file = Path("./logs/forecaster_90d.log")

    configure_logging(log_path=log_file, level=log_level)

    console.print("\n[bold cyan]7-Day Forex Forecaster[/bold cyan]")
    console.print("=" * 60)

    try:
        # Run pipeline
        with console.status("[yellow]Running forecast pipeline...[/yellow]"):
            report_path = run_forecast_pipeline(
                skip_email=skip_email,
                output_dir=output_dir,
            )

        # Success message
        console.print(f"\n[bold green]✓ Forecast completed successfully![/bold green]")
        console.print(f"[green]Report saved to:[/green] {report_path}")

        if skip_email:
            console.print("[yellow]Email delivery was skipped[/yellow]")

    except Exception as e:
        console.print(f"\n[bold red]✗ Pipeline failed:[/bold red] {e}")
        logger.exception("Pipeline execution failed")
        raise typer.Exit(code=1)


@app.command()
def validate(
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        "-l",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    ),
) -> None:
    """
    Validate forecast generation without creating reports.

    This command runs the forecasting models and validates outputs
    without generating charts, reports, or sending emails. Useful
    for testing and debugging.

    Examples:
        $ python -m services.forecaster_90d.cli validate
        $ python -m services.forecaster_90d.cli validate -l DEBUG
    """
    configure_logging(level=log_level)

    console.print("\n[bold cyan]Validating 7-Day Forecast[/bold cyan]")
    console.print("=" * 60)

    try:
        # Load data
        with console.status("[yellow]Loading data...[/yellow]"):
            settings = get_settings()
            service_config = get_service_config()
            loader = DataLoader(settings)
            bundle = loader.load()

        console.print(
            f"[green]✓ Data loaded:[/green] {len(bundle.indicators)} indicators, "
            f"{len(bundle.sources)} sources"
        )

        # Generate forecast
        with console.status("[yellow]Generating forecast...[/yellow]"):
            from forex_core.forecasting import ForecastEngine

            engine = ForecastEngine(
                config=settings,
                horizon=service_config.horizon,
                steps=service_config.steps,
            )
            forecast, artifacts = engine.forecast(bundle)

        console.print(
            f"[green]✓ Forecast generated:[/green] {len(forecast.series)} points"
        )

        # Validate forecast
        with console.status("[yellow]Validating forecast...[/yellow]"):
            is_valid = validate_forecast(bundle, forecast)

        if is_valid:
            console.print("[bold green]✓ Validation passed![/bold green]")

            # Display forecast summary
            table = Table(title="7-Day Forecast Summary")
            table.add_column("Day", style="cyan")
            table.add_column("Date", style="blue")
            table.add_column("Mean", justify="right", style="green")
            table.add_column("Lower", justify="right", style="yellow")
            table.add_column("Upper", justify="right", style="yellow")

            for i, point in enumerate(forecast.series, 1):
                table.add_row(
                    f"Day {i}",
                    point.date.strftime("%Y-%m-%d"),
                    f"{point.mean:.2f}",
                    f"{point.ci95_low:.2f}",
                    f"{point.ci95_high:.2f}",
                )

            console.print(table)

            # Display model artifacts
            console.print(f"\n[bold]Model Metrics:[/bold]")
            for model_name, result in artifacts.models.items():
                console.print(
                    f"  {model_name}: RMSE={result.rmse:.4f}, "
                    f"MAPE={result.mape:.4f}, Weight={result.weight:.4f}"
                )

        else:
            console.print("[bold red]✗ Validation failed![/bold red]")
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(f"\n[bold red]✗ Validation failed:[/bold red] {e}")
        logger.exception("Validation failed")
        raise typer.Exit(code=1)


@app.command()
def backtest(
    days: int = typer.Option(
        30,
        "--days",
        "-d",
        help="Number of days to backtest",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Directory to save backtest results",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        "-l",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    ),
) -> None:
    """
    Run backtest to evaluate forecast accuracy.

    This command evaluates historical forecast performance by
    comparing predictions against actual values.

    NOTE: Backtesting functionality is not yet implemented.

    Examples:
        $ python -m services.forecaster_90d.cli backtest --days 30
        $ python -m services.forecaster_90d.cli backtest -d 60 -o ./backtest_results
    """
    configure_logging(level=log_level)

    console.print("\n[bold cyan]Backtesting 7-Day Forecasts[/bold cyan]")
    console.print("=" * 60)
    console.print(f"[yellow]Days to backtest:[/yellow] {days}")

    # TODO: Implement backtesting logic
    console.print(
        "\n[bold yellow]⚠ Backtesting not yet implemented[/bold yellow]\n"
        "This feature will be available in a future release."
    )

    raise typer.Exit(code=0)


@app.command()
def info() -> None:
    """
    Display service configuration and environment info.

    Shows current configuration, paths, API keys status, and model settings.
    """
    settings = get_settings()
    service_config = get_service_config()

    console.print("\n[bold cyan]Forecaster 90D - Configuration[/bold cyan]")
    console.print("=" * 60)

    # Service configuration
    table = Table(title="Service Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Horizon", service_config.horizon)
    table.add_row("Projection Days", str(service_config.projection_days))
    table.add_row("Frequency", service_config.frequency)
    table.add_row("Historical Lookback", f"{service_config.historical_lookback_days} days")
    table.add_row("Report Title", service_config.report_title)

    console.print(table)

    # Environment settings
    env_table = Table(title="Environment Settings")
    env_table.add_column("Setting", style="cyan")
    env_table.add_column("Value", style="green")

    env_table.add_row("Environment", settings.environment)
    env_table.add_row("Timezone", settings.report_timezone)
    env_table.add_row("Output Directory", str(settings.output_dir))
    env_table.add_row("Data Directory", str(settings.data_dir))
    env_table.add_row("Chart Directory", str(settings.chart_dir))

    console.print(env_table)

    # API Keys status
    api_table = Table(title="API Keys Status")
    api_table.add_column("API", style="cyan")
    api_table.add_column("Status", style="green")

    api_table.add_row(
        "FRED API",
        "[green]✓ Configured[/green]" if settings.fred_api_key else "[red]✗ Missing[/red]",
    )
    api_table.add_row(
        "NewsAPI",
        "[green]✓ Configured[/green]" if settings.news_api_key else "[red]✗ Missing[/red]",
    )
    api_table.add_row(
        "Alpha Vantage",
        "[green]✓ Configured[/green]"
        if settings.alphavantage_api_key
        else "[red]✗ Missing[/red]",
    )
    api_table.add_row(
        "Gmail",
        "[green]✓ Configured[/green]"
        if settings.gmail_user and settings.gmail_app_password
        else "[red]✗ Missing[/red]",
    )

    console.print(api_table)

    # Model configuration
    model_table = Table(title="Model Configuration")
    model_table.add_column("Model", style="cyan")
    model_table.add_column("Status", style="green")

    model_table.add_row(
        "ARIMA",
        "[green]✓ Enabled[/green]" if settings.enable_arima else "[red]✗ Disabled[/red]",
    )
    model_table.add_row(
        "VAR",
        "[green]✓ Enabled[/green]" if settings.enable_var else "[red]✗ Disabled[/red]",
    )
    model_table.add_row(
        "Random Forest",
        "[green]✓ Enabled[/green]" if settings.enable_rf else "[red]✗ Disabled[/red]",
    )
    model_table.add_row("Ensemble Window", f"{settings.ensemble_window} days")

    console.print(model_table)


def main() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
