"""
app/tools/email_sender.py
Tool — SMTP Email Sender

Sends application emails via SMTP (Gmail, Outlook, or any SMTP server).
Gated by ENABLE_EMAIL_SEND env flag — always drafts, only sends if enabled.
"""
from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional

from loguru import logger


class EmailSender:
    """
    Sends job application emails via SMTP.

    Safety: ENABLE_EMAIL_SEND must be explicitly set to 'true'.
    Default behavior is draft-only (no actual send).
    """

    def __init__(self):
        self.host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER", "")
        self.password = os.getenv("SMTP_PASSWORD", "")
        self.from_name = os.getenv("EMAIL_FROM_NAME", "Applicant")
        self.enabled = os.getenv("ENABLE_EMAIL_SEND", "false").lower() == "true"

    def send(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachments: Optional[list[str]] = None,
    ) -> bool:
        """
        Send application email.
        Returns True if sent (or would have been sent in dry-run mode).
        """
        if not self.enabled:
            logger.info(
                f"[EmailSender] DRY RUN — would send to {to_email}: '{subject}'"
            )
            return True  # Pretend success in draft mode

        if not self.user or not self.password:
            logger.error("[EmailSender] SMTP credentials not configured")
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = f"{self.from_name} <{self.user}>"
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            # Attach files (resume, cover letter)
            if attachments:
                for filepath in attachments:
                    path = Path(filepath)
                    if path.exists():
                        with open(path, "rb") as f:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename={path.name}"
                        )
                        msg.attach(part)
                        logger.debug(f"[EmailSender] Attached: {path.name}")

            with smtplib.SMTP(self.host, self.port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.user, to_email, msg.as_string())

            logger.info(f"[EmailSender] ✓ Email sent to {to_email}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("[EmailSender] SMTP authentication failed — check credentials")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"[EmailSender] SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"[EmailSender] Unexpected error: {e}")
            return False
