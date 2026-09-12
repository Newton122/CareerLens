"""Sending email: password-reset and verification links.

Uses Python's standard ``smtplib``, so any SMTP provider works and no extra
package is needed. Settings come from config.py (SMTP_HOST, SMTP_PORT,
SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM, SMTP_SECURITY).

When SMTP is not configured:

* in development the whole email, link included, is written to the server
  log, so you can copy the link from the terminal and test the flow locally;
* in production nothing sensitive is logged -- a reset link in a log file
  would let anyone who can read the logs take over the account -- only a
  warning that email is not configured.

Callers send from a background task (FastAPI ``BackgroundTasks``), after the
response has gone out. That keeps requests fast, and it means "forgot
password" takes the same time whether or not the account exists, so the
timing cannot reveal which email addresses are registered.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage

from ai_job_intelligence import config

logger = logging.getLogger(__name__)

SMTP_TIMEOUT_SECONDS = 15


def is_configured() -> bool:
    return bool(config.SMTP_HOST and config.SMTP_FROM)


def send_email(to: str, subject: str, body: str) -> bool:
    """Send a plain-text email. True if it was handed to the SMTP server."""
    if not is_configured():
        if config.IS_PRODUCTION:
            logger.warning(
                "Email to %s not sent: SMTP is not configured (set SMTP_HOST).", to
            )
        else:
            logger.warning(
                "SMTP not configured -- development copy of the email:\n"
                "To: %s\nSubject: %s\n\n%s",
                to,
                subject,
                body,
            )
        return False

    message = EmailMessage()
    message["From"] = config.SMTP_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    try:
        if config.SMTP_SECURITY == "ssl":
            server = smtplib.SMTP_SSL(
                config.SMTP_HOST,
                config.SMTP_PORT,
                timeout=SMTP_TIMEOUT_SECONDS,
                context=ssl.create_default_context(),
            )
        else:
            server = smtplib.SMTP(
                config.SMTP_HOST, config.SMTP_PORT, timeout=SMTP_TIMEOUT_SECONDS
            )
        with server:
            if config.SMTP_SECURITY == "starttls":
                server.starttls(context=ssl.create_default_context())
            if config.SMTP_USERNAME:
                server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            server.send_message(message)
        return True
    except (smtplib.SMTPException, OSError) as exc:
        # Never raise: this runs after the response, and a mail outage must
        # not look like an application error to the user.
        logger.error("Could not send email to %s: %s", to, exc)
        return False


# --- the two emails the app sends -------------------------------------------


def send_password_reset(to: str, link: str, minutes_valid: int) -> bool:
    return send_email(
        to,
        "Reset your CareerLens password",
        "Someone (hopefully you) asked to reset the password for your "
        "CareerLens account.\n\n"
        f"Choose a new password here:\n{link}\n\n"
        f"This link works once and expires in {minutes_valid} minutes. "
        "Resetting signs you out on every device.\n\n"
        "If you didn't ask for this, ignore this email; your password has "
        "not changed.",
    )


def send_verification(to: str, link: str, hours_valid: int) -> bool:
    return send_email(
        to,
        "Confirm your email for CareerLens",
        "Welcome to CareerLens!\n\n"
        f"Confirm that this is your email address:\n{link}\n\n"
        f"The link expires in {hours_valid} hours. If you didn't create a "
        "CareerLens account, you can ignore this email.",
    )
