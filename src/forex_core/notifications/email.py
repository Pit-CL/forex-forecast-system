"""
Email Notification Service for USD/CLP Forecasting System.

This module provides email delivery capabilities for forecast reports using
Gmail SMTP with app-specific passwords.

Security:
    - Uses Gmail app-specific passwords (not account password)
    - SMTP over SSL (port 465)
    - Credentials from environment variables only

Dependencies:
    - Python standard library (smtplib, email)

Author: Forex Forecast System
License: MIT
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import List, Sequence

import pandas as pd

from ..config.base import Settings
from ..utils.logging import get_logger

logger = get_logger(__name__)

# Horizon label mapping for Spanish display
HORIZON_LABELS = {
    "7d": "Semanal (7 días)",
    "15d": "Quincenal (15 días)",
    "30d": "Mensual (30 días)",
    "90d": "Trimestral (90 días)",
    "12m": "Anual (12 meses)",
}


class EmailSender:
    """
    Sends email notifications with PDF report attachments.

    This class handles:
    - SMTP authentication via Gmail
    - PDF attachment encoding
    - Bulk recipient delivery
    - Error handling and logging

    Attributes:
        settings: System configuration with email credentials
        gmail_user: Gmail account (from settings)
        gmail_password: App-specific password (from settings)
        recipients: List of recipient email addresses

    Raises:
        ValueError: If email credentials are not configured
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the email sender.

        Args:
            settings: System configuration with email settings

        Raises:
            ValueError: If GMAIL_USER or GMAIL_APP_PASSWORD not set
        """
        if not settings.gmail_user or not settings.gmail_app_password:
            raise ValueError(
                "Email sending requires GMAIL_USER and GMAIL_APP_PASSWORD "
                "to be configured in environment variables. "
                "Create an app-specific password at: "
                "https://myaccount.google.com/apppasswords"
            )

        self.settings = settings
        self.gmail_user = settings.gmail_user
        self.gmail_password = settings.gmail_app_password
        self.recipients = settings.email_recipients

        logger.info(
            f"EmailSender initialized for {len(self.recipients)} recipients",
            extra={"gmail_user": self.gmail_user},
        )

    def _generate_executive_summary(
        self,
        bundle,
        forecast,
        horizon: str,
    ) -> str:
        """Generate executive summary with forecast highlights and actions."""
        from ..data.loader import DataBundle
        from ..data.models import ForecastResult

        # Current price
        current_price = bundle.usdclp_series.iloc[-1]

        # Forecast endpoint
        fc_last = forecast.series[-1]
        fc_mean = fc_last.mean
        fc_change_pct = ((fc_mean / current_price) - 1) * 100

        # IC 80% range
        ic80_low = fc_last.ci80_low
        ic80_high = fc_last.ci80_high

        # Determine directional bias
        if fc_change_pct > 0.3:
            bias = "ALCISTA"
            bias_emoji = "📈"
        elif fc_change_pct < -0.3:
            bias = "BAJISTA"
            bias_emoji = "📉"
        else:
            bias = "NEUTRAL"
            bias_emoji = "➡️"

        # Horizon-specific actions
        horizon_label = HORIZON_LABELS.get(horizon, horizon)

        if bias == "ALCISTA":
            action_importers = "Cubrir 30-50% exposición en retrocesos"
            action_exporters = "Esperar niveles superiores para vender USD"
            action_traders = "Long USD/CLP en pullbacks, target IC80 superior"
        elif bias == "BAJISTA":
            action_importers = "Aguardar descensos, no apresurarse en coberturas"
            action_exporters = "Asegurar niveles actuales, cubrir 40-60% exposición"
            action_traders = "Short USD/CLP en rebotes, target IC80 inferior"
        else:
            action_importers = "Coberturas escalonadas 20-30-30-20%"
            action_exporters = "Estrategia neutral, vender en extremos de rango"
            action_traders = "Range-bound trading, vender volatilidad"

        summary = f"""
=== RESUMEN EJECUTIVO ===

Período analizado: {horizon_label}
Sesgo direccional: {bias} {bias_emoji}
Precio actual: {current_price:.2f} CLP
Precio proyectado: {fc_mean:.2f} CLP ({fc_change_pct:+.2f}%)
Rango proyectado (IC 80%): {ic80_low:.2f} - {ic80_high:.2f} CLP

ACCIONES RECOMENDADAS:
• [Importadores]: {action_importers}
• [Exportadores]: {action_exporters}
• [Traders]: {action_traders}

=== INFORME COMPLETO ===
Ver archivo adjunto PDF para análisis detallado con gráficos y proyecciones.

