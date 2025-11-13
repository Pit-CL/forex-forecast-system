#!/usr/bin/env python3
"""
CI Coverage Diagnostic Script.

Analyzes why CI95 coverage is only 85.7% instead of the expected >92%.

This script:
1. Loads historical validation results
2. Analyzes distribution of forecast errors
3. Tests different CI estimation methods:
   - Current: Normal distribution (z-score = 1.96)
   - Alternative: t-distribution (accounts for uncertainty)
   - Alternative: Bootstrap (non-parametric)
4. Recommends improvements

Usage:
    python scripts/diagnose_ci_coverage.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from scipy import stats
from loguru import logger

from forex_core.config import get_settings
from forex_core.mlops import PredictionTracker

console = Console()


def analyze_residuals(errors: np.ndarray) -> dict:
    """
    Analyze distribution of forecast errors.

    Args:
        errors: Array of forecast errors (predicted - actual).

    Returns:
        Dictionary with distribution statistics.
    """
    # Descriptive stats
    mean_error = np.mean(errors)
    std_error = np.std(errors, ddof=1)  # Sample std dev
    skewness = stats.skew(errors)
    kurtosis = stats.kurtosis(errors)

    # Normality tests
    shapiro_stat, shapiro_p = stats.shapiro(errors)

    # Jarque-Bera test for normality
    jb_stat, jb_p = stats.jarque_bera(errors)

    return {
        "n": len(errors),
        "mean": mean_error,
        "std": std_error,
        "skewness": skewness,
        "kurtosis": kurtosis,
        "shapiro_stat": shapiro_stat,
        "shapiro_p": shapiro_p,
        "jb_stat": jb_stat,
        "jb_p": jb_p,
        "is_normal": shapiro_p > 0.05 and jb_p > 0.05,
    }


def compute_ci_coverage(
    errors: np.ndarray,
    std_estimates: np.ndarray,
    method: str = "normal",
    confidence: float = 0.95,
) -> float:
    """
    Compute CI coverage using different methods.

    Args:
        errors: Forecast errors.
        std_estimates: Estimated standard deviations (predicted).
        method: "normal", "t-dist", or "bootstrap".
        confidence: Confidence level (0.95 for 95%).

    Returns:
        Coverage rate (fraction of errors within intervals).
    """
    n = len(errors)
    alpha = 1 - confidence

    if method == "normal":
        # Current method: z-score
        z = stats.norm.ppf(1 - alpha / 2)
        ci_low = -z * std_estimates
        ci_high = z * std_estimates

    elif method == "t-dist":
        # t-distribution with df = n - 1
        df = max(n - 1, 1)
        t = stats.t.ppf(1 - alpha / 2, df=df)
        ci_low = -t * std_estimates
        ci_high = t * std_estimates

    elif method == "bootstrap":
        # Bootstrap percentile method
        percentile_low = (alpha / 2) * 100
        percentile_high = (1 - alpha / 2) * 100

        ci_low = np.percentile(errors, percentile_low)
        ci_high = np.percentile(errors, percentile_high)

        # Expand for all observations (simple approach)
        ci_low = np.full(n, ci_low)
        ci_high = np.full(n, ci_high)

    else:
        raise ValueError(f"Unknown method: {method}")

    # Check coverage
    in_interval = (errors >= ci_low) & (errors <= ci_high)
    coverage = np.mean(in_interval)

    return coverage


def recommend_improvements(dist_stats: dict, coverage_results: dict) -> list[str]:
    """
    Generate recommendations based on analysis.

    Args:
        dist_stats: Distribution statistics from analyze_residuals().
        coverage_results: Coverage rates for different methods.

    Returns:
        List of recommendation strings.
    """
    recommendations = []

    # Check normality
    if not dist_stats["is_normal"]:
        recommendations.append(
            f"⚠️  Errors are NOT normally distributed (Shapiro p={dist_stats['shapiro_p']:.4f}). "
            "Consider using t-distribution or bootstrap methods."
        )

    # Check skewness
    if abs(dist_stats["skewness"]) > 0.5:
        recommendations.append(
            f"⚠️  High skewness ({dist_stats['skewness']:.2f}). "
            "Asymmetric errors suggest using quantile regression or bootstrapping."
        )

    # Check kurtosis
    if abs(dist_stats["kurtosis"]) > 1.0:
        recommendations.append(
            f"⚠️  High kurtosis ({dist_stats['kurtosis']:.2f}). "
            "Fat tails suggest using t-distribution with lower df."
        )

    # Compare coverage methods
    best_method = max(coverage_results, key=coverage_results.get)
    best_coverage = coverage_results[best_method]

    if best_coverage > 0.92:
        recommendations.append(
            f"✅ Switch to {best_method} method achieves {best_coverage:.1%} coverage."
        )
    else:
        recommendations.append(
            f"⚠️  Even best method ({best_method}) only achieves {best_coverage:.1%}. "
            "Consider: (1) Longer validation window, (2) Ensemble uncertainty, "
            "(3) Time-varying volatility (GARCH)."
        )

    return recommendations


def main():
    """Main diagnostic script."""
    console.print("\n[bold cyan]CI Coverage Diagnostic Tool[/bold cyan]\n")

    # Load settings
    settings = get_settings()

    # Load predictions directly from parquet
    console.print("[yellow]Loading prediction history...[/yellow]")
    storage_path = settings.data_dir / "predictions" / "predictions.parquet"

    if not storage_path.exists():
        console.print(f"[red]No prediction data found at {storage_path}![/red]")
        return

    # Read parquet file
    df = pd.read_parquet(storage_path)

    if df.empty:
        console.print("[red]Prediction file is empty![/red]")
        return

    # Filter for predictions with actuals
    df_with_actuals = df[df["actual_value"].notna()].copy()

    if len(df_with_actuals) == 0:
        console.print("[red]No predictions have actual values yet![/red]")
        console.print(f"Total predictions: {len(df)}")
        console.print(f"With actuals: 0")
        return

    console.print(f"✓ Loaded {len(df_with_actuals)} predictions with actuals\n")

    # Analyze by horizon
    for horizon in df_with_actuals["horizon"].unique():
        console.print(f"[bold yellow]═══ Analyzing {horizon} ═══[/bold yellow]\n")

        horizon_df = df_with_actuals[df_with_actuals["horizon"] == horizon].copy()

        # Calculate errors
        horizon_df["error"] = horizon_df["predicted_mean"] - horizon_df["actual_value"]
        horizon_df["ci_width"] = horizon_df["ci95_high"] - horizon_df["ci95_low"]
        horizon_df["predicted_std"] = horizon_df["ci_width"] / (2 * 1.96)  # Reverse engineer std

        errors = horizon_df["error"].values
        predicted_std = horizon_df["predicted_std"].values

        # 1. Distribution analysis
        console.print("[cyan]1. Error Distribution Analysis[/cyan]")
        dist_stats = analyze_residuals(errors)

        dist_table = Table(show_header=False, box=None)
        dist_table.add_column("Metric", style="dim")
        dist_table.add_column("Value")

        dist_table.add_row("Sample size", f"{dist_stats['n']}")
        dist_table.add_row("Mean error", f"{dist_stats['mean']:.2f} CLP")
        dist_table.add_row("Std dev", f"{dist_stats['std']:.2f} CLP")
        dist_table.add_row("Skewness", f"{dist_stats['skewness']:.3f}")
        dist_table.add_row("Kurtosis", f"{dist_stats['kurtosis']:.3f}")
        dist_table.add_row("Shapiro-Wilk p", f"{dist_stats['shapiro_p']:.4f}")
        dist_table.add_row("Jarque-Bera p", f"{dist_stats['jb_p']:.4f}")
        dist_table.add_row(
            "Normal?",
            "[green]Yes[/green]" if dist_stats["is_normal"] else "[red]No[/red]",
        )

        console.print(dist_table)
        console.print()

        # 2. Current coverage
        console.print("[cyan]2. Current CI Coverage (Normal z-score)[/cyan]")
        current_coverage = compute_ci_coverage(errors, predicted_std, method="normal")
        console.print(f"Current CI95 Coverage: [yellow]{current_coverage:.1%}[/yellow]")
        console.print(f"Target: [green]≥92%[/green]")
        console.print(f"Gap: [red]{92 - current_coverage * 100:.1f}pp[/red]\n")

        # 3. Alternative methods
        console.print("[cyan]3. Alternative CI Methods[/cyan]")
        coverage_results = {
            "normal": current_coverage,
            "t-dist": compute_ci_coverage(errors, predicted_std, method="t-dist"),
            "bootstrap": compute_ci_coverage(errors, predicted_std, method="bootstrap"),
        }

        alt_table = Table(show_header=True, box=None)
        alt_table.add_column("Method", style="cyan")
        alt_table.add_column("CI95 Coverage", justify="right")
        alt_table.add_column("Improvement", justify="right")

        for method, coverage in coverage_results.items():
            improvement = (coverage - current_coverage) * 100
            color = "green" if coverage >= 0.92 else "yellow" if coverage >= 0.85 else "red"

            alt_table.add_row(
                method,
                f"[{color}]{coverage:.1%}[/{color}]",
                f"{improvement:+.1f}pp" if improvement != 0 else "-",
            )

        console.print(alt_table)
        console.print()

        # 4. Recommendations
        console.print("[cyan]4. Recommendations[/cyan]")
        recommendations = recommend_improvements(dist_stats, coverage_results)

        for i, rec in enumerate(recommendations, 1):
            console.print(f"{i}. {rec}")

        console.print("\n" + "─" * 80 + "\n")

    # Summary
    console.print(Panel(
        "[bold green]Analysis complete![/bold green]\n\n"
        "Next steps:\n"
        "1. Update ForecastEngine._build_points() to use t-distribution\n"
        "2. Test with historical validation data\n"
        "3. Re-run validation to confirm >92% coverage\n"
        "4. Consider bootstrap for highly non-normal errors",
        title="Summary",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
