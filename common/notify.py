"""
Shared email sending for all agents. Supports two methods, chosen via the
EMAIL_METHOD environment variable ("resend" or "smtp"), and always supports
multiple recipients via ALERT_EMAILS (comma-separated list).

Resend without domain verification ("onboarding@resend.dev") can ONLY send
to the email address the Resend account itself was created with — that
doesn't work in practice if a customer wants multiple recipients. For that,
either the Resend domain needs to be verified, or SMTP should be used
instead.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests


def _get_recipients():
    raw = os.environ.get("ALERT_EMAILS", "")
    recipients = [e.strip() for e in raw.split(",") if e.strip()]
    if not recipients:
        raise RuntimeError(
            "ALERT_EMAILS is not set. Must be a comma-separated list of "
            "recipients, e.g. 'person1@company.com,person2@company.com'."
        )
    return recipients


def send_email(subject, text_body, html_body=None):
    """Sends an email. html_body is optional — if provided, the email is
    sent as both HTML and plain text (clients that can't render HTML
    automatically fall back to text_body)."""
    recipients = _get_recipients()
    method = os.environ.get("EMAIL_METHOD", "resend").lower()

    if method == "smtp":
        _send_via_smtp(subject, text_body, recipients, html_body)
    elif method == "resend":
        _send_via_resend(subject, text_body, recipients, html_body)
    else:
        raise RuntimeError(f"Unknown EMAIL_METHOD: '{method}'. Must be 'resend' or 'smtp'.")


def _send_via_resend(subject, text_body, recipients, html_body=None):
    api_key = os.environ["RESEND_API_KEY"]
    sender = os.environ.get("ALERT_EMAIL_FROM", "onboarding@resend.dev")

    if sender == "onboarding@resend.dev" and len(recipients) > 1:
        print(
            "WARNING: you are using Resend's test sender with multiple "
            "recipients. This will likely fail for every recipient other "
            "than the account's own email. Verify a domain in Resend, or "
            "switch to SMTP.",
        )

    payload = {"from": sender, "to": recipients, "subject": subject, "text": text_body}
    if html_body:
        payload["html"] = html_body

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()


def _send_via_smtp(subject, text_body, recipients, html_body=None):
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    username = os.environ["SMTP_USERNAME"]
    password = os.environ["SMTP_PASSWORD"]
    sender = os.environ.get("ALERT_EMAIL_FROM", username)

    if html_body:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))
    else:
        msg = MIMEText(text_body, "plain", "utf-8")

    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)

    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls()
        server.login(username, password)
        server.sendmail(sender, recipients, msg.as_string())
