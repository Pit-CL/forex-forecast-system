"""
Notifications module for forex forecast system.

Exports:
    - EmailSender: Send email notifications with PDF attachments
"""

from .email import EmailSender

__all__ = [
    "EmailSender",
]
