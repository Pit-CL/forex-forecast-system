"""
Dashboard Utilities for MLOps CLI.

Helper functions para obtener datos y generar visualizaciones
para el dashboard de MLOps.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger
from rich.console import Console


def get_prediction_summary() -> list[dict]:
    """
    Get summary of prediction tracking.

    Returns:
        List of dicts with prediction stats per horizon.
    """
    from forex_core.config import get_settings

    settings = get_settings()
    storage_path = settings.data_dir / "predictions" / "predictions.parquet"

    if not storage_path.exists():
        return []

    try:
        df = pd.read_parquet(storage_path)

        summary = []
        for horizon in df["horizon"].unique():
            horizon_df = df[df["horizon"] == horizon]

            # Convert forecast_date to datetime if needed
            horizon_df = horizon_df.copy()
            horizon_df["forecast_date"] = pd.to_datetime(horizon_df["forecast_date"])

            cutoff_7d = datetime.now() - timedelta(days=7)
            cutoff_30d = datetime.now() - timedelta(days=30)

            summary.append(
                {
                    "horizon": horizon,
                    "total": len(horizon_df),
                    "last_7d": len(horizon_df[horizon_df["forecast_date"] >= cutoff_7d]),
                    "last_30d": len(horizon_df[horizon_df["forecast_date"] >= cutoff_30d]),
                    "latest_date": horizon_df["forecast_date"].max().strftime("%Y-%m-%d"),
                }
            )

        return sorted(summary, key=lambda x: x["horizon"])

    except Exception as e:
        logger.error(f"Failed to get prediction summary: {e}")
        return []


def get_drift_summary() -> list[dict]:
    """
    Get summary of drift status across horizons.

    Returns:
        List of dicts with drift summary per horizon.
    """
    from forex_core.config import get_settings
    from forex_core.mlops.drift_trends import DriftTrendAnalyzer

    settings = get_settings()
    storage_path = settings.data_dir / "drift_history" / "drift_history.parquet"

    if not storage_path.exists():
        return []

    try:
        analyzer = DriftTrendAnalyzer(storage_path=storage_path)
        df = pd.read_parquet(storage_path)

        summary = []
        for horizon in df["horizon"].unique():
            try:
                trend_report = analyzer.analyze_trend(horizon, lookback_days=90)

                # Determine status
                if trend_report.requires_action():
                    status = "⚠️ ACTION REQUIRED"
                elif trend_report.trend.value == "worsening":
                    status = "⚡ WORSENING"
                elif trend_report.trend.value == "improving":
                    status = "✓ IMPROVING"
                else:
                    status = "○ STABLE"

                summary.append(
                    {
                        "horizon": horizon,
                        "score": trend_report.current_score,
                        "trend": trend_report.trend.value.upper(),
                        "status": status,
                    }
                )

            except Exception as e:
                logger.warning(f"Failed to analyze drift for {horizon}: {e}")

        return sorted(summary, key=lambda x: x["horizon"])

    except Exception as e:
        logger.error(f"Failed to get drift summary: {e}")
        return []


def get_validation_summary() -> list[dict]:
    """
    Get summary of latest validation results.

    Returns:
        List of dicts with validation summary per horizon.
    """
    from forex_core.config import get_settings

    settings = get_settings()
    reports_dir = settings.data_dir / "validation_reports"

    if not reports_dir.exists():
        return []

    try:
        # Find latest summary for each horizon
        summary_files = sorted(
            reports_dir.glob("summary_*.parquet"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if not summary_files:
            return []

        # Group by horizon and get latest
        horizon_reports = {}
        for filepath in summary_files:
            df = pd.read_parquet(filepath)
            row = df.iloc[0]

            horizon = row["horizon"]
            if horizon not in horizon_reports:
                horizon_reports[horizon] = {
                    "horizon": horizon,
                    "rmse": row["avg_rmse"],
                    "mape": row["avg_mape"],
                    "ci95": row["avg_ci95_coverage"],
                    "acceptable": row.get("is_acceptable", False),
                }

        return sorted(horizon_reports.values(), key=lambda x: x["horizon"])

    except Exception as e:
        logger.error(f"Failed to get validation summary: {e}")
        return []


def get_alert_summary(days: int = 7) -> list[dict]:
    """
    Get summary of alert activity.

    Args:
        days: Days of history to analyze.

    Returns:
        List of dicts with alert summary per horizon.
    """
    logs_dir = Path("logs")

    if not logs_dir.exists():
        return []

    try:
        summary = []

        for horizon in ["7d", "15d", "30d", "90d"]:
            log_file = logs_dir / f"alerts_{horizon}.log"

            if not log_file.exists():
                continue

            # Parse log file
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Count decisions in last N days
            cutoff = datetime.now() - timedelta(days=days)

            total = 0
            sent = 0
            last_alert_date = None

            # Simple parsing (assumes log format from AlertManager)
            for block in content.split("=" * 60):
                if "ALERT EVALUATION" in block:
                    try:
                        # Extract timestamp
                        for line in block.split("\n"):
                            if line.startswith("Timestamp:"):
                                timestamp_str = line.split("Timestamp:")[1].strip()
                                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

                                if timestamp >= cutoff:
                                    total += 1

                                    if "SEND ALERT" in block:
                                        sent += 1
                                        if last_alert_date is None or timestamp > last_alert_date:
                                            last_alert_date = timestamp

                    except Exception:
                        continue

            summary.append(
                {
                    "horizon": horizon,
                    "total": total,
                    "sent": sent,
                    "no_alert": total - sent,
                    "last_alert": last_alert_date.strftime("%Y-%m-%d") if last_alert_date else None,
                }
            )

        return summary

    except Exception as e:
        logger.error(f"Failed to get alert summary: {e}")
        return []


def get_readiness_summary() -> Optional[dict]:
    """
    Get Chronos readiness summary.

    Returns:
        Dict with readiness score and level, or None.
    """
    try:
        from forex_core.config import get_settings
        from forex_core.mlops.readiness import ChronosReadinessChecker

        settings = get_settings()
        checker = ChronosReadinessChecker(data_dir=settings.data_dir)
        report = checker.assess()

        return {
            "score": report.score,
            "level": report.level.value,
            "recommendation": report.recommendation,
        }

    except Exception as e:
        logger.warning(f"Readiness check failed: {e}")
        return None


def get_drift_details(horizon: str, days: int) -> Optional[dict]:
    """
    Get detailed drift analysis for a horizon.

    Args:
        horizon: Horizon to analyze.
        days: Days of history.

    Returns:
        Dict with detailed drift data.
    """
    from forex_core.config import get_settings
    from forex_core.mlops.drift_trends import DriftTrendAnalyzer

    settings = get_settings()
    storage_path = settings.data_dir / "drift_history" / "drift_history.parquet"

    if not storage_path.exists():
        return None

    try:
        analyzer = DriftTrendAnalyzer(storage_path=storage_path)
        trend_report = analyzer.analyze_trend(horizon, lookback_days=days)
        history = analyzer.get_drift_history(horizon, days=30)

        # Prepare history for plotting
        history_list = []
        if not history.empty:
            history = history.sort_values("timestamp")
            for _, row in history.iterrows():
                history_list.append(
                    {
                        "date": pd.to_datetime(row["timestamp"]).strftime("%Y-%m-%d"),
                        "score": row["drift_score"],
                        "severity": row["severity"],
                    }
                )

        # Prepare test breakdown
        test_breakdown = []
        if not history.empty:
            for _, row in history.iterrows():
                test_breakdown.append(
                    {
                        "date": pd.to_datetime(row["timestamp"]).strftime("%Y-%m-%d"),
                        "ks": row.get("ks_drift", False),
                        "t": row.get("t_drift", False),
                        "levene": row.get("levene_drift", False),
                        "ljungbox": row.get("ljungbox_drift", False),
                        "score": row["drift_score"],
                    }
                )

        return {
            "current_score": trend_report.current_score,
            "avg_30d": trend_report.avg_score_30d,
            "avg_90d": trend_report.avg_score_90d,
            "trend": trend_report.trend.value.upper(),
            "consecutive_high": trend_report.consecutive_high,
            "recommendation": trend_report.recommendation,
            "history": history_list,
            "test_breakdown": test_breakdown,
        }

    except Exception as e:
        logger.error(f"Failed to get drift details: {e}")
        return None


def get_validation_details(horizon: str, limit: int) -> list[dict]:
    """
    Get detailed validation results for a horizon.

    Args:
        horizon: Horizon to analyze.
        limit: Max number of reports.

    Returns:
        List of validation report dicts.
    """
    from forex_core.config import get_settings

    settings = get_settings()
    reports_dir = settings.data_dir / "validation_reports"

    if not reports_dir.exists():
        return []

    try:
        # Find summary files for this horizon
        pattern = f"summary_validation_{horizon}_*.parquet"
        summary_files = sorted(
            reports_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True
        )

        results = []
        for filepath in summary_files[:limit]:
            df = pd.read_parquet(filepath)
            row = df.iloc[0]

            results.append(
                {
                    "timestamp": pd.to_datetime(row["timestamp"]).strftime("%Y-%m-%d %H:%M"),
                    "horizon": row["horizon"],
                    "mode": row["mode"],
                    "n_folds": row["n_folds"],
                    "avg_rmse": row["avg_rmse"],
                    "std_rmse": row["std_rmse"],
                    "avg_mae": row["avg_mae"],
                    "avg_mape": row["avg_mape"],
                    "avg_ci95_coverage": row["avg_ci95_coverage"],
                    "avg_bias": row["avg_bias"],
                    "is_acceptable": row.get("is_acceptable", False),
                }
            )

        return results

    except Exception as e:
        logger.error(f"Failed to get validation details: {e}")
        return []


def get_alert_details(
    horizon: Optional[str], days: int, severity: Optional[str]
) -> Optional[dict]:
    """
    Get detailed alert history.

    Args:
        horizon: Filter by horizon (optional).
        days: Days of history.
        severity: Filter by severity (optional).

    Returns:
        Dict with alert details.
    """
    logs_dir = Path("logs")

    if not logs_dir.exists():
        return None

    try:
        horizons = [horizon] if horizon else ["7d", "15d", "30d", "90d"]

        frequency = []
        recent = []

        cutoff = datetime.now() - timedelta(days=days)

        for h in horizons:
            log_file = logs_dir / f"alerts_{h}.log"

            if not log_file.exists():
                continue

            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()

            total_checks = 0
            alerts_sent = 0
            severities = []

            for block in content.split("=" * 60):
                if "ALERT EVALUATION" in block:
                    try:
                        timestamp = None
                        decision = None
                        sev = None
                        reason = None

                        for line in block.split("\n"):
                            if line.startswith("Timestamp:"):
                                timestamp_str = line.split("Timestamp:")[1].strip()
                                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                            elif line.startswith("Decision:"):
                                decision = line.split("Decision:")[1].strip()
                            elif line.startswith("Severity:"):
                                sev = line.split("Severity:")[1].strip()
                            elif line.startswith("Reason:"):
                                reason = line.split("Reason:")[1].strip()

                        if timestamp and timestamp >= cutoff:
                            total_checks += 1

                            if decision and "SEND ALERT" in decision:
                                alerts_sent += 1

                                if sev:
                                    severities.append(sev)

                                # Add to recent if matches severity filter
                                if not severity or (sev and severity.lower() in sev.lower()):
                                    recent.append(
                                        {
                                            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M"),
                                            "horizon": h,
                                            "severity": sev if sev else "UNKNOWN",
                                            "reason": reason if reason else "No reason",
                                        }
                                    )

                    except Exception:
                        continue

            # Calculate average severity
            avg_sev = "N/A"
            if severities:
                severity_counts = {}
                for s in severities:
                    severity_counts[s] = severity_counts.get(s, 0) + 1

                avg_sev = max(severity_counts, key=severity_counts.get)

            frequency.append(
                {
                    "horizon": h,
                    "total_checks": total_checks,
                    "alerts_sent": alerts_sent,
                    "avg_severity": avg_sev,
                }
            )

        # Sort recent by timestamp (newest first)
        recent.sort(key=lambda x: x["timestamp"], reverse=True)

        return {"frequency": frequency, "recent": recent}

    except Exception as e:
        logger.error(f"Failed to get alert details: {e}")
        return None


def plot_drift_trend(history: list[dict], console: Console):
    """
    Plot drift trend as ASCII chart.

    Args:
        history: List of drift history dicts.
        console: Rich console for output.
    """
    if not history:
        console.print("[dim]No data to plot[/dim]")
        return

    # Extract scores
    scores = [h["score"] for h in history]
    dates = [h["date"] for h in history]

    # Simple ASCII sparkline
    min_score = min(scores)
    max_score = max(scores)
    range_score = max_score - min_score if max_score > min_score else 1

    height = 10
    width = min(len(scores), 60)

    # Sample points if too many
    if len(scores) > width:
        step = len(scores) // width
        scores = scores[::step]
        dates = dates[::step]

    # Normalize scores to height
    normalized = [(s - min_score) / range_score * (height - 1) for s in scores]

    # Build chart
    for row in range(height - 1, -1, -1):
        line = ""
        for norm in normalized:
            if round(norm) == row:
                line += "●"
            elif norm > row:
                line += "│"
            else:
                line += " "

        # Add y-axis label
        score_at_row = min_score + (row / (height - 1)) * range_score
        console.print(f"{score_at_row:5.1f} │ {line}")

    # X-axis
    console.print("      " + "─" * len(normalized))
    console.print(f"      {dates[0]}  →  {dates[-1]}")


__all__ = [
    "get_prediction_summary",
    "get_drift_summary",
    "get_validation_summary",
    "get_alert_summary",
    "get_readiness_summary",
    "get_drift_details",
    "get_validation_details",
    "get_alert_details",
    "plot_drift_trend",
]
