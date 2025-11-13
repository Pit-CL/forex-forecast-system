#!/usr/bin/env python3
"""
MLOps Dashboard CLI.

Herramienta de línea de comandos para monitorear el sistema de forecasting:
- Estado general del sistema
- Análisis de drift
- Resultados de validación
- Historial de alertas

Usage:
    python scripts/mlops_dashboard.py show
    python scripts/mlops_dashboard.py drift --horizon 7d
    python scripts/mlops_dashboard.py validation --horizon 7d
    python scripts/mlops_dashboard.py alerts --horizon 7d --days 7
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timedelta

import typer
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

app = typer.Typer(
    help="MLOps Dashboard - Monitor forex forecasting system",
    add_completion=False,
)
console = Console()


@app.command()
def show(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information"),
):
    """
    Show overall system status and health.

    Displays:
    - Prediction tracking status
    - Recent drift analysis
    - Latest validation results
    - Alert activity
    - Chronos readiness score
    """
    from forex_core.mlops.dashboard_utils import (
        get_alert_summary,
        get_drift_summary,
        get_prediction_summary,
        get_readiness_summary,
        get_validation_summary,
    )

    console.print("\n[bold cyan]MLOps System Dashboard[/bold cyan]", style="bold")
    console.print(f"[dim]As of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n")

    # 1. Prediction Tracking
    console.print("[yellow]═══ Prediction Tracking ═══[/yellow]")
    pred_summary = get_prediction_summary()

    if pred_summary:
        pred_table = Table(show_header=True, box=None)
        pred_table.add_column("Horizon", style="cyan")
        pred_table.add_column("Total", justify="right")
        pred_table.add_column("Last 7d", justify="right")
        pred_table.add_column("Last 30d", justify="right")
        pred_table.add_column("Latest", style="dim")

        for row in pred_summary:
            pred_table.add_row(
                row["horizon"],
                str(row["total"]),
                str(row["last_7d"]),
                str(row["last_30d"]),
                row["latest_date"],
            )

        console.print(pred_table)
    else:
        console.print("[dim]No prediction data available[/dim]")

    console.print()

    # 2. Drift Status
    console.print("[yellow]═══ Drift Status ═══[/yellow]")
    drift_summary = get_drift_summary()

    if drift_summary:
        drift_table = Table(show_header=True, box=None)
        drift_table.add_column("Horizon", style="cyan")
        drift_table.add_column("Current Score", justify="right")
        drift_table.add_column("Trend", justify="center")
        drift_table.add_column("Status", justify="center")

        for row in drift_summary:
            # Color code status
            status = row["status"]
            if "CRITICAL" in status or "HIGH" in status:
                status_style = "red bold"
            elif "WARNING" in status:
                status_style = "yellow"
            else:
                status_style = "green"

            drift_table.add_row(
                row["horizon"],
                f"{row['score']:.1f}/100",
                row["trend"],
                Text(status, style=status_style),
            )

        console.print(drift_table)
    else:
        console.print("[dim]No drift history available[/dim]")

    console.print()

    # 3. Validation Results
    console.print("[yellow]═══ Latest Validation ═══[/yellow]")
    val_summary = get_validation_summary()

    if val_summary:
        val_table = Table(show_header=True, box=None)
        val_table.add_column("Horizon", style="cyan")
        val_table.add_column("RMSE", justify="right")
        val_table.add_column("MAPE", justify="right")
        val_table.add_column("CI95", justify="right")
        val_table.add_column("Status", justify="center")

        for row in val_summary:
            status = "✓" if row["acceptable"] else "✗"
            status_style = "green" if row["acceptable"] else "red"

            val_table.add_row(
                row["horizon"],
                f"{row['rmse']:.2f}",
                f"{row['mape']:.2f}%",
                f"{row['ci95']:.1%}",
                Text(status, style=status_style),
            )

        console.print(val_table)
    else:
        console.print("[dim]No validation results available[/dim]")

    console.print()

    # 4. Alert Activity
    console.print("[yellow]═══ Recent Alerts (7 days) ═══[/yellow]")
    alert_summary = get_alert_summary(days=7)

    if alert_summary:
        alert_table = Table(show_header=True, box=None)
        alert_table.add_column("Horizon", style="cyan")
        alert_table.add_column("Total", justify="right")
        alert_table.add_column("Sent", justify="right")
        alert_table.add_column("No Alert", justify="right")
        alert_table.add_column("Last Alert", style="dim")

        for row in alert_summary:
            alert_table.add_row(
                row["horizon"],
                str(row["total"]),
                str(row["sent"]),
                str(row["no_alert"]),
                row["last_alert"] if row["last_alert"] else "Never",
            )

        console.print(alert_table)
    else:
        console.print("[dim]No alert history available[/dim]")

    console.print()

    # 5. Chronos Readiness
    console.print("[yellow]═══ Chronos Readiness ═══[/yellow]")
    readiness = get_readiness_summary()

    if readiness:
        score = readiness["score"]
        level = readiness["level"]

        # Color code by readiness level
        if level == "PRODUCTION_READY":
            color = "green"
            emoji = "✓"
        elif level == "TESTING_READY":
            color = "yellow"
            emoji = "⚡"
        elif level == "DEVELOPMENT":
            color = "blue"
            emoji = "🔧"
        else:
            color = "red"
            emoji = "✗"

        console.print(
            Panel(
                f"[{color} bold]{emoji} {level}[/{color} bold]\n"
                f"Score: [{color}]{score}/100[/{color}]\n"
                f"[dim]{readiness['recommendation']}[/dim]",
                border_style=color,
            )
        )
    else:
        console.print("[dim]Readiness check not available[/dim]")

    console.print()


@app.command()
def drift(
    horizon: str = typer.Option("7d", "--horizon", "-h", help="Forecast horizon (7d, 15d, 30d, 90d)"),
    days: int = typer.Option(90, "--days", "-d", help="Days of history to show"),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed drift breakdown"),
):
    """
    Show drift analysis for a specific horizon.

    Displays:
    - Drift trend over time
    - Current drift score
    - Breakdown by test type (KS, T-test, Levene, Ljung-Box)
    - Recommendations
    """
    from forex_core.mlops.dashboard_utils import get_drift_details, plot_drift_trend

    console.print(f"\n[bold cyan]Drift Analysis - {horizon}[/bold cyan]\n")

    drift_data = get_drift_details(horizon, days)

    if not drift_data:
        console.print(f"[red]No drift data available for {horizon}[/red]")
        return

    # Summary stats
    console.print("[yellow]Summary[/yellow]")
    summary_table = Table(show_header=False, box=None)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value")

    summary_table.add_row("Current Score", f"{drift_data['current_score']:.1f}/100")
    summary_table.add_row("30-day Average", f"{drift_data['avg_30d']:.1f}/100")
    summary_table.add_row("90-day Average", f"{drift_data['avg_90d']:.1f}/100")
    summary_table.add_row("Trend", drift_data["trend"])
    summary_table.add_row("Consecutive HIGH", str(drift_data["consecutive_high"]))

    console.print(summary_table)
    console.print()

    # Recommendation
    recommendation = drift_data["recommendation"]
    if "CRITICAL" in recommendation:
        style = "red bold"
    elif "WARNING" in recommendation:
        style = "yellow"
    else:
        style = "green"

    console.print(Panel(recommendation, title="Recommendation", border_style=style))
    console.print()

    # Drift trend chart (ASCII art)
    if drift_data["history"]:
        console.print("[yellow]Drift Trend (last 30 days)[/yellow]")
        plot_drift_trend(drift_data["history"], console)
        console.print()

    # Detailed breakdown
    if detailed and drift_data.get("test_breakdown"):
        console.print("[yellow]Test Breakdown[/yellow]")
        breakdown_table = Table(show_header=True)
        breakdown_table.add_column("Date", style="dim")
        breakdown_table.add_column("KS", justify="center")
        breakdown_table.add_column("T-test", justify="center")
        breakdown_table.add_column("Levene", justify="center")
        breakdown_table.add_column("Ljung-Box", justify="center")
        breakdown_table.add_column("Score", justify="right")

        for row in drift_data["test_breakdown"][-10:]:  # Last 10 entries
            breakdown_table.add_row(
                row["date"],
                "✓" if row["ks"] else "○",
                "✓" if row["t"] else "○",
                "✓" if row["levene"] else "○",
                "✓" if row["ljungbox"] else "○",
                f"{row['score']:.1f}",
            )

        console.print(breakdown_table)


@app.command()
def validation(
    horizon: str = typer.Option("7d", "--horizon", "-h", help="Forecast horizon"),
    limit: int = typer.Option(5, "--limit", "-n", help="Number of reports to show"),
):
    """
    Show validation results for a specific horizon.

    Displays:
    - Recent validation runs
    - Per-fold metrics
    - Performance trends
    """
    from forex_core.mlops.dashboard_utils import get_validation_details

    console.print(f"\n[bold cyan]Validation Results - {horizon}[/bold cyan]\n")

    val_data = get_validation_details(horizon, limit)

    if not val_data:
        console.print(f"[red]No validation results for {horizon}[/red]")
        return

    # Show recent runs
    console.print(f"[yellow]Recent Validation Runs ({len(val_data)} reports)[/yellow]")

    for i, report in enumerate(val_data, 1):
        acceptable = report["is_acceptable"]
        status = "✓ ACCEPTABLE" if acceptable else "✗ NEEDS IMPROVEMENT"
        status_style = "green" if acceptable else "red"

        console.print(f"\n[cyan]Run #{i}[/cyan] - {report['timestamp']}")
        console.print(f"Status: [{status_style}]{status}[/{status_style}]")
        console.print(f"Mode: {report['mode']} | Folds: {report['n_folds']}")

        metrics_table = Table(show_header=False, box=None, padding=(0, 2))
        metrics_table.add_column("Metric", style="dim")
        metrics_table.add_column("Value")

        metrics_table.add_row("RMSE", f"{report['avg_rmse']:.2f} (±{report['std_rmse']:.2f})")
        metrics_table.add_row("MAE", f"{report['avg_mae']:.2f}")
        metrics_table.add_row("MAPE", f"{report['avg_mape']:.2f}%")
        metrics_table.add_row("CI95 Coverage", f"{report['avg_ci95_coverage']:.1%}")
        metrics_table.add_row("Bias", f"{report['avg_bias']:+.2f}")

        console.print(metrics_table)


@app.command()
def alerts(
    horizon: str = typer.Option(None, "--horizon", "-h", help="Filter by horizon"),
    days: int = typer.Option(30, "--days", "-d", help="Days of history"),
    severity: str = typer.Option(None, "--severity", "-s", help="Filter by severity"),
):
    """
    Show alert history and patterns.

    Displays:
    - Recent alerts by horizon
    - Alert frequency
    - Event types triggering alerts
    """
    from forex_core.mlops.dashboard_utils import get_alert_details

    title = "Alert History"
    if horizon:
        title += f" - {horizon}"
    if severity:
        title += f" ({severity.upper()})"

    console.print(f"\n[bold cyan]{title}[/bold cyan]\n")

    alert_data = get_alert_details(horizon, days, severity)

    if not alert_data:
        console.print("[red]No alert data available[/red]")
        return

    # Alert frequency
    console.print(f"[yellow]Last {days} days[/yellow]")
    freq_table = Table(show_header=True, box=None)
    freq_table.add_column("Horizon", style="cyan")
    freq_table.add_column("Total Checks", justify="right")
    freq_table.add_column("Alerts Sent", justify="right")
    freq_table.add_column("Alert Rate", justify="right")
    freq_table.add_column("Avg Severity", justify="center")

    for row in alert_data["frequency"]:
        alert_rate = (row["alerts_sent"] / row["total_checks"] * 100) if row["total_checks"] > 0 else 0

        freq_table.add_row(
            row["horizon"],
            str(row["total_checks"]),
            str(row["alerts_sent"]),
            f"{alert_rate:.1f}%",
            row["avg_severity"],
        )

    console.print(freq_table)
    console.print()

    # Recent alerts
    if alert_data.get("recent"):
        console.print("[yellow]Recent Alerts[/yellow]")
        recent_table = Table(show_header=True)
        recent_table.add_column("Date", style="dim")
        recent_table.add_column("Horizon", style="cyan")
        recent_table.add_column("Severity", justify="center")
        recent_table.add_column("Reason", style="dim")

        for row in alert_data["recent"][-10:]:
            severity_text = row["severity"].upper()
            if severity_text in ["CRITICAL", "HIGH"]:
                severity_style = "red bold"
            elif severity_text == "WARNING":
                severity_style = "yellow"
            else:
                severity_style = "green"

            recent_table.add_row(
                row["timestamp"],
                row["horizon"],
                Text(severity_text, style=severity_style),
                row["reason"][:50] + "..." if len(row["reason"]) > 50 else row["reason"],
            )

        console.print(recent_table)


if __name__ == "__main__":
    app()