---
Sistema Automático de Pronóstico USD/CLP
Generado: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')} (Chile)
"""
        return summary

    def send(
        self,
        report_path: Path,
        subject: str | None = None,
        body: str | None = None,
        additional_attachments: Sequence[Path] = None,
        bundle = None,
        forecast = None,
        horizon: str = "7d",
    ) -> None:
        """
        Send email with PDF report attachment.

        Args:
            report_path: Path to main PDF report
            subject: Email subject line (auto-generated if None)
            body: Email body text (auto-generated if None)
            additional_attachments: Optional additional files to attach
            bundle: DataBundle for generating executive summary
            forecast: ForecastResult for generating executive summary
            horizon: Forecast horizon code (e.g., "7d", "15d")

        Raises:
            smtplib.SMTPException: If email sending fails
            FileNotFoundError: If report_path does not exist
        """
        if not report_path.exists():
            raise FileNotFoundError(f"Report file not found: {report_path}")

        # Generate subject with date and bias if bundle/forecast provided
        if subject is None:
            if bundle is not None and forecast is not None:
                current_price = bundle.usdclp_series.iloc[-1]
                fc_last = forecast.series[-1]
                fc_change_pct = ((fc_last.mean / current_price) - 1) * 100

                if fc_change_pct > 0.3:
                    bias_label = "ALCISTA 📈"
                elif fc_change_pct < -0.3:
                    bias_label = "BAJISTA 📉"
                else:
                    bias_label = "NEUTRAL ➡️"

                date_str = pd.Timestamp.now().strftime('%Y-%m-%d')
                horizon_label = HORIZON_LABELS.get(horizon, horizon)
                subject = f"[USD/CLP] Proyección {horizon_label} - {date_str} - {bias_label}"
            else:
                subject = self._generate_subject(report_path)

        # Generate body with executive summary if bundle/forecast provided
        if body is None:
            if bundle is not None and forecast is not None:
                body = self._generate_executive_summary(bundle, forecast, horizon)
            else:
                body = self._generate_body(report_path)

        # Build attachments list
        attachments = [report_path]
        if additional_attachments:
            attachments.extend(additional_attachments)

        # Send email
        logger.info(
            f"Sending email: {subject}",
            extra={
                "recipients": len(self.recipients),
                "attachments": len(attachments),
            },
        )

        self._send_email(subject, body, attachments)

        logger.info(
            f"Email sent successfully",
            extra={
                "recipients": self.recipients,
                "subject": subject,
            },
        )

    def _send_email(
        self,
        subject: str,
        body: str,
        attachments: Sequence[Path],
    ) -> None:
        """
        Internal method to send email via Gmail SMTP.

        Args:
            subject: Email subject
            body: Email body text
            attachments: List of file paths to attach
        """
        # Create message
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.gmail_user
        message["To"] = ", ".join(self.recipients)
        message.set_content(body)

        # Attach files
        for attachment in attachments:
            content = attachment.read_bytes()
            maintype = "application"
            subtype = "pdf" if attachment.suffix == ".pdf" else "octet-stream"

            message.add_attachment(
                content,
                maintype=maintype,
                subtype=subtype,
                filename=attachment.name,
            )

        # Send via SMTP
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(self.gmail_user, self.gmail_password)
            server.send_message(message)

    def _generate_subject(self, report_path: Path) -> str:
        """
        Generate email subject from report filename.

        Args:
            report_path: Path to report file

        Returns:
            Email subject string
        """
        filename = report_path.stem  # Filename without extension

        if "7d" in filename:
            return "Proyección USD/CLP (7 días) - Forex Forecast System"
        elif "12m" in filename:
            return "Proyección USD/CLP (12 meses) - Forex Forecast System"
        elif "importer" in filename.lower():
            return "Informe Entorno Importador - Forex Forecast System"
        else:
            return "Reporte USD/CLP - Forex Forecast System"

    def _generate_body(self, report_path: Path) -> str:
        """
        Generate email body text.

        Args:
            report_path: Path to report file

        Returns:
            Email body string
        """
        body = (
            "Estimado/a,\n\n"
            "Se adjunta el reporte de proyección USD/CLP generado automáticamente.\n\n"
            f"Archivo: {report_path.name}\n"
            f"Tamaño: {report_path.stat().st_size / 1024:.1f} KB\n\n"
            "Este reporte ha sido generado mediante modelos estadísticos (ARIMA, VAR, Random Forest) "
            "con datos actualizados del Banco Central de Chile, Federal Reserve, y otras fuentes.\n\n"
            "Para consultas o soporte técnico, responder a este correo.\n\n"
            "Saludos,\n"
            "Forex Forecast System\n"
            "🤖 Generado automáticamente"
        )

        return body
