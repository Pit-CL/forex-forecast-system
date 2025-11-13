#!/usr/bin/env python3
"""
Performance Monitoring CLI.

Check forecast accuracy metrics for degradation.

Usage:
    python scripts/check_performance.py --horizon 7d
    python scripts/check_performance.py --all
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from forex_core.mlops.performance_monitor import PerformanceMonitor, PerformanceStatus

app = typer.Typer(help="Performance monitoring CLI")
console = Console()


@app.command()
def check(
    horizon: str = typer.Option(None, "--horizon", "-h", help="Specific horizon to check"),
    all_horizons: bool = typer.Option(False, "--all", "-a", help="Check all horizons"),
    data_dir: Path = typer.Option(Path("data"), "--data-dir", "-d", help="Data directory"),
):
    """
    Check forecast performance for degradation.

    Examples:
        python scripts/check_performance.py --horizon 7d
        python scripts/check_performance.py --all
    """
    console.print("\n[bold cyan]Performance Monitoring Check[/bold cyan]\n")

    # Initialize monitor
    monitor = PerformanceMonitor(
        data_dir=data_dir,
        baseline_days=60,
        recent_days=14,
        degradation_threshold=0.15,  # 15%
    )

    if all_horizons or horizon is None:
        # Check all horizons
        reports = monitor.check_all_horizons()

        # Summary table
        summary_table = Table(title="Performance Summary", show_header=True)
        summary_table.add_column("Horizon", style="cyan")
        summary_table.add_column("Status", justify="center")
        summary_table.add_column("RMSE Δ", justify="right")
        summary_table.add_column("MAPE Δ", justify="right")
        summary_table.add_column("Samples", justify="right")

        for hor, report in reports.items():
            # Color code by status
            if report.status == PerformanceStatus.EXCELLENT:
                status_style = "green bold"
            elif report.status == PerformanceStatus.GOOD:
                status_style = "green"
            elif report.status == PerformanceStatus.DEGRADED:
                status_style = "yellow"
            else:  # CRITICAL
                status_style = "red bold"

            rmse_delta = report.degradation_pct.get("rmse", 0.0)
            mape_delta = report.degradation_pct.get("mape", 0.0)

            summary_table.add_row(
                hor,
                f"[{status_style}]{report.status.value.upper()}[/{status_style}]",
                f"[{status_style}]{rmse_delta:+.1f}%[/{status_style}]",
                f"[{status_style}]{mape_delta:+.1f}%[/{status_style}]",
                str(report.recent_metrics.n_predictions),
            )

        console.print(summary_table)
        console.print()

        # Show details for degraded/critical
        for hor, report in reports.items():
            if report.degradation_detected:
                _print_detailed_report(report, console)

    else:
        # Check specific horizon
        report = monitor.check_performance(horizon)
        _print_detailed_report(report, console)


def _print_detailed_report(report, console):
    """Print detailed degradation report."""
    # Status panel color
    if report.status == PerformanceStatus.EXCELLENT:
        border_color = "green"
        status_emoji = "✅"
    elif report.status == PerformanceStatus.GOOD:
        border_color = "green"
        status_emoji = "✓"
    elif report.status == PerformanceStatus.DEGRADED:
        border_color = "yellow"
        status_emoji = "⚠"
    else:  # CRITICAL
        border_color = "red"
        status_emoji = "✗"

    console.print(f"\n[bold]Horizon: {report.horizon}[/bold]")
    console.print(
        Panel(
            f"[bold]Status:[/bold] {status_emoji} {report.status.value.upper()}\n"
            f"[bold]Degradation Detected:[/bold] {report.degradation_detected}\n\n"
            f"{report.recommendation}",
            title=f"Performance Status - {report.horizon}",
            border_style=border_color,
        )
    )

    # Metrics comparison table
    if report.baseline_metrics and report.degradation_pct:
        metrics_table = Table(show_header=True, title=f"Metrics Comparison - {report.horizon}")
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Baseline", justify="right")
        metrics_table.add_column("Recent", justify="right")
        metrics_table.add_column("Change", justify="right")
        metrics_table.add_column("P-value", justify="right")
        metrics_table.add_column("Significant", justify="center")

        for metric in ["rmse", "mape", "mae"]:
            if metric in report.baseline_metrics:
                baseline = report.baseline_metrics[metric].mean
                recent = getattr(report.recent_metrics, metric)
                delta = report.degradation_pct.get(metric, 0.0)
                p_value = report.p_value.get(metric, 1.0)

                # Color code degradation
                if delta > 15 and p_value < 0.05:
                    delta_style = "red"
                elif delta > 5:
                    delta_style = "yellow"
                elif delta < -5:
                    delta_style = "green"
                else:
                    delta_style = "white"

                significant = "✓" if p_value < 0.05 else "○"

                metrics_table.add_row(
                    metric.upper(),
                    f"{baseline:.2f}",
                    f"{recent:.2f}",
                    f"[{delta_style}]{delta:+.1f}%[/{delta_style}]",
                    f"{p_value:.3f}",
                    significant,
                )

        console.print(metrics_table)
        console.print()

    # Additional metrics
    if report.recent_metrics.n_predictions > 0:
        console.print("[yellow]Additional Metrics:[/yellow]")
        add_table = Table(show_header=False, box=None)
        add_table.add_column("Metric", style="dim")
        add_table.add_column("Value")

        add_table.add_row("Recent Predictions", str(report.recent_metrics.n_predictions))
        add_table.add_row("CI95 Coverage", f"{report.recent_metrics.ci95_coverage:.1%}")
        add_table.add_row("Bias", f"{report.recent_metrics.bias:+.2f}")

        if report.baseline_metrics:
            baseline_samples = report.baseline_metrics["rmse"].n_samples
            add_table.add_row("Baseline Predictions", str(baseline_samples))

        console.print(add_table)
        console.print()


if __name__ == "__main__":
    app()
