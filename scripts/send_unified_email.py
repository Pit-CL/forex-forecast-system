#!/usr/bin/env python3
"""
Send Unified Email with CID Images.

This script sends production emails with:
- HTML body with inline images (using CID)
- PDF attachment (light version ~30KB)

Usage:
    python scripts/send_unified_email.py <html_path> <pdf_path>

Example:
    python scripts/send_unified_email.py output/email.html output/report.pdf
"""

import sys
import smtplib
import re
import base64
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from forex_core.config import get_settings
from loguru import logger


def send_email_with_cid(html_path: Path, pdf_path: Path, subject: str = None) -> bool:
    """
    Send email with HTML body (CID images) and PDF attachment.
    
    Args:
        html_path: Path to HTML email file
        pdf_path: Path to PDF attachment
        subject: Email subject (auto-generated if None)
        
    Returns:
        True if sent successfully, False otherwise
    """
    settings = get_settings()
    
    logger.info(f'Sending unified email: {html_path.name} + {pdf_path.name}')
    
    # Read HTML
    with open(html_path, 'r', encoding='utf-8') as f:
        email_body_html = f.read()
    
    # Extract all base64 images from HTML
    img_matches = list(re.finditer(r'data:image/(png|jpeg|jpg);base64,([A-Za-z0-9+/=]+)', email_body_html))
    
    logger.info(f'Found {len(img_matches)} base64 images in HTML')
    
    # Create message with related content (for inline images)
    msg = MIMEMultipart('related')
    msg['From'] = settings.gmail_user
    msg['To'] = ', '.join(settings.email_recipients)
    
    # Generate subject if not provided
    if subject is None:
        # Extract from HTML title or use default
        title_match = re.search(r'<title>([^<]+)</title>', email_body_html)
        if title_match:
            subject = title_match.group(1)
        else:
            subject = 'USD/CLP Forecast Report'
    
    msg['Subject'] = subject
    logger.info(f'Subject: {subject}')
    
    # Create alternative part for HTML
    msg_alternative = MIMEMultipart('alternative')
    msg.attach(msg_alternative)
    
    # Replace base64 images with CID references and attach them
    for idx, match in enumerate(img_matches):
        img_format = match.group(1)
        img_base64 = match.group(2)
        cid_name = f'image{idx}'
        
        # Replace base64 with CID
        email_body_html = email_body_html.replace(
            match.group(0),
            f'cid:{cid_name}'
        )
        
        # Decode and attach image
        img_data = base64.b64decode(img_base64)
        img_mime = MIMEImage(img_data, img_format)
        img_mime.add_header('Content-ID', f'<{cid_name}>')
        img_mime.add_header('Content-Disposition', 'inline', filename=f'{cid_name}.{img_format}')
        msg.attach(img_mime)
        
        logger.info(f'  Image {idx}: {len(img_data)} bytes as CID:{cid_name}')
    
    # Attach HTML body
    msg_alternative.attach(MIMEText(email_body_html, 'html', 'utf-8'))
    
    # Attach PDF
    with open(pdf_path, 'rb') as f:
        pdf_attachment = MIMEBase('application', 'pdf')
        pdf_attachment.set_payload(f.read())
        encoders.encode_base64(pdf_attachment)
        pdf_attachment.add_header('Content-Disposition', f'attachment; filename="{pdf_path.name}"')
        msg.attach(pdf_attachment)
    
    logger.info(f'PDF attached: {pdf_path.name} ({pdf_path.stat().st_size / 1024:.1f} KB)')
    
    # Send email
    try:
        logger.info(f'Sending to: {settings.email_recipients}')
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(settings.gmail_user, settings.gmail_app_password)
            server.send_message(msg)
        
        logger.info('✅ Email sent successfully with CID images!')
        return True
        
    except Exception as e:
        logger.error(f'❌ Failed to send email: {e}')
        return False


def main():
    """Main function."""
    if len(sys.argv) < 3:
        print('Usage: python send_unified_email.py <html_path> <pdf_path> [subject]')
        sys.exit(1)
    
    html_path = Path(sys.argv[1])
    pdf_path = Path(sys.argv[2])
    subject = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not html_path.exists():
        print(f'❌ HTML file not found: {html_path}')
        sys.exit(1)
    
    if not pdf_path.exists():
        print(f'❌ PDF file not found: {pdf_path}')
        sys.exit(1)
    
    success = send_email_with_cid(html_path, pdf_path, subject)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
