"""
Command-line interface for importer report service.

This module provides a CLI using Typer for generating comprehensive
monthly macro-economic reports for importers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from forex_core.config import get_settings
from forex_core.utils.logging import logger, configure_logging

from .config import get_service_config
from .pipeline import run_report_pipeline

app = typer.Typer(
    name="importer-report",
    help="Comprehensive macro-economic report for importers",
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
        help="Path to log file (default: logs/importer_report.log)",
    ),
) -> None:
    """
    Generate comprehensive importer macro-economic report.

    This command executes the complete report generation workflow:
    - Load data from multiple sources
    - Generate 7-day daily forecast
    - Generate 12-month monthly forecast
    - Perform PESTEL analysis
    - Perform Porter's Five Forces analysis
    - Analyze target sectors (restaurants, retail, etc.)
    - Create comprehensive 10-20 page PDF report
    - Send email notification (optional)

    Examples:
        # Generate monthly report with email
        $ python -m services.importer_report.cli run

        # Generate report without email
        $ python -m services.importer_report.cli run --skip-email

        # Custom output directory and debug logging
        $ python -m services.importer_report.cli run -o ./reports -l DEBUG
    """
    # Configure logging
    if log_file is None:
        log_file = Path("./logs/importer_report.log")

    configure_logging(log_path=log_file, level=log_level)

    # Display banner
    console.print(
        Panel.fit(
            "[bold cyan]Informe Mensual del Entorno Macroeconómico del Importador[/bold cyan]\n"
            "[dim]Análisis Estratégico y Proyecciones USD/CLP[/dim]",
            border_style="cyan",
        )
    )

    try:
        # Run pipeline
        with console.status("[yellow]Generando informe completo...[/yellow]"):
            report_path = run_report_pipeline(
                skip_email=skip_email,
                output_dir=output_dir,
            )

        # Success message
        console.print(
            f"\n[bold green]✓ Informe generado exitosamente![/bold green]"
        )
        console.print(f"[green]Guardado en:[/green] {report_path}")

        if skip_email:
            console.print("[yellow]El envío por email fue omitido[/yellow]")

        # Display summary
        _display_report_summary()

    except Exception as e:
        console.print(f"\n[bold red]✗ La generación del informe falló:[/bold red] {e}")
        logger.exception("Pipeline execution failed")
        raise typer.Exit(code=1)


@app.command()
def preview(
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        "-l",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    ),
) -> None:
    """
    Preview report sections without generating full PDF.

    This command shows what sections would be included in the report
    without actually generating charts or PDF output. Useful for
    validation and testing.

    Examples:
        $ python -m services.importer_report.cli preview
        $ python -m services.importer_report.cli preview -l DEBUG
    """
    configure_logging(level=log_level)

    console.print("\n[bold cyan]Vista Previa del Informe[/bold cyan]")
    console.print("=" * 60)

    service_config = get_service_config()

    # Display sections that will be included
    table = Table(title="Secciones del Informe")
    table.add_column("Orden", style="cyan", justify="right")
    table.add_column("Sección", style="green")
    table.add_column("Estado", style="yellow")

    section_names = {
        "executive_summary": "Resumen Ejecutivo",
        "current_situation": "Situación Actual",
        "forecast_7d": "Proyección 7 Días",
        "forecast_12m": "Proyección 12 Meses",
        "pestel_analysis": "Análisis PESTEL",
        "porter_forces": "Fuerzas de Porter",
        "sector_analysis": "Análisis por Sector",
        "risk_matrix": "Matriz de Riesgos",
        "recommendations": "Recomendaciones",
        "sources": "Fuentes de Datos",
    }

    for i, section in enumerate(service_config.report_sections, 1):
        status = "[green]✓ Incluido[/green]"
        if section == "pestel_analysis" and not service_config.include_pestel:
            status = "[red]✗ Deshabilitado[/red]"
        elif section == "porter_forces" and not service_config.include_porter:
            status = "[red]✗ Deshabilitado[/red]"
        elif section == "sector_analysis" and not service_config.include_sector_analysis:
            status = "[red]✗ Deshabilitado[/red]"

        table.add_row(
            str(i),
            section_names.get(section, section),
            status,
        )

    console.print(table)

    # Display sectors that will be analyzed
    if service_config.include_sector_analysis:
        sectors_table = Table(title="Sectores a Analizar")
        sectors_table.add_column("Sector", style="cyan")
        sectors_table.add_column("Sensibilidad FX", style="yellow")

        for sector in service_config.target_sectors:
            sectors_table.add_row(sector, "Media-Alta")

        console.print(sectors_table)

    # Configuration summary
    console.print(f"\n[bold]Configuración:[/bold]")
    console.print(f"  Título: {service_config.report_title}")
    console.print(f"  Límite de páginas: {service_config.page_limit}")
    console.print(f"  Idioma: {service_config.language.upper()}")
    console.print(f"  Estilo de gráficos: {service_config.chart_style}")


@app.command()
def info() -> None:
    """
    Display service configuration and environment info.

    Shows current configuration, paths, API keys status, and report settings.
    """
    settings = get_settings()
    service_config = get_service_config()

    console.print("\n[bold cyan]Importer Report - Configuración[/bold cyan]")
    console.print("=" * 60)

    # Service configuration
    table = Table(title="Configuración del Servicio")
    table.add_column("Ajuste", style="cyan")
    table.add_column("Valor", style="green")

    table.add_row("Título del Informe", service_config.report_title)
    table.add_row("Límite de Páginas", str(service_config.page_limit))
    table.add_row("Idioma", service_config.language.upper())
    table.add_row("PESTEL Habilitado", "✓ Sí" if service_config.include_pestel else "✗ No")
    table.add_row("Porter Habilitado", "✓ Sí" if service_config.include_porter else "✗ No")
    table.add_row(
        "Análisis Sectorial",
        "✓ Sí" if service_config.include_sector_analysis else "✗ No",
    )
    table.add_row("Sectores Objetivo", ", ".join(service_config.target_sectors))

    console.print(table)

    # Environment settings
    env_table = Table(title="Configuración de Entorno")
    env_table.add_column("Ajuste", style="cyan")
    env_table.add_column("Valor", style="green")

    env_table.add_row("Entorno", settings.environment)
    env_table.add_row("Zona Horaria", settings.report_timezone)
    env_table.add_row("Directorio de Salida", str(settings.output_dir))
    env_table.add_row("Directorio de Datos", str(settings.data_dir))
    env_table.add_row("Directorio de Gráficos", str(settings.chart_dir))

    console.print(env_table)

    # API Keys status
    api_table = Table(title="Estado de API Keys")
    api_table.add_column("API", style="cyan")
    api_table.add_column("Estado", style="green")

    api_table.add_row(
        "FRED API",
        "[green]✓ Configurado[/green]"
        if settings.fred_api_key
        else "[red]✗ Falta[/red]",
    )
    api_table.add_row(
        "NewsAPI",
        "[green]✓ Configurado[/green]"
        if settings.news_api_key
        else "[red]✗ Falta[/red]",
    )
    api_table.add_row(
        "Alpha Vantage",
        "[green]✓ Configurado[/green]"
        if settings.alphavantage_api_key
        else "[red]✗ Falta[/red]",
    )
    api_table.add_row(
        "Gmail",
        "[green]✓ Configurado[/green]"
        if settings.gmail_user and settings.gmail_app_password
        else "[red]✗ Falta[/red]",
    )

    console.print(api_table)

    # Model configuration
    model_table = Table(title="Configuración de Modelos")
    model_table.add_column("Modelo", style="cyan")
    model_table.add_column("Estado", style="green")

    model_table.add_row(
        "ARIMA",
        "[green]✓ Habilitado[/green]"
        if settings.enable_arima
        else "[red]✗ Deshabilitado[/red]",
    )
    model_table.add_row(
        "VAR",
        "[green]✓ Habilitado[/green]"
        if settings.enable_var
        else "[red]✗ Deshabilitado[/red]",
    )
    model_table.add_row(
        "Random Forest",
        "[green]✓ Habilitado[/green]"
        if settings.enable_rf
        else "[red]✗ Deshabilitado[/red]",
    )
    model_table.add_row("Ventana de Ensemble", f"{settings.ensemble_window} días")

    console.print(model_table)


def _display_report_summary() -> None:
    """Display summary of generated report content."""
    service_config = get_service_config()

    summary = Table(title="Contenido del Informe")
    summary.add_column("Componente", style="cyan")
    summary.add_column("Descripción", style="green")

    summary.add_row("Pronósticos", "7 días (diario) + 12 meses (mensual)")
    summary.add_row("Análisis PESTEL", "6 dimensiones estratégicas")
    summary.add_row("Fuerzas de Porter", "5 fuerzas competitivas")
    summary.add_row("Análisis Sectorial", f"{len(service_config.target_sectors)} sectores")
    summary.add_row("Matriz de Riesgos", "Identificación y mitigación")
    summary.add_row("Recomendaciones", "Estratégicas y tácticas")

    console.print("\n")
    console.print(summary)


def main() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
