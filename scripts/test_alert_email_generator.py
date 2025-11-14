#!/usr/bin/env python3
"""
Test script for Alert Email Generator.

Demonstrates how to generate both market shock and model performance alert emails
with sample data.

Usage:
    python scripts/test_alert_email_generator.py --type market
    python scripts/test_alert_email_generator.py --type model
    python scripts/test_alert_email_generator.py --type both
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forex_core.alerts import (
    Alert,
    AlertSeverity,
    AlertType,
    ModelAlert,
    ModelAlertSeverity,
    ModelAlertType,
    generate_market_shock_email,
    generate_model_performance_email,
)


def create_sample_market_shock_alerts():
    """Create sample market shock alerts for testing."""
    alerts = [
        Alert(
            alert_type=AlertType.TREND_REVERSAL,
            severity=AlertSeverity.CRITICAL,
            timestamp=datetime.now(),
            message="Cambio diario significativo en USD/CLP: alza de 2.5% a $958.30",
            metrics={
                "daily_change_pct": 2.5,
                "current_rate": 958.30,
                "previous_rate": 935.10,
            },
            recommendation="Revisar drivers del movimiento y actualizar expectativas de corto plazo",
        ),
        Alert(
            alert_type=AlertType.COPPER_SHOCK,
            severity=AlertSeverity.WARNING,
            timestamp=datetime.now(),
            message="Caída sostenida del cobre (7 días): 8.5% ($4.35 → $3.98)",
            metrics={
                "weekly_change_pct": -8.5,
                "week_start_price": 4.35,
                "week_end_price": 3.98,
            },
            recommendation="Monitorear impacto acumulado en exportaciones chilenas",
        ),
        Alert(
            alert_type=AlertType.VIX_SPIKE,
            severity=AlertSeverity.WARNING,
            timestamp=datetime.now(),
            message="Estrés de mercado moderado: VIX en 32.5 (umbral 30)",
            metrics={
                "current_vix": 32.5,
                "threshold": 30.0,
                "stress_level": "moderado",
            },
            recommendation=None,
        ),
        Alert(
            alert_type=AlertType.DXY_EXTREME,
            severity=AlertSeverity.INFO,
            timestamp=datetime.now(),
            message="Dólar fuerte: DXY en 105.8 (umbral 105)",
            metrics={
                "current_dxy": 105.8,
                "threshold": 105.0,
                "distance_from_threshold": 0.8,
            },
            recommendation=None,
        ),
    ]
    return alerts


def create_sample_model_performance_alerts():
    """Create sample model performance alerts for testing."""
    alerts = [
        ModelAlert(
            alert_type=ModelAlertType.DEGRADATION_CRITICAL,
            severity=ModelAlertSeverity.CRITICAL,
            model_name="xgboost_7d",
            horizon="7d",
            message="CRITICAL: xgboost_7d (7d) - RMSE degraded by 35.2% vs baseline",
            current_metrics={
                "rmse": 13.8,
                "mae": 10.5,
                "mape": 1.2,
                "directional_accuracy": 0.52,
            },
            baseline_metrics={
                "rmse": 10.2,
                "mae": 7.8,
                "mape": 0.9,
                "directional_accuracy": 0.62,
            },
            degradation_pct={
                "rmse": 0.352,
                "mae": 0.346,
                "mape": 0.333,
                "directional_accuracy": 0.161,
            },
            recommendations=[
                "IMMEDIATE: Stop using this model for production forecasts",
                "Investigate root cause (data drift, regime change, outliers)",
                "Trigger emergency re-training with recent data",
                "Consider using ensemble fallback or previous model version",
                "Review last 7 days of predictions for patterns",
            ],
        ),
        ModelAlert(
            alert_type=ModelAlertType.DIRECTIONAL_ACCURACY_LOW,
            severity=ModelAlertSeverity.WARNING,
            model_name="xgboost_7d",
            horizon="7d",
            message="Directional accuracy below threshold: 52.0% < 55.0%",
            current_metrics={
                "rmse": 13.8,
                "mae": 10.5,
                "mape": 1.2,
                "directional_accuracy": 0.52,
            },
            baseline_metrics={
                "rmse": 10.2,
                "mae": 7.8,
                "mape": 0.9,
                "directional_accuracy": 0.62,
            },
            recommendations=[
                "Model not reliably predicting direction",
                "Review feature importance - trend indicators may be weak",
                "Check if recent period has high volatility/noise",
                "Consider adding momentum/trend features",
            ],
        ),
        ModelAlert(
            alert_type=ModelAlertType.RETRAINING_SUCCESS,
            severity=ModelAlertSeverity.INFO,
            model_name="sarimax_30d",
            horizon="30d",
            message="Re-training completed successfully for sarimax_30d (30d) (RMSE improved by 8.5%)",
            current_metrics={
                "rmse": 18.5,
                "mae": 14.2,
                "mape": 1.8,
                "directional_accuracy": 0.65,
            },
            baseline_metrics={
                "rmse": 20.2,
                "mae": 15.8,
                "mape": 2.0,
                "directional_accuracy": 0.61,
            },
            details={
                "hyperparameters": {"order": "(2,1,2)", "seasonal_order": "(1,1,1,7)"},
                "training_time_seconds": 342.5,
                "timestamp": datetime.now().isoformat(),
            },
            recommendations=[
                "Update baseline metrics with new performance",
                "Monitor first 3-5 forecasts with new model",
                "Compare predictions with previous model version",
            ],
        ),
    ]
    return alerts


def create_sample_market_data():
    """Create sample market data snapshot."""
    return {
        "usdclp": 958.30,
        "copper_price": 3.98,
        "dxy": 105.8,
        "vix": 32.5,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Test alert email generator with sample data"
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=["market", "model", "both"],
        default="both",
        help="Type of alert to generate",
    )
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Skip PDF generation (only HTML)",
    )
    args = parser.parse_args()

    output_dir = Path(__file__).parent.parent / "output" / "alerts"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Alert Email Generator Test")
    print("=" * 70)

    # Market shock alert
    if args.type in ["market", "both"]:
        print("\n1. Generating Market Shock Alert Email...")
        print("-" * 70)

        alerts = create_sample_market_shock_alerts()
        market_data = create_sample_market_data()

        print(f"   - Alerts: {len(alerts)} total")
        print(f"     - CRITICAL: {sum(1 for a in alerts if a.severity == AlertSeverity.CRITICAL)}")
        print(f"     - WARNING: {sum(1 for a in alerts if a.severity == AlertSeverity.WARNING)}")
        print(f"     - INFO: {sum(1 for a in alerts if a.severity == AlertSeverity.INFO)}")

        html, pdf_bytes = generate_market_shock_email(
            alerts, market_data, generate_pdf=not args.no_pdf
        )

        # Save HTML
        html_path = output_dir / "market_shock_alert.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"   ✓ HTML saved: {html_path}")

        # Save PDF
        if pdf_bytes:
            pdf_path = output_dir / "market_shock_alert.pdf"
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
            pdf_size = len(pdf_bytes) / 1024
            print(f"   ✓ PDF saved: {pdf_path} ({pdf_size:.1f} KB)")
        elif not args.no_pdf:
            print("   ⚠ PDF generation skipped (WeasyPrint not available)")

    # Model performance alert
    if args.type in ["model", "both"]:
        print("\n2. Generating Model Performance Alert Email...")
        print("-" * 70)

        alerts = create_sample_model_performance_alerts()

        print(f"   - Alerts: {len(alerts)} total")
        print(f"     - CRITICAL: {sum(1 for a in alerts if a.severity == ModelAlertSeverity.CRITICAL)}")
        print(f"     - WARNING: {sum(1 for a in alerts if a.severity == ModelAlertSeverity.WARNING)}")
        print(f"     - INFO: {sum(1 for a in alerts if a.severity == ModelAlertSeverity.INFO)}")

        html, pdf_bytes = generate_model_performance_email(
            alerts, generate_pdf=not args.no_pdf
        )

        # Save HTML
        html_path = output_dir / "model_performance_alert.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"   ✓ HTML saved: {html_path}")

        # Save PDF
        if pdf_bytes:
            pdf_path = output_dir / "model_performance_alert.pdf"
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
            pdf_size = len(pdf_bytes) / 1024
            print(f"   ✓ PDF saved: {pdf_path} ({pdf_size:.1f} KB)")
        elif not args.no_pdf:
            print("   ⚠ PDF generation skipped (WeasyPrint not available)")

    print("\n" + "=" * 70)
    print("✅ Alert email generation completed successfully")
    print(f"\nOutput directory: {output_dir}")
    print("\nNext steps:")
    print("  1. Open HTML files in browser to review formatting")
    print("  2. Check PDF files for proper layout (2 pages max)")
    print("  3. Integrate with send_alert_email.py for dispatch")


if __name__ == "__main__":
    main()
