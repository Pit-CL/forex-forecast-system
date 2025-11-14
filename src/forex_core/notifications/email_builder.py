"""
Email Content Builder for Unified USD/CLP Emails.

This module generates responsive HTML emails with inline chart previews
and mobile-first design for the unified email system.

Features:
- Executive summary always visible
- Forecast sections with detailed metrics
- Inline chart previews (base64 encoded)
- System health dashboard integration
- Mobile-responsive design
- All content in Spanish

Author: Forex Forecast System
License: MIT
"""

from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .unified_email import (
    ForecastData,
    SystemHealthData,
    UnifiedEmailContent,
)
from ..utils.logging import get_logger

logger = get_logger(__name__)


class EmailContentBuilder:
    """
    Builds HTML content for unified emails.

    Generates responsive, mobile-first email HTML with:
    - Executive summary section
    - Forecast sections (one per horizon)
    - System health dashboard
    - Performance metrics
    - Inline chart previews
    """

    # Institutional colors
    COLOR_PRIMARY = "#004f71"  # Azul institucional
    COLOR_SECONDARY = "#d8e5ed"  # Gris claro
    COLOR_PRIMARY_DARK = "#003a54"  # Azul oscuro (variant)
    COLOR_PRIMARY_LIGHT = "#0066a1"  # Azul claro (variant)

    # CSS for responsive email (inline styles for email client compatibility)
    EMAIL_CSS = """
    <style>
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
        .priority-urgent {
            background: linear-gradient(135deg, #ff4757 0%, #ff6348 100%);
        }
        .priority-attention {
            background: linear-gradient(135deg, #ffa502 0%, #ff6348 100%);
        }
        .executive-summary {
            background: white;
            border-left: 4px solid #004f71;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .executive-summary h2 {
            margin-top: 0;
            color: #004f71;
            font-size: 18px;
        }
        .executive-summary ul {
            margin: 10px 0;
            padding-left: 20px;
        }
        .executive-summary li {
            margin: 8px 0;
            line-height: 1.6;
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
        .forecast-metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 15px 0;
        }
        .metric {
            padding: 12px;
            background: #f8f9fa;
            border-radius: 6px;
        }
        .metric-label {
            font-size: 12px;
            color: #6c757d;
            margin-bottom: 4px;
        }
        .metric-value {
            font-size: 20px;
            font-weight: bold;
            color: #333;
        }
        .bias-alcista {
            color: #28a745;
        }
        .bias-bajista {
            color: #dc3545;
        }
        .bias-neutral {
            color: #6c757d;
        }
        .status-excellent {
            color: #28a745;
            font-weight: bold;
        }
        .status-good {
            color: #28a745;
        }
        .status-degraded {
            color: #dc3545;
            font-weight: bold;
        }
        .status-warning {
            color: #ffc107;
            font-weight: bold;
        }
        .chart-preview {
            max-width: 100%;
            border-radius: 8px;
            margin: 15px 0;
        }
        .pdf-attachment {
            display: inline-block;
            padding: 10px 20px;
            background: #004f71;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            margin: 10px 0;
        }
        .recommendations {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 15px 0;
            border-radius: 6px;
        }
        .recommendations h4 {
            margin-top: 0;
            color: #856404;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            color: #6c757d;
            font-size: 12px;
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
            background-color: #f8f9fa;
            font-weight: 600;
            color: #555;
        }
        @media only screen and (max-width: 600px) {
            body {
                padding: 10px;
            }
            .header {
                padding: 20px;
            }
            .header h1 {
                font-size: 20px;
            }
            .forecast-metrics {
                grid-template-columns: 1fr;
            }
        }
    </style>
    """

    def __init__(self):
        """Initialize the email content builder."""
        logger.info("EmailContentBuilder initialized")

    def build(
        self,
        forecasts: List[ForecastData],
        system_health: SystemHealthData,
        priority: str,
        pdf_attachments: List[Path],
        current_date: datetime | None = None,
    ) -> str:
        """
        Build complete HTML email content.

        Args:
            forecasts: List of forecast data to include
            system_health: System health data
            priority: Email priority ("URGENT", "ATTENTION", "ROUTINE")
            pdf_attachments: List of PDF paths that will be attached
            current_date: Date for email (defaults to now)

        Returns:
            Complete HTML string for email body
        """
        if current_date is None:
            current_date = datetime.now()

        logger.info(
            f"Building email content: {len(forecasts)} forecasts, priority={priority}",
        )

        # Build sections
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            '<meta charset="UTF-8">',
            f"<title>USD/CLP Daily Report - {current_date.strftime('%Y-%m-%d')}</title>",
            self.EMAIL_CSS,
            "</head>",
            "<body>",
            self._build_header(priority, current_date),
            self._build_executive_summary(forecasts, system_health),
        ]

        # Add forecast sections
        for forecast in forecasts:
            has_pdf = forecast.pdf_path in pdf_attachments if forecast.pdf_path else False
            html_parts.append(self._build_forecast_section(forecast, has_pdf))

        # Add system health section
        html_parts.append(self._build_system_health_section(system_health))

        # Add recommendations if needed
        if forecasts:
            html_parts.append(self._build_recommendations_section(forecasts[0]))

        # Footer
        html_parts.append(self._build_footer(current_date))

        html_parts.extend([
            "</body>",
            "</html>",
        ])

        return "\n".join(html_parts)

    def _build_header(self, priority: str, current_date: datetime) -> str:
        """Build email header with priority indicator."""
        priority_class = f"priority-{priority.lower()}" if priority != "ROUTINE" else ""

        priority_icons = {
            "URGENT": "🚨 URGENTE",
            "ATTENTION": "⚠️ ATENCIÓN",
            "ROUTINE": "📊",
        }

        icon = priority_icons.get(priority, "📊")

        # Spanish day and month names
        dias = {
            'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
            'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
        }
        meses = {
            'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril',
            'May': 'Mayo', 'June': 'Junio', 'July': 'Julio', 'August': 'Agosto',
            'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'
        }

        fecha_en = current_date.strftime('%A, %B %d, %Y')
        dia_en = current_date.strftime('%A')
        mes_en = current_date.strftime('%B')
        fecha_es = fecha_en.replace(dia_en, dias[dia_en]).replace(mes_en, meses[mes_en])

        return f"""
        <div class="header {priority_class}">
            <h1>{icon} Sistema de Pronóstico USD/CLP</h1>
            <div class="date">{fecha_es}</div>
        </div>
        """

    def _build_executive_summary(
        self,
        forecasts: List[ForecastData],
        system_health: SystemHealthData,
    ) -> str:
        """Build executive summary section."""
        summary_items = []

        # Add forecast summaries
        for forecast in forecasts:
            bias_class = f"bias-{forecast.bias.lower()}"
            summary_items.append(
                f'<li><strong>{forecast.horizon}:</strong> '
                f'${forecast.current_price:.0f} → ${forecast.forecast_price:.0f} '
                f'(<span class="{bias_class}">{forecast.change_pct:+.1f}%</span>) '
                f'| {forecast.bias}</li>'
            )

        # Add system health
        readiness_class = "status-excellent" if system_health.readiness_score >= 90 else "status-good"
        summary_items.append(
            f'<li><strong>Salud del Sistema:</strong> '
            f'<span class="{readiness_class}">{system_health.readiness_level}</span> '
            f'({system_health.readiness_score:.0f}/100)</li>'
        )

        # Add alerts if any
        if system_health.has_critical_issues():
            alert_count = (
                len(system_health.degradation_details) +
                len(system_health.drift_details)
            )
            summary_items.append(
                f'<li><strong>Alertas:</strong> '
                f'<span class="status-warning">{alert_count} problemas detectados</span></li>'
            )
        else:
            summary_items.append(
                '<li><strong>Alertas:</strong> '
                '<span class="status-good">✓ Sistema operando normalmente</span></li>'
            )

        return f"""
        <div class="executive-summary">
            <h2>🎯 Resumen Ejecutivo</h2>
            <ul>
                {"".join(summary_items)}
            </ul>
        </div>
        """

    def _build_forecast_section(
        self,
        forecast: ForecastData,
        has_pdf: bool,
    ) -> str:
        """Build section for a single forecast."""
        bias_class = f"bias-{forecast.bias.lower()}"

        # Build metrics grid
        metrics_html = f"""
        <div class="forecast-metrics">
            <div class="metric">
                <div class="metric-label">Precio Actual</div>
                <div class="metric-value">${forecast.current_price:.2f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Pronóstico</div>
                <div class="metric-value">${forecast.forecast_price:.2f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Cambio</div>
                <div class="metric-value {bias_class}">{forecast.change_pct:+.2f}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Sesgo</div>
                <div class="metric-value {bias_class}">{forecast.bias}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Volatilidad</div>
                <div class="metric-value">{forecast.volatility}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Rango IC 95%</div>
                <div class="metric-value" style="font-size: 14px;">
                    ${forecast.ci95_low:.0f} - ${forecast.ci95_high:.0f}
                </div>
            </div>
        </div>
        """

        # Add chart preview if available
        chart_html = ""
        if forecast.chart_preview:
            chart_html = f"""
            <div>
                <h4>Vista Previa</h4>
                <img src="data:image/png;base64,{forecast.chart_preview.decode()}"
                     class="chart-preview"
                     alt="Gráfico de Pronóstico" />
            </div>
            """

        # Add top drivers if available
        drivers_html = ""
        if forecast.top_drivers:
            drivers_list = "".join([f"<li>{driver}</li>" for driver in forecast.top_drivers[:3]])
            drivers_html = f"""
            <div>
                <h4>Principales Drivers</h4>
                <ul>
                    {drivers_list}
                </ul>
            </div>
            """

        # Add PDF link if attached
        pdf_html = ""
        if has_pdf:
            pdf_html = f"""
            <div style="margin-top: 15px;">
                <span class="pdf-attachment">📎 PDF Adjunto: forecast_{forecast.horizon}_{datetime.now().strftime('%Y-%m-%d')}.pdf</span>
            </div>
            """

        return f"""
        <div class="section">
            <div class="section-header">
                <h3>📈 Pronóstico {forecast.horizon.upper()} - {forecast.bias}</h3>
            </div>
            <div class="section-content">
                {metrics_html}
                {chart_html}
                {drivers_html}
                {pdf_html}
            </div>
        </div>
        """

    def _build_system_health_section(
        self,
        system_health: SystemHealthData,
    ) -> str:
        """Build system health dashboard section."""
        # Performance table
        performance_rows = []
        for horizon, status in system_health.performance_status.items():
            status_class = f"status-{status.lower()}"
            performance_rows.append(
                f"""
                <tr>
                    <td>{horizon}</td>
                    <td class="{status_class}">{status}</td>
                </tr>
                """
            )

        # Alerts
        alerts_html = ""
        if system_health.degradation_detected or system_health.drift_detected:
            alerts = []
            if system_health.degradation_detected:
                alerts.extend([f"<li>⚠️ {detail}</li>" for detail in system_health.degradation_details])
            if system_health.drift_detected:
                alerts.extend([f"<li>⚠️ {detail}</li>" for detail in system_health.drift_details])

            alerts_html = f"""
            <div class="recommendations">
                <h4>⚠️ Alertas de Sistema</h4>
                <ul>
                    {"".join(alerts)}
                </ul>
            </div>
            """

        return f"""
        <div class="section">
            <div class="section-header">
                <h3>🏥 Salud del Sistema</h3>
            </div>
            <div class="section-content">
                <div class="forecast-metrics">
                    <div class="metric">
                        <div class="metric-label">Estado</div>
                        <div class="metric-value">{system_health.readiness_level}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Puntaje</div>
                        <div class="metric-value">{system_health.readiness_score:.0f}/100</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Predicciones Recientes</div>
                        <div class="metric-value">{system_health.recent_predictions}</div>
                    </div>
                </div>

                <h4>Rendimiento por Horizonte</h4>
                <table>
                    <thead>
                        <tr>
                            <th>Horizonte</th>
                            <th>Estado</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(performance_rows)}
                    </tbody>
                </table>

                {alerts_html}
            </div>
        </div>
        """

    def _build_recommendations_section(self, primary_forecast: ForecastData) -> str:
        """Build recommendations section based on forecast bias with dynamic levels."""
        # Calculate dynamic levels based on current prices and confidence intervals
        current = primary_forecast.current_price
        forecast = primary_forecast.forecast_price
        ci80_low = primary_forecast.ci80_low
        ci80_high = primary_forecast.ci80_high

        # Calculate support/resistance levels
        support_level = int(ci80_low / 5) * 5  # Round to nearest 5
        resistance_level = int(ci80_high / 5) * 5
        mid_level = int(current / 5) * 5

        if primary_forecast.bias == "ALCISTA":
            recommendations = {
                "Importadores": f"Cubrir 30-50% exposición en retrocesos hacia ${support_level}-{support_level+5}. Evitar compras masivas arriba de ${resistance_level}.",
                "Exportadores": f"Esperar niveles superiores (${resistance_level}+) para vender USD. Aprovechar rally del cobre para mejores tipos de cambio.",
                "Traders": f"Long USD/CLP en pullbacks a ${support_level}-{support_level+5}, target IC80 superior (${resistance_level}). Stop loss bajo ${support_level-5}.",
                "Tesorería Corporativa": f"Estrategia escalonada: cubrir 20% actual, 30% en ${support_level+5}, 30% en ${mid_level}, 20% en ${mid_level+5}.",
            }
        elif primary_forecast.bias == "BAJISTA":
            recommendations = {
                "Importadores": f"Aguardar descensos hacia ${support_level}-{support_level-5}, no apresurarse en coberturas. Aprovechar debilidad del USD.",
                "Exportadores": f"Asegurar niveles actuales (${int(current)}), cubrir 40-60% exposición. Vender en rebotes hacia ${resistance_level}.",
                "Traders": f"Short USD/CLP en rebotes a ${resistance_level}-{resistance_level-5}, target IC80 inferior (${support_level}). Stop loss sobre ${resistance_level+5}.",
                "Tesorería Corporativa": f"Cubrir en rebotes: 30% en ${resistance_level-5}, 30% en ${mid_level+5}, 20% en ${mid_level}, 20% spot.",
            }
        else:  # NEUTRAL
            recommendations = {
                "Importadores": f"Coberturas escalonadas: 25% en ${support_level}, 25% en ${mid_level-5}, 25% en ${mid_level}, 25% en ${mid_level+5}.",
                "Exportadores": f"Estrategia neutral, vender en extremos de rango superior (${resistance_level}+). Mantener flexibilidad.",
                "Traders": f"Range-bound trading entre ${support_level}-{resistance_level}, vender volatilidad. Neutral hasta ruptura clara.",
                "Tesorería Corporativa": f"Estrategia balanceada: cubrir 20% actual, 30% en ${mid_level-5}, 30% en ${mid_level+5}, 20% en ${resistance_level-5}.",
            }

        recommendations_html = "".join([
            f"<li><strong>{role}:</strong> {action}</li>"
            for role, action in recommendations.items()
        ])

        return f"""
        <div class="section">
            <div class="section-header">
                <h3>💡 Recomendaciones por Perfil</h3>
            </div>
            <div class="section-content">
                <table>
                    <thead>
                        <tr>
                            <th>Perfil</th>
                            <th>Recomendación</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([f'<tr><td><strong>{role}</strong></td><td>{action}</td></tr>' for role, action in recommendations.items()])}
                    </tbody>
                </table>
                <p style="color: #6c757d; font-size: 12px; margin-top: 15px;">
                    <em>Estas recomendaciones son generadas automáticamente basadas en el pronóstico y no constituyen asesoría financiera.
                    Consulte con su asesor antes de tomar decisiones de inversión.</em>
                </p>
            </div>
        </div>
        """

    def _build_footer(self, current_date: datetime) -> str:
        """Build email footer."""
        return f"""
        <div class="footer">
            <p>
                Generado automáticamente por USD/CLP Forecasting System<br>
                {current_date.strftime('%Y-%m-%d %H:%M')} (Chile)<br>
                <em>Sistema de pronóstico automatizado - MLOps Phase 2</em>
            </p>
        </div>
        """


__all__ = ["EmailContentBuilder"]
