"""
Alert Email Generator for USD/CLP Forecasting System.

Generates HTML emails and PDF reports for two types of alerts:
1. Market Shock Alerts (from MarketShockDetector)
2. Model Performance Alerts (from ModelPerformanceMonitor)

This module reuses the existing HTML/CSS format from test_email_and_pdf.py
to ensure visual consistency across all system communications.

Key Features:
- Short format PDFs (2 pages max, not 5 like forecast reports)
- Reuses existing CSS styling and section structure
- WeasyPrint for PDF generation
- Severity-based color coding
- Clean, simple template generation (no template engine)

Example:
    >>> from pathlib import Path
    >>> from market_shock_detector import MarketShockDetector, Alert
    >>> from alert_email_generator import generate_market_shock_email
    >>>
    >>> # Market shock alert
    >>> alerts = [...]  # From MarketShockDetector
    >>> market_data = {...}  # Current market snapshot
    >>> html, pdf_bytes = generate_market_shock_email(alerts, market_data)
    >>>
    >>> # Model performance alert
    >>> from model_performance_alerts import ModelAlert
    >>> alerts = [...]  # From ModelPerformanceMonitor
    >>> html, pdf_bytes = generate_model_performance_email(alerts)
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

try:
    from weasyprint import HTML

    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False
    logger.warning("WeasyPrint not available - PDF generation disabled")


# Common CSS reused from test_email_and_pdf.py
COMMON_CSS = """
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
        background-color: #f5f5f5;
        color: #333;
    }
    .header {
        background: linear-gradient(135deg, #004f71 0%, #003a54 100%);
        color: white;
        padding: 30px;
        border-radius: 10px;
        margin-bottom: 30px;
        text-align: center;
    }
    .header h1 {
        margin: 0;
        font-size: 24px;
    }
    .header .date {
        margin-top: 5px;
        opacity: 0.9;
        font-size: 14px;
    }
    .section {
        background: white;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        overflow: hidden;
    }
    .section-header {
        background: #f8f9fa;
        padding: 15px 20px;
        border-bottom: 1px solid #e9ecef;
    }
    .section-header h3 {
        margin: 0;
        font-size: 16px;
        color: #333;
    }
    .section-content {
        padding: 20px;
    }
    .metric {
        padding: 15px;
        background: #f8f9fa;
        border-radius: 6px;
        border-left: 4px solid #004f71;
        margin: 10px 0;
    }
    .metric-label {
        font-size: 12px;
        color: #6c757d;
        margin-bottom: 5px;
    }
    .metric-value {
        font-size: 22px;
        font-weight: bold;
        color: #333;
    }
    .metric-value.positive { color: #28a745; }
    .metric-value.negative { color: #dc3545; }
    .alert-badge {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: bold;
        margin-right: 8px;
    }
    .alert-badge.critical {
        background: #dc3545;
        color: white;
    }
    .alert-badge.warning {
        background: #ffc107;
        color: #333;
    }
    .alert-badge.info {
        background: #17a2b8;
        color: white;
    }
    .alert-item {
        padding: 15px;
        background: #f8f9fa;
        border-radius: 6px;
        margin: 10px 0;
        border-left: 4px solid #004f71;
    }
    .alert-item.critical {
        border-left-color: #dc3545;
        background: #fff5f5;
    }
    .alert-item.warning {
        border-left-color: #ffc107;
        background: #fffef5;
    }
    .alert-item.info {
        border-left-color: #17a2b8;
        background: #f5fcff;
    }
    .alert-message {
        font-weight: bold;
        margin-bottom: 10px;
        font-size: 14px;
    }
    .alert-metrics {
        font-size: 12px;
        color: #6c757d;
        margin: 8px 0;
    }
    .alert-recommendation {
        font-size: 13px;
        color: #333;
        margin-top: 10px;
        padding: 10px;
        background: white;
        border-radius: 4px;
        font-style: italic;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
    }
    th, td {
        padding: 12px;
        text-align: left;
        border-bottom: 1px solid #e9ecef;
    }
    th {
        background-color: #004f71;
        color: white;
        font-weight: 600;
        font-size: 13px;
    }
    .footer {
        margin-top: 30px;
        padding: 20px;
        background: white;
        border-radius: 8px;
        text-align: center;
        font-size: 11px;
        color: #6c757d;
    }
    .recommendations-list {
        list-style: decimal;
        padding-left: 20px;
        margin: 10px 0;
    }
    .recommendations-list li {
        margin: 8px 0;
        line-height: 1.6;
    }
"""


def generate_market_shock_email(
    alerts: List[Any],
    market_data: Dict[str, Any],
    generate_pdf: bool = True,
) -> Tuple[str, Optional[bytes]]:
    """
    Generate market shock alert email with HTML and PDF.

    Args:
        alerts: List of Alert objects from MarketShockDetector
        market_data: Dict with current market snapshot:
            - usdclp: Current USD/CLP rate
            - copper_price: Current copper price
            - dxy: Current DXY index
            - vix: Current VIX level
            - timestamp: Data timestamp
        generate_pdf: Whether to generate PDF (default True)

    Returns:
        Tuple of (html_string, pdf_bytes). pdf_bytes is None if generate_pdf=False
        or WeasyPrint unavailable.

    Example:
        >>> alerts = detector.detect_all(data)
        >>> market_data = {
        ...     "usdclp": 954.20,
        ...     "copper_price": 4.25,
        ...     "dxy": 104.2,
        ...     "vix": 15.3,
        ...     "timestamp": "2025-01-14 18:00"
        ... }
        >>> html, pdf = generate_market_shock_email(alerts, market_data)
    """
    if not alerts:
        logger.warning("No alerts provided for market shock email")
        return "", None

    # Get alert summary
    critical_count = sum(1 for a in alerts if a.severity.value.upper() == "CRITICAL")
    warning_count = sum(1 for a in alerts if a.severity.value.upper() == "WARNING")
    info_count = sum(1 for a in alerts if a.severity.value.upper() == "INFO")

    # Determine overall severity
    if critical_count > 0:
        overall_severity = "CRÍTICO"
        header_emoji = "🚨"
    elif warning_count > 0:
        overall_severity = "ADVERTENCIA"
        header_emoji = "⚠️"
    else:
        overall_severity = "INFORMATIVO"
        header_emoji = "ℹ️"

    # Get primary alert type
    primary_alert_type = alerts[0].alert_type.value.replace("_", " ").title()

    # Current timestamp
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Build HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Alerta de Mercado - USD/CLP - {now}</title>
<style>
{COMMON_CSS}
</style>
</head>
<body>
    <div class="header">
        <h1>{header_emoji} ALERTA: {primary_alert_type}</h1>
        <div class="date">{now} (Chile)</div>
        <div class="date">Severidad: {overall_severity}</div>
    </div>

    <div class="section">
        <div class="section-header">
            <h3>📊 Snapshot de Mercado</h3>
        </div>
        <div class="section-content">
            <table>
                <thead>
                    <tr>
                        <th>Indicador</th>
                        <th>Valor Actual</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>USD/CLP</strong></td>
                        <td>${market_data.get('usdclp', 'N/A'):.2f}</td>
                    </tr>
                    <tr>
                        <td><strong>Copper (HG=F)</strong></td>
                        <td>${market_data.get('copper_price', 'N/A'):.2f}/lb</td>
                    </tr>
                    <tr>
                        <td><strong>DXY</strong></td>
                        <td>{market_data.get('dxy', 'N/A'):.2f}</td>
                    </tr>
                    <tr>
                        <td><strong>VIX</strong></td>
                        <td>{market_data.get('vix', 'N/A'):.1f}</td>
                    </tr>
                </tbody>
            </table>
            <p style="font-size: 11px; color: #6c757d; margin-top: 10px;">
                Datos actualizados: {market_data.get('timestamp', now)}
            </p>
        </div>
    </div>

    <div class="section">
        <div class="section-header">
            <h3>🔔 Alertas Detectadas ({len(alerts)} total)</h3>
        </div>
        <div class="section-content">
            <p style="margin-bottom: 15px;">
                <span class="alert-badge critical">{critical_count} CRÍTICAS</span>
                <span class="alert-badge warning">{warning_count} ADVERTENCIAS</span>
                <span class="alert-badge info">{info_count} INFO</span>
            </p>
"""

    # Add alerts (group by severity)
    for severity_name in ["CRITICAL", "WARNING", "INFO"]:
        severity_alerts = [
            a for a in alerts if a.severity.value.upper() == severity_name
        ]

        if severity_alerts:
            severity_class = severity_name.lower()
            html += f'\n            <h4 style="color: #333; margin-top: 20px;">{severity_name}</h4>\n'

            for alert in severity_alerts:
                html += f"""
            <div class="alert-item {severity_class}">
                <div class="alert-message">{alert.message}</div>
"""

                # Add metrics if available
                if hasattr(alert, "metrics") and alert.metrics:
                    html += '                <div class="alert-metrics">\n'
                    for key, value in alert.metrics.items():
                        if isinstance(value, float):
                            html += f"                    <strong>{key}:</strong> {value:.2f}<br>\n"
                        else:
                            html += f"                    <strong>{key}:</strong> {value}<br>\n"
                    html += "                </div>\n"

                # Add recommendation if available
                if hasattr(alert, "recommendation") and alert.recommendation:
                    html += f"""
                <div class="alert-recommendation">
                    💡 {alert.recommendation}
                </div>
"""

                html += "            </div>\n"

    html += """        </div>
    </div>
"""

    # Recommendations section
    critical_alerts_with_recs = [
        a for a in alerts if a.severity.value.upper() == "CRITICAL" and hasattr(a, "recommendation") and a.recommendation
    ]

    if critical_alerts_with_recs:
        html += """
    <div class="section">
        <div class="section-header">
            <h3>💡 Recomendaciones Prioritarias</h3>
        </div>
        <div class="section-content">
            <ol class="recommendations-list">
"""
        for alert in critical_alerts_with_recs:
            html += f"                <li>{alert.recommendation}</li>\n"

        html += """            </ol>
            <p style="font-size: 12px; color: #6c757d; margin-top: 15px;">
                <strong>Acción recomendada:</strong> Revisar drivers del movimiento y actualizar expectativas de pronóstico si es necesario.
            </p>
        </div>
    </div>
"""

    # Footer
    html += f"""
    <div class="footer">
        <strong>USD/CLP Forecasting System - Alert System</strong><br>
        Generado automáticamente el {now} (Chile)<br>
        <em>Este es un sistema de alertas automático basado en umbrales configurados.</em><br>
        <em>Evalúe la situación con su equipo antes de tomar decisiones.</em>
    </div>
</body>
</html>
"""

    # Generate PDF
    pdf_bytes = None
    if generate_pdf and WEASYPRINT_AVAILABLE:
        try:
            pdf_html = _generate_market_shock_pdf_html(alerts, market_data, now)
            pdf_bytes = HTML(string=pdf_html).write_pdf()
            logger.info(f"Market shock alert PDF generated ({len(pdf_bytes)} bytes)")
        except Exception as e:
            logger.error(f"Failed to generate market shock PDF: {e}")

    return html, pdf_bytes


def generate_model_performance_email(
    alerts: List[Any],
    generate_pdf: bool = True,
) -> Tuple[str, Optional[bytes]]:
    """
    Generate model performance alert email with HTML and PDF.

    Args:
        alerts: List of ModelAlert objects from ModelPerformanceMonitor
        generate_pdf: Whether to generate PDF (default True)

    Returns:
        Tuple of (html_string, pdf_bytes). pdf_bytes is None if generate_pdf=False
        or WeasyPrint unavailable.

    Example:
        >>> from model_performance_alerts import ModelPerformanceMonitor
        >>> monitor = ModelPerformanceMonitor()
        >>> alerts = monitor.check_degradation("xgboost_7d", metrics, "7d")
        >>> html, pdf = generate_model_performance_email(alerts)
    """
    if not alerts:
        logger.warning("No alerts provided for model performance email")
        return "", None

    # Get alert summary
    critical_count = sum(1 for a in alerts if a.severity.value == "critical")
    warning_count = sum(1 for a in alerts if a.severity.value == "warning")
    info_count = sum(1 for a in alerts if a.severity.value == "info")

    # Determine overall severity
    if critical_count > 0:
        overall_severity = "CRÍTICO"
        header_emoji = "🚨"
    elif warning_count > 0:
        overall_severity = "ADVERTENCIA"
        header_emoji = "⚠️"
    else:
        overall_severity = "INFORMATIVO"
        header_emoji = "✅"

    # Get model name from first alert
    model_name = alerts[0].model_name if hasattr(alerts[0], "model_name") else "Unknown Model"
    horizon = alerts[0].horizon if hasattr(alerts[0], "horizon") else ""

    # Current timestamp
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Build HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Alerta de Performance - {model_name} - {now}</title>
<style>
{COMMON_CSS}
</style>
</head>
<body>
    <div class="header">
        <h1>{header_emoji} ALERTA: Performance del Modelo</h1>
        <div class="date">{now} (Chile)</div>
        <div class="date">Modelo: {model_name} ({horizon})</div>
        <div class="date">Severidad: {overall_severity}</div>
    </div>

    <div class="section">
        <div class="section-header">
            <h3>📊 Resumen de Alertas</h3>
        </div>
        <div class="section-content">
            <p style="margin-bottom: 15px;">
                <span class="alert-badge critical">{critical_count} CRÍTICAS</span>
                <span class="alert-badge warning">{warning_count} ADVERTENCIAS</span>
                <span class="alert-badge info">{info_count} INFO</span>
            </p>
        </div>
    </div>
"""

    # Add alerts grouped by severity
    for severity_name, severity_value in [
        ("CRÍTICAS", "critical"),
        ("ADVERTENCIAS", "warning"),
        ("INFORMACIÓN", "info"),
    ]:
        severity_alerts = [a for a in alerts if a.severity.value == severity_value]

        if severity_alerts:
            html += f"""
    <div class="section">
        <div class="section-header">
            <h3>🔔 Alertas {severity_name} ({len(severity_alerts)})</h3>
        </div>
        <div class="section-content">
"""

            for alert in severity_alerts:
                alert_class = severity_value
                html += f"""
            <div class="alert-item {alert_class}">
                <div class="alert-message">{alert.message}</div>
"""

                # Add current vs baseline metrics comparison if available
                if (
                    hasattr(alert, "current_metrics")
                    and alert.current_metrics
                    and hasattr(alert, "baseline_metrics")
                    and alert.baseline_metrics
                ):
                    html += """
                <table style="margin-top: 15px; font-size: 12px;">
                    <thead>
                        <tr>
                            <th>Métrica</th>
                            <th>Actual</th>
                            <th>Baseline</th>
                            <th>Cambio</th>
                        </tr>
                    </thead>
                    <tbody>
"""

                    for metric in ["rmse", "mae", "mape", "directional_accuracy"]:
                        if metric in alert.current_metrics and metric in alert.baseline_metrics:
                            current = alert.current_metrics[metric]
                            baseline = alert.baseline_metrics[metric]

                            # Calculate change
                            if metric == "directional_accuracy":
                                change = current - baseline
                                change_str = f"{change:+.2%}"
                                change_class = "positive" if change > 0 else "negative"
                            else:
                                change = ((current - baseline) / baseline) * 100 if baseline > 0 else 0
                                change_str = f"{change:+.1f}%"
                                change_class = "negative" if change > 0 else "positive"

                            metric_display = metric.upper().replace("_", " ")
                            html += f"""
                        <tr>
                            <td><strong>{metric_display}</strong></td>
                            <td>{current:.2f}</td>
                            <td>{baseline:.2f}</td>
                            <td class="{change_class}">{change_str}</td>
                        </tr>
"""

                    html += """
                    </tbody>
                </table>
"""

                # Add recommendations if available
                if hasattr(alert, "recommendations") and alert.recommendations:
                    html += """
                <div style="margin-top: 15px;">
                    <strong style="font-size: 13px;">Recomendaciones:</strong>
                    <ol class="recommendations-list" style="font-size: 12px;">
"""
                    for rec in alert.recommendations[:3]:  # Show top 3
                        html += f"                        <li>{rec}</li>\n"
                    html += """                    </ol>
                </div>
"""

                html += "            </div>\n"

            html += """        </div>
    </div>
"""

    # Footer
    html += f"""
    <div class="footer">
        <strong>USD/CLP Forecasting System - MLOps Performance Monitor</strong><br>
        Generado automáticamente el {now} (Chile)<br>
        <em>Este reporte monitorea la salud de los modelos de pronóstico.</em><br>
        <em>Revise las recomendaciones y tome acción según severidad.</em>
    </div>
</body>
</html>
"""

    # Generate PDF
    pdf_bytes = None
    if generate_pdf and WEASYPRINT_AVAILABLE:
        try:
            pdf_html = _generate_model_performance_pdf_html(alerts, now)
            pdf_bytes = HTML(string=pdf_html).write_pdf()
            logger.info(f"Model performance alert PDF generated ({len(pdf_bytes)} bytes)")
        except Exception as e:
            logger.error(f"Failed to generate model performance PDF: {e}")

    return html, pdf_bytes


def _generate_market_shock_pdf_html(
    alerts: List[Any], market_data: Dict[str, Any], timestamp: str
) -> str:
    """
    Generate PDF-specific HTML for market shock alerts (2 pages max).

    Uses Letter size pages with proper margins for printing.
    """
    critical_count = sum(1 for a in alerts if a.severity.value.upper() == "CRITICAL")
    warning_count = sum(1 for a in alerts if a.severity.value.upper() == "WARNING")
    info_count = sum(1 for a in alerts if a.severity.value.upper() == "INFO")

    if critical_count > 0:
        overall_severity = "CRÍTICO"
    elif warning_count > 0:
        overall_severity = "ADVERTENCIA"
    else:
        overall_severity = "INFORMATIVO"

    primary_alert_type = alerts[0].alert_type.value.replace("_", " ").title()

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{
            size: Letter;
            margin: 2cm;
            @bottom-right {{
                content: "Página " counter(page);
                font-size: 10px;
                color: #666;
            }}
        }}
        body {{
            font-family: Arial, sans-serif;
            color: #333;
            line-height: 1.6;
        }}
        .header {{
            background: #dc3545;
            color: white;
            padding: 30px;
            text-align: center;
            margin: -2cm -2cm 30px -2cm;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .header .subtitle {{
            margin-top: 10px;
            font-size: 14px;
        }}
        .section {{
            margin-bottom: 25px;
            page-break-inside: avoid;
        }}
        .section h2 {{
            color: #004f71;
            border-bottom: 2px solid #004f71;
            padding-bottom: 10px;
            font-size: 18px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 12px;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }}
        th {{
            background-color: #004f71;
            color: white;
        }}
        .alert-box {{
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
            border-left: 4px solid #004f71;
            background: #f8f9fa;
        }}
        .alert-box.critical {{
            border-left-color: #dc3545;
            background: #fff5f5;
        }}
        .alert-box.warning {{
            border-left-color: #ffc107;
            background: #fffef5;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid #e9ecef;
            text-align: center;
            font-size: 10px;
            color: #6c757d;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚨 Alerta de Mercado: {primary_alert_type}</h1>
        <div class="subtitle">{timestamp} (Chile) | Severidad: {overall_severity}</div>
    </div>

    <div class="section">
        <h2>Snapshot de Mercado</h2>
        <table>
            <tr>
                <td><strong>USD/CLP</strong></td>
                <td>${market_data.get('usdclp', 'N/A'):.2f}</td>
            </tr>
            <tr>
                <td><strong>Copper (HG=F)</strong></td>
                <td>${market_data.get('copper_price', 'N/A'):.2f}/lb</td>
            </tr>
            <tr>
                <td><strong>DXY</strong></td>
                <td>{market_data.get('dxy', 'N/A'):.2f}</td>
            </tr>
            <tr>
                <td><strong>VIX</strong></td>
                <td>{market_data.get('vix', 'N/A'):.1f}</td>
            </tr>
        </table>
    </div>

    <div class="section">
        <h2>Alertas Detectadas ({critical_count} críticas, {warning_count} advertencias, {info_count} info)</h2>
"""

    # Add alerts
    for alert in alerts:
        severity_class = alert.severity.value.lower()
        html += f"""
        <div class="alert-box {severity_class}">
            <strong>{alert.severity.value.upper()}:</strong> {alert.message}
"""
        if hasattr(alert, "recommendation") and alert.recommendation:
            html += f"            <br><em>💡 {alert.recommendation}</em>\n"

        html += "        </div>\n"

    html += f"""
    </div>

    <div class="footer">
        <strong>USD/CLP Forecasting System - Alert System</strong><br>
        Generado: {timestamp}<br>
        Sistema automático de alertas
    </div>
</body>
</html>
"""

    return html


def _generate_model_performance_pdf_html(alerts: List[Any], timestamp: str) -> str:
    """
    Generate PDF-specific HTML for model performance alerts (2 pages max).

    Uses Letter size pages with proper margins for printing.
    """
    critical_count = sum(1 for a in alerts if a.severity.value == "critical")
    warning_count = sum(1 for a in alerts if a.severity.value == "warning")
    info_count = sum(1 for a in alerts if a.severity.value == "info")

    if critical_count > 0:
        overall_severity = "CRÍTICO"
        header_color = "#dc3545"
    elif warning_count > 0:
        overall_severity = "ADVERTENCIA"
        header_color = "#ffc107"
    else:
        overall_severity = "INFORMATIVO"
        header_color = "#28a745"

    model_name = alerts[0].model_name if hasattr(alerts[0], "model_name") else "Unknown"
    horizon = alerts[0].horizon if hasattr(alerts[0], "horizon") else ""

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{
            size: Letter;
            margin: 2cm;
            @bottom-right {{
                content: "Página " counter(page);
                font-size: 10px;
                color: #666;
            }}
        }}
        body {{
            font-family: Arial, sans-serif;
            color: #333;
            line-height: 1.6;
        }}
        .header {{
            background: {header_color};
            color: white;
            padding: 30px;
            text-align: center;
            margin: -2cm -2cm 30px -2cm;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .header .subtitle {{
            margin-top: 10px;
            font-size: 14px;
        }}
        .section {{
            margin-bottom: 25px;
            page-break-inside: avoid;
        }}
        .section h2 {{
            color: #004f71;
            border-bottom: 2px solid #004f71;
            padding-bottom: 10px;
            font-size: 18px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 12px;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }}
        th {{
            background-color: #004f71;
            color: white;
        }}
        .alert-box {{
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
            border-left: 4px solid #004f71;
            background: #f8f9fa;
            font-size: 12px;
        }}
        .alert-box.critical {{
            border-left-color: #dc3545;
            background: #fff5f5;
        }}
        .alert-box.warning {{
            border-left-color: #ffc107;
            background: #fffef5;
        }}
        .recommendations {{
            list-style: decimal;
            padding-left: 20px;
            margin: 10px 0;
            font-size: 11px;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid #e9ecef;
            text-align: center;
            font-size: 10px;
            color: #6c757d;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Alerta de Performance del Modelo</h1>
        <div class="subtitle">{model_name} ({horizon}) | {timestamp} (Chile)</div>
        <div class="subtitle">Severidad: {overall_severity}</div>
    </div>

    <div class="section">
        <h2>Resumen ({critical_count} críticas, {warning_count} advertencias, {info_count} info)</h2>
"""

    # Add alerts
    for alert in alerts:
        severity_class = alert.severity.value
        html += f"""
        <div class="alert-box {severity_class}">
            <strong>{alert.severity.value.upper()}:</strong> {alert.message}
"""

        # Add metrics comparison if available
        if (
            hasattr(alert, "current_metrics")
            and alert.current_metrics
            and hasattr(alert, "baseline_metrics")
            and alert.baseline_metrics
        ):
            html += """
            <table style="margin-top: 10px;">
                <tr>
                    <th>Métrica</th>
                    <th>Actual</th>
                    <th>Baseline</th>
                </tr>
"""
            for metric in ["rmse", "mae", "directional_accuracy"]:
                if metric in alert.current_metrics and metric in alert.baseline_metrics:
                    current = alert.current_metrics[metric]
                    baseline = alert.baseline_metrics[metric]
                    html += f"""
                <tr>
                    <td>{metric.upper()}</td>
                    <td>{current:.2f}</td>
                    <td>{baseline:.2f}</td>
                </tr>
"""
            html += "            </table>\n"

        # Add recommendations
        if hasattr(alert, "recommendations") and alert.recommendations:
            html += "            <strong>Recomendaciones:</strong>\n"
            html += '            <ol class="recommendations">\n'
            for rec in alert.recommendations[:3]:
                html += f"                <li>{rec}</li>\n"
            html += "            </ol>\n"

        html += "        </div>\n"

    html += f"""
    </div>

    <div class="footer">
        <strong>USD/CLP Forecasting System - MLOps Performance Monitor</strong><br>
        Generado: {timestamp}<br>
        Monitoreo automático de performance
    </div>
</body>
</html>
"""

    return html


__all__ = [
    "generate_market_shock_email",
    "generate_model_performance_email",
]
