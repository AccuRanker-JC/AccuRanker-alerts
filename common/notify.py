"""
Delt mail-afsendelse for alle agenter. Understøtter to metoder, valgt via
env-variablen EMAIL_METHOD ("resend" eller "smtp"), og altid flere modtagere
via ALERT_EMAILS (kommasepareret liste).

Resend uden domæneverificering ("onboarding@resend.dev") kan KUN sende til
den mail-adresse, Resend-kontoen selv er oprettet med - det holder derfor
ikke i praksis, hvis en kunde vil have flere modtagere. Til det skal enten
Resend-domænet verificeres, eller SMTP bruges i stedet.
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
            "ALERT_EMAILS er ikke sat. Skal være en kommasepareret liste af "
            "modtagere, fx 'person1@firma.dk,person2@firma.dk'."
        )
    return recipients


def send_email(subject, text_body, html_body=None):
    """Sender en mail. html_body er valgfri - hvis den angives, sendes mailen
    som både HTML og ren tekst (klienter der ikke kan vise HTML falder
    automatisk tilbage til text_body)."""
    recipients = _get_recipients()
    method = os.environ.get("EMAIL_METHOD", "resend").lower()

    if method == "smtp":
        _send_via_smtp(subject, text_body, recipients, html_body)
    elif method == "resend":
        _send_via_resend(subject, text_body, recipients, html_body)
    else:
        raise RuntimeError(f"Ukendt EMAIL_METHOD: '{method}'. Skal være 'resend' eller 'smtp'.")


def _send_via_resend(subject, text_body, recipients, html_body=None):
    api_key = os.environ["RESEND_API_KEY"]
    sender = os.environ.get("ALERT_EMAIL_FROM", "onboarding@resend.dev")

    if sender == "onboarding@resend.dev" and len(recipients) > 1:
        print(
            "ADVARSEL: du bruger Resends test-afsender med flere modtagere. "
            "Det vil sandsynligvis fejle for alle modtagere udover kontoens "
            "egen e-mail. Verificér et domæne i Resend, eller skift til SMTP.",
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
