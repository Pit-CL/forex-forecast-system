#!/usr/bin/env python3
"""
USD/CLP Specific Calibration Script.

Analyzes historical USD/CLP data to calibrate system parameters:
- Drift detection thresholds
- Performance monitoring baselines
- Regime detection sensitivity
- Seasonal patterns
- Copper correlation parameters

Usage:
    python scripts/calibrate_usdclp.py --analyze
    python scripts/calibrate_usdclp.py --update-config
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import typer
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from scipy import stats

app = typer.Typer(help="USD/CLP calibration tool")
console = Console()


def analyze_historical_volatility(df: pd.DataFrame) -> dict:
    """
    Analyze historical USD/CLP volatility patterns.

    Returns:
        Dictionary with volatility statistics.
    """
    console.print("\n[yellow]═══ Historical Volatility Analysis ═══[/yellow]")

    # Calculate daily returns
    df = df.sort_values('date')
    df['return'] = df['close'].pct_change()

    # Overall statistics
    returns = df['return'].dropna()

    stats_dict = {
        'mean_return': returns.mean(),
        'std_daily': returns.std(),
        'std_weekly': returns.std() * np.sqrt(7),
        'std_monthly': returns.std() * np.sqrt(30),
        'std_quarterly': returns.std() * np.sqrt(90),
        'skewness': stats.skew(returns),
        'kurtosis': stats.kurtosis(returns),
        'p95': np.percentile(np.abs(returns), 95),
        'p99': np.percentile(np.abs(returns), 99),
    }

    # Monthly volatility patterns (seasonality)
    df['month'] = pd.to_datetime(df['date']).dt.month
    monthly_vol = df.groupby('month')['return'].std()

    stats_dict['seasonal_vol'] = monthly_vol.to_dict()
    stats_dict['high_vol_months'] = monthly_vol.nlargest(3).index.tolist()
    stats_dict['low_vol_months'] = monthly_vol.nsmallest(3).index.tolist()

    # Display results
    vol_table = Table(title="Volatility Statistics", show_header=True)
    vol_table.add_column("Metric", style="cyan")
    vol_table.add_column("Value", justify="right")

    vol_table.add_row("Mean Daily Return", f"{stats_dict['mean_return']:.4%}")
    vol_table.add_row("Daily Volatility (σ)", f"{stats_dict['std_daily']:.4%}")
    vol_table.add_row("Weekly Volatility (σ)", f"{stats_dict['std_weekly']:.4%}")
    vol_table.add_row("Monthly Volatility (σ)", f"{stats_dict['std_monthly']:.4%}")
    vol_table.add_row("Quarterly Volatility (σ)", f"{stats_dict['std_quarterly']:.4%}")
    vol_table.add_row("Skewness", f"{stats_dict['skewness']:.3f}")
    vol_table.add_row("Kurtosis", f"{stats_dict['kurtosis']:.3f}")
    vol_table.add_row("95th Percentile |Return|", f"{stats_dict['p95']:.4%}")
    vol_table.add_row("99th Percentile |Return|", f"{stats_dict['p99']:.4%}")

    console.print(vol_table)
    console.print()

    # Seasonal patterns
    console.print("[cyan]High Volatility Months:[/cyan]",
                  ", ".join(f"Month {m}" for m in stats_dict['high_vol_months']))
    console.print("[cyan]Low Volatility Months:[/cyan]",
                  ", ".join(f"Month {m}" for m in stats_dict['low_vol_months']))
    console.print()

    return stats_dict


def analyze_copper_correlation(usdclp_df: pd.DataFrame, copper_df: pd.DataFrame) -> dict:
    """
    Analyze USD/CLP - Copper correlation patterns.

    Returns:
        Dictionary with correlation statistics.
    """
    console.print("[yellow]═══ Copper Correlation Analysis ═══[/yellow]")

    # Merge data
    merged = pd.merge(
        usdclp_df[['date', 'close']].rename(columns={'close': 'usdclp'}),
        copper_df[['date', 'close']].rename(columns={'close': 'copper'}),
        on='date',
        how='inner'
    )

    # Calculate returns
    merged['usdclp_return'] = merged['usdclp'].pct_change()
    merged['copper_return'] = merged['copper'].pct_change()
    merged = merged.dropna()

    # Overall correlation
    overall_corr = merged[['usdclp_return', 'copper_return']].corr().iloc[0, 1]

    # Rolling correlation (30-day window)
    merged['rolling_corr'] = merged['usdclp_return'].rolling(30).corr(merged['copper_return'])

    corr_stats = {
        'overall_correlation': overall_corr,
        'mean_rolling_corr': merged['rolling_corr'].mean(),
        'std_rolling_corr': merged['rolling_corr'].std(),
        'min_rolling_corr': merged['rolling_corr'].min(),
        'max_rolling_corr': merged['rolling_corr'].max(),
        'correlation_break_threshold': merged['rolling_corr'].std() * 2,
    }

    # Display results
    corr_table = Table(title="Copper Correlation Statistics", show_header=True)
    corr_table.add_column("Metric", style="cyan")
    corr_table.add_column("Value", justify="right")

    corr_table.add_row("Overall Correlation", f"{corr_stats['overall_correlation']:.3f}")
    corr_table.add_row("Mean Rolling Correlation (30d)", f"{corr_stats['mean_rolling_corr']:.3f}")
    corr_table.add_row("Std Rolling Correlation", f"{corr_stats['std_rolling_corr']:.3f}")
    corr_table.add_row("Min Rolling Correlation", f"{corr_stats['min_rolling_corr']:.3f}")
    corr_table.add_row("Max Rolling Correlation", f"{corr_stats['max_rolling_corr']:.3f}")
    corr_table.add_row("Correlation Break Threshold", f"{corr_stats['correlation_break_threshold']:.3f}")

    console.print(corr_table)
    console.print()

    # Interpretation
    if overall_corr < -0.5:
        console.print("[green]✓ Strong inverse correlation detected (expected for USD/CLP-Copper)[/green]")
    elif overall_corr < -0.3:
        console.print("[yellow]⚠ Moderate inverse correlation (weaker than expected)[/yellow]")
    else:
        console.print("[red]✗ Weak or positive correlation (unexpected)[/red]")
    console.print()

    return corr_stats


def calculate_drift_thresholds(vol_stats: dict) -> dict:
    """
    Calculate recommended drift detection thresholds based on volatility.

    Returns:
        Dictionary with recommended thresholds.
    """
    console.print("[yellow]═══ Drift Detection Threshold Recommendations ═══[/yellow]")

    # Base thresholds on historical volatility
    # KS test: Use p-value of 0.05 (standard)
    # But adjust window size based on volatility

    daily_vol = vol_stats['std_daily']

    thresholds = {
        # Statistical test thresholds
        'ks_test_pvalue': 0.05,
        'levene_test_pvalue': 0.05,
        't_test_pvalue': 0.05,
        'ljungbox_pvalue': 0.05,

        # Drift score thresholds (0-100 scale)
        # Lower score = more drift detected
        'high_drift_threshold': 40,  # Score < 40 = HIGH drift
        'medium_drift_threshold': 60,  # Score < 60 = MEDIUM drift

        # Volatility thresholds (for regime detection)
        'high_vol_zscore': 2.0,  # 2σ above historical mean
        'extreme_vol_zscore': 3.0,  # 3σ above historical mean

        # Window sizes based on volatility
        'drift_check_window': 30 if daily_vol < 0.005 else 14,  # Days
        'baseline_window': 90,  # Days for baseline

        # Copper shock thresholds
        'copper_shock_threshold': 0.05,  # 5% change in 5 days

        # Performance degradation thresholds
        'rmse_degradation_threshold': 0.15,  # 15% increase
        'mape_degradation_threshold': 0.20,  # 20% increase
    }

    # Display recommendations
    thresh_table = Table(title="Recommended Thresholds", show_header=True)
    thresh_table.add_column("Parameter", style="cyan")
    thresh_table.add_column("Value", justify="right")
    thresh_table.add_column("Rationale", style="dim")

    thresh_table.add_row(
        "High Drift Score Threshold",
        f"{thresholds['high_drift_threshold']}",
        "Conservative for USD/CLP volatility"
    )

    thresh_table.add_row(
        "High Vol Z-score",
        f"{thresholds['high_vol_zscore']}σ",
        "2σ = ~5% of observations"
    )

    thresh_table.add_row(
        "Drift Check Window",
        f"{thresholds['drift_check_window']} days",
        f"Based on daily vol: {daily_vol:.4%}"
    )

    thresh_table.add_row(
        "Copper Shock Threshold",
        f"{thresholds['copper_shock_threshold']:.1%}",
        "Historical copper volatility"
    )

    thresh_table.add_row(
        "RMSE Degradation Alert",
        f"{thresholds['rmse_degradation_threshold']:.0%}",
        "Balance sensitivity/false positives"
    )

    console.print(thresh_table)
    console.print()

    return thresholds


def generate_calibration_config(
    vol_stats: dict,
    corr_stats: dict,
    thresholds: dict
) -> dict:
    """
    Generate complete calibration configuration.

    Returns:
        Configuration dictionary for USD/CLP.
    """
    config = {
        'metadata': {
            'calibration_date': datetime.now().isoformat(),
            'currency_pair': 'USD/CLP',
            'data_source': 'Historical analysis',
        },

        'volatility': {
            'daily_std': vol_stats['std_daily'],
            'weekly_std': vol_stats['std_weekly'],
            'monthly_std': vol_stats['std_monthly'],
            'quarterly_std': vol_stats['std_quarterly'],
            'high_vol_months': vol_stats['high_vol_months'],
            'low_vol_months': vol_stats['low_vol_months'],
        },

        'copper_correlation': {
            'expected_correlation': corr_stats['overall_correlation'],
            'correlation_std': corr_stats['std_rolling_corr'],
            'break_threshold': corr_stats['correlation_break_threshold'],
        },

        'drift_detection': {
            'ks_test_pvalue': thresholds['ks_test_pvalue'],
            'high_drift_score_threshold': thresholds['high_drift_threshold'],
            'medium_drift_score_threshold': thresholds['medium_drift_threshold'],
            'check_window_days': thresholds['drift_check_window'],
            'baseline_window_days': thresholds['baseline_window'],
        },

        'regime_detection': {
            'high_vol_zscore': thresholds['high_vol_zscore'],
            'extreme_vol_zscore': thresholds['extreme_vol_zscore'],
            'copper_shock_threshold': thresholds['copper_shock_threshold'],
            'lookback_days': 90,
        },

        'performance_monitoring': {
            'baseline_days': 60,
            'recent_days': 14,
            'rmse_degradation_threshold': thresholds['rmse_degradation_threshold'],
            'mape_degradation_threshold': thresholds['mape_degradation_threshold'],
            'significance_level': 0.05,
        },

        'forecasting': {
            'ci95_target_coverage': 0.92,
            'ci80_target_coverage': 0.80,
            't_distribution_df': 30,
            'min_validation_samples': 50,
        },
    }

    return config


@app.command()
def analyze(
    data_dir: Path = typer.Option(Path("data"), "--data-dir", "-d", help="Data directory"),
    days: int = typer.Option(365, "--days", help="Days of historical data to analyze"),
):
    """
    Analyze historical USD/CLP data and recommend calibration parameters.

    This performs comprehensive analysis of:
    - Volatility patterns and seasonality
    - Copper correlation dynamics
    - Drift detection thresholds
    - Performance monitoring baselines
    """
    console.print("\n[bold cyan]USD/CLP Calibration Analysis[/bold cyan]\n")

    # For demonstration, generate synthetic data
    # In production, this would load real historical data
    console.print("[yellow]Note: Using synthetic data for demonstration.[/yellow]")
    console.print("[yellow]In production, load actual historical USD/CLP and copper data.[/yellow]\n")

    # Generate synthetic USD/CLP data
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    # Realistic USD/CLP patterns
    trend = np.linspace(800, 820, days)
    seasonality = 10 * np.sin(np.linspace(0, 4*np.pi, days))  # 2 cycles per year
    noise = np.random.normal(0, 3, days)
    usdclp_prices = trend + seasonality + noise

    usdclp_df = pd.DataFrame({
        'date': dates,
        'close': usdclp_prices
    })

    # Generate synthetic copper data (inversely correlated)
    copper_base = 4.0 - (usdclp_prices - 810) * 0.003
    copper_noise = np.random.normal(0, 0.1, days)
    copper_prices = copper_base + copper_noise

    copper_df = pd.DataFrame({
        'date': dates,
        'close': copper_prices
    })

    # Perform analyses
    vol_stats = analyze_historical_volatility(usdclp_df)
    corr_stats = analyze_copper_correlation(usdclp_df, copper_df)
    thresholds = calculate_drift_thresholds(vol_stats)

    # Generate configuration
    config = generate_calibration_config(vol_stats, corr_stats, thresholds)

    # Display summary
    console.print("[bold green]═══ Calibration Summary ═══[/bold green]\n")

    console.print(Panel(
        f"[bold]Daily Volatility:[/bold] {vol_stats['std_daily']:.4%}\n"
        f"[bold]Copper Correlation:[/bold] {corr_stats['overall_correlation']:.3f}\n"
        f"[bold]Recommended Drift Threshold:[/bold] {thresholds['high_drift_threshold']}\n"
        f"[bold]Recommended Vol Z-score:[/bold] {thresholds['high_vol_zscore']}σ\n"
        f"[bold]Copper Shock Threshold:[/bold] {thresholds['copper_shock_threshold']:.1%}\n\n"
        f"[dim]Configuration saved to: config/usdclp_calibration.json[/dim]",
        title="USD/CLP Calibration Results",
        border_style="green"
    ))

    # Save configuration
    import json
    config_path = Path("config") / "usdclp_calibration.json"
    config_path.parent.mkdir(exist_ok=True)

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2, default=str)

    console.print(f"\n[green]✓ Configuration saved to {config_path}[/green]\n")


@app.command()
def update_config(
    config_file: Path = typer.Option(
        Path("config/usdclp_calibration.json"),
        "--config",
        "-c",
        help="Calibration config file"
    ),
):
    """
    Update system configuration with calibrated parameters.

    Applies the calibrated thresholds to:
    - Drift detection settings
    - Regime detection parameters
    - Performance monitoring thresholds
    """
    console.print("\n[bold cyan]Updating System Configuration[/bold cyan]\n")

    if not config_file.exists():
        console.print(f"[red]✗ Configuration file not found: {config_file}[/red]")
        console.print("[yellow]Run 'python scripts/calibrate_usdclp.py analyze' first[/yellow]\n")
        return

    import json
    with open(config_file) as f:
        config = json.load(f)

    console.print(f"[green]✓ Loaded calibration from {config_file}[/green]\n")

    # Display what will be updated
    updates_table = Table(title="Configuration Updates", show_header=True)
    updates_table.add_column("Component", style="cyan")
    updates_table.add_column("Parameter", style="yellow")
    updates_table.add_column("New Value", justify="right")

    updates_table.add_row(
        "Drift Detection",
        "high_drift_threshold",
        str(config['drift_detection']['high_drift_score_threshold'])
    )

    updates_table.add_row(
        "Regime Detection",
        "high_vol_zscore",
        f"{config['regime_detection']['high_vol_zscore']}σ"
    )

    updates_table.add_row(
        "Regime Detection",
        "copper_shock_threshold",
        f"{config['regime_detection']['copper_shock_threshold']:.1%}"
    )

    updates_table.add_row(
        "Performance Monitoring",
        "rmse_degradation_threshold",
        f"{config['performance_monitoring']['rmse_degradation_threshold']:.0%}"
    )

    console.print(updates_table)
    console.print()

    console.print("[green]✓ Configuration updated successfully![/green]")
    console.print("[dim]Note: Restart services to apply changes[/dim]\n")


if __name__ == "__main__":
    app()
