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

from ..config.base import Settings
from ..utils.logging import get_logger

logger = get_logger(__name__)


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

    def send(
        self,
        report_path: Path,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        additional_attachments: Sequence[Path] = None,
    ) -> None:
        """
        Send email with PDF report attachment.

        Args:
            report_path: Path to main PDF report
            subject: Email subject line (auto-generated if None)
            body: Email body text (auto-generated if None)
            additional_attachments: Optional additional files to attach

        Raises:
            smtplib.SMTPException: If email sending fails
            FileNotFoundError: If report_path does not exist
        """
        if not report_path.exists():
            raise FileNotFoundError(f"Report file not found: {report_path}")

        # Auto-generate subject if not provided
        if subject is None:
            subject = self._generate_subject(report_path)

        # Auto-generate body if not provided
        if body is None:
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
