"""
Send Copper Impact Report via Email.

Este script envía automáticamente el reporte de impacto de copper
a rafael@cavara.cl cada vez que se ejecuta el tracking semanal.

Uso:
    python scripts/send_copper_report_email.py

    O desde weekly_copper_tracking.sh:
    python scripts/send_copper_report_email.py "$LATEST_REPORT"

Requiere:
    - GMAIL_USER y GMAIL_APP_PASSWORD en .env
    - Reporte HTML generado previamente
"""

from __future__ import annotations

import sys
import json
import smtplib
from pathlib import Path
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forex_core.config import get_settings
from loguru import logger


class CopperReportEmailer:
    """
    Envía reportes de impacto de copper por email.

    Diseñado para enviar a rafael@cavara.cl (responsable de optimización).
    """

    # Email configuration
    RECIPIENT = "rafael@cavara.cl"
    COPPER_INTEGRATION_DATE = datetime(2025, 11, 13)

    def __init__(self):
        """Initialize emailer with settings."""
        self.settings = get_settings()
        self.project_dir = Path(__file__).parent.parent
        self.output_dir = self.project_dir / "output"

        logger.info("CopperReportEmailer initialized")

    def find_latest_report(self) -> Optional[tuple[Path, Path]]:
        """
        Find latest HTML and JSON reports.

        Returns:
            Tuple of (html_path, json_path) or None if not found
        """
        # Find latest HTML report
        html_reports = sorted(
            self.output_dir.glob("copper_impact_report_*.html"),
            reverse=True
        )

        if not html_reports:
            logger.warning("No HTML reports found")
            return None

        html_path = html_reports[0]

        # Find corresponding JSON
        timestamp = html_path.stem.replace("copper_impact_report_", "")
        json_path = self.output_dir / f"copper_impact_report_{timestamp}.json"

        if not json_path.exists():
            logger.warning(f"JSON report not found: {json_path}")
            return None

        logger.info(f"Found reports: {html_path.name}, {json_path.name}")
        return html_path, json_path

    def load_report_data(self, json_path: Path) -> Dict:
        """Load report data from JSON."""
        with open(json_path, 'r') as f:
            data = json.load(f)
        return data

    def calculate_week_number(self, days_since: int) -> int:
        """Calculate week number since integration."""
        return (days_since // 7) + 1

    def generate_email_subject(self, report_data: Dict) -> str:
        """
        Generate dynamic email subject.

        Args:
            report_data: Report JSON data

        Returns:
            Subject line string
        """
        days_since = report_data['days_since_integration']
        week_num = self.calculate_week_number(days_since)
        status = report_data['overall_assessment']['status']

        # Status emojis
        status_emoji = {
            'INSUFFICIENT_DATA': 'ℹ️',
            'PARTIAL_SUCCESS': '⚠️',
            'SUCCESS': '✅',
            'MINIMAL_IMPROVEMENT': '⚠️',
            'NO_IMPROVEMENT': '❌',
        }

        emoji = status_emoji.get(status, '📊')

        # Special case for milestone
        if days_since >= 21:
            return f"🎯 MILESTONE: Copper Impact Report - Semana {week_num} - ACCIÓN REQUERIDA"
        else:
            return f"{emoji} Copper Impact Report - Semana {week_num} - {status.replace('_', ' ')}"

    def build_email_body(self, report_data: Dict, html_path: Path) -> str:
        """
        Build HTML email body with executive summary.

        Args:
            report_data: Report JSON data
            html_path: Path to full HTML report

        Returns:
            HTML email body string
        """
        days_since = report_data['days_since_integration']
        week_num = self.calculate_week_number(days_since)
        status = report_data['overall_assessment']['status']
        recommendation = report_data['overall_assessment']['recommendation']
        avg_improvement = report_data['overall_assessment']['avg_rmse_improvement_pct']

        # Status color
        status_colors = {
            'SUCCESS': '#28a745',
            'PARTIAL_SUCCESS': '#ffc107',
            'MINIMAL_IMPROVEMENT': '#fd7e14',
            'NO_IMPROVEMENT': '#dc3545',
            'INSUFFICIENT_DATA': '#6c757d',
        }
        status_color = status_colors.get(status, '#6c757d')

        # Milestone banner
        milestone_banner = ""
        if days_since >= 21:
            milestone_banner = f"""
            <div style="background: linear-gradient(135deg, #ff6348 0%, #ff4757 100%);
                        color: white; padding: 20px; margin: 20px 0;
                        border-radius: 8px; text-align: center;">
                <h2 style="margin: 0;">🎯 MILESTONE ALCANZADO</h2>
                <p style="margin: 10px 0 0 0; font-size: 16px;">
                    {days_since} días de datos recopilados - ACCIÓN REQUERIDA
                </p>
            </div>
            """

        # Build analysis summary
        analysis_rows = []
        for horizon, metrics in report_data['analysis_by_horizon'].items():
            comp = metrics['comparison']
            pre = metrics['pre_copper']
            post = metrics['post_copper']

            if comp['rmse_improvement_pct'] is not None:
                improvement = f"{comp['rmse_improvement_pct']:+.2f}%"
                color = '#28a745' if comp['rmse_improvement_pct'] < 0 else '#dc3545'
            else:
                improvement = "N/A"
                color = '#6c757d'

            analysis_rows.append(f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #e9ecef;">{horizon}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #e9ecef;">{post['count']}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #e9ecef; color: {color}; font-weight: bold;">
                        {improvement}
                    </td>
                </tr>
            """)

        # Next execution
        next_execution = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                    color: #333;
                }}
                .header {{
                    background: linear-gradient(135deg, #004f71 0%, #003a54 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                }}
                .section {{
                    background: white;
                    padding: 25px;
                    margin-bottom: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .status-box {{
                    background: {status_color};
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                    margin: 20px 0;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                th {{
                    background-color: #004f71;
                    color: white;
                    padding: 12px;
                    text-align: left;
                }}
                .recommendation {{
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 6px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Reporte de Impacto: Copper Integration</h1>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">
                    Semana {week_num} | {days_since} días desde integración | {datetime.now().strftime('%Y-%m-%d')}
                </p>
            </div>

            {milestone_banner}

            <div class="section">
                <h2 style="margin-top: 0; color: #004f71;">🎯 Estado del Análisis</h2>
                <div class="status-box">
                    <h3 style="margin: 0;">{status.replace('_', ' ')}</h3>
                    <p style="margin: 10px 0 0 0;">
                        Mejora Promedio RMSE: {f"{avg_improvement:+.2f}%" if avg_improvement is not None else "N/A"}
                    </p>
                </div>

                <div class="recommendation">
                    <strong>📌 Recomendación:</strong> {recommendation}
                </div>
            </div>

            <div class="section">
                <h2 style="margin-top: 0; color: #004f71;">📊 Resumen por Horizonte</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Horizonte</th>
                            <th>Predicciones</th>
                            <th>Mejora RMSE</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(analysis_rows)}
                    </tbody>
                </table>
            </div>

            <div class="section">
                <h2 style="margin-top: 0; color: #004f71;">📎 Reporte Completo</h2>
                <p>
                    El reporte HTML completo con todos los detalles está adjunto a este email.
                    Ábrelo en tu navegador para ver el análisis detallado.
                </p>
                <p style="color: #6c757d; font-size: 14px;">
                    <strong>Archivo adjunto:</strong> {html_path.name}
                </p>
            </div>

            <div class="section">
                <h2 style="margin-top: 0; color: #004f71;">📅 Próxima Ejecución</h2>
                <p>
                    El próximo reporte se generará automáticamente el <strong>{next_execution}</strong>
                    a las 10:00 AM (Chile) y te llegará por email.
                </p>
            </div>

            <div style="text-align: center; margin-top: 30px; padding: 20px; color: #6c757d; font-size: 12px;">
                <p>
                    <strong>USD/CLP Forecasting System - Copper Impact Tracking</strong><br>
                    Sistema automatizado de seguimiento | rafael@cavara.cl<br>
                    Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')} (Chile)
                </p>
            </div>
        </body>
        </html>
        """

        return html

    def send_email(
        self,
        subject: str,
        body_html: str,
        attachment_path: Path,
    ) -> bool:
        """
        Send email with report.

        Args:
            subject: Email subject
            body_html: HTML body content
            attachment_path: Path to HTML report to attach

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.settings.gmail_user
            msg['To'] = self.RECIPIENT
            msg['Subject'] = subject

            # Attach HTML body
            msg.attach(MIMEText(body_html, 'html'))

            # Attach HTML report
            with open(attachment_path, 'rb') as f:
                attachment = MIMEBase('text', 'html')
                attachment.set_payload(f.read())
                encoders.encode_base64(attachment)
                attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{attachment_path.name}"'
                )
                msg.attach(attachment)

            # Send email
            logger.info(f"Sending email to {self.RECIPIENT}...")

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(
                    self.settings.gmail_user,
                    self.settings.gmail_app_password
                )
                server.send_message(msg)

            logger.info(f"✅ Email sent successfully to {self.RECIPIENT}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            return False

    def run(self, html_path: Optional[Path] = None) -> bool:
        """
        Run email sending process.

        Args:
            html_path: Optional path to HTML report. If None, finds latest.

        Returns:
            True if email sent successfully
        """
        logger.info("=" * 70)
        logger.info("COPPER REPORT EMAIL - Starting")
        logger.info("=" * 70)

        # Find reports
        if html_path is None:
            reports = self.find_latest_report()
            if reports is None:
                logger.error("No reports found to send")
                return False
            html_path, json_path = reports
        else:
            # Find corresponding JSON
            timestamp = html_path.stem.replace("copper_impact_report_", "")
            json_path = html_path.parent / f"copper_impact_report_{timestamp}.json"
            if not json_path.exists():
                logger.error(f"JSON report not found: {json_path}")
                return False

        # Load report data
        report_data = self.load_report_data(json_path)

        # Generate subject
        subject = self.generate_email_subject(report_data)
        logger.info(f"Subject: {subject}")

        # Build email body
        body_html = self.build_email_body(report_data, html_path)

        # Send email
        success = self.send_email(subject, body_html, html_path)

        logger.info("=" * 70)
        logger.info(f"COPPER REPORT EMAIL - {'Success' if success else 'Failed'}")
        logger.info("=" * 70)

        return success


def main():
    """Main function."""
    # Optional: Accept HTML path as argument
    html_path = None
    if len(sys.argv) > 1:
        html_path = Path(sys.argv[1])
        if not html_path.exists():
            print(f"❌ Error: File not found: {html_path}")
            sys.exit(1)

    emailer = CopperReportEmailer()
    success = emailer.run(html_path)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
