"""
Delivery helpers for SMS (Twilio) and Email (SMTP) alerts.
All credentials are read from environment variables (or backend/.env).
"""
import os
import re
import smtplib
from email.message import EmailMessage


def normalize_phone(raw: str, default_country: str | None = None) -> str:
    """Normalize local phone numbers to E.164 format (e.g. 7618103393 -> +917618103393)."""
    country = (default_country or os.environ.get("DEFAULT_COUNTRY_CODE", "+91")).strip()
    cleaned = re.sub(r"[\s\-()]", "", (raw or "").strip())
    if not cleaned:
        return ""
    if cleaned.startswith("+"):
        return "+" + re.sub(r"\D", "", cleaned[1:])
    digits = re.sub(r"\D", "", cleaned)
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10 and country:
        return f"{country}{digits}"
    return "+" + digits


def send_sms(phone: str, body: str) -> tuple[str, str | None]:
    """Send SMS via Twilio. Returns (status, error_message)."""
    sid = os.environ.get("TWILIO_SID", "").strip()
    token = os.environ.get("TWILIO_TOKEN", "").strip()
    from_num = os.environ.get("TWILIO_FROM", "").strip()
    if not (sid and token and from_num):
        return "not_configured", "Set TWILIO_SID, TWILIO_TOKEN, and TWILIO_FROM to send SMS."

    to_num = normalize_phone(phone)
    if not to_num:
        return "failed", "Invalid phone number."
    try:
        from twilio.rest import Client
        Client(sid, token).messages.create(body=body, from_=from_num, to=to_num)
        return "sent", None
    except Exception as exc:
        return "failed", str(exc)


def send_email(to_addr: str, subject: str, body: str) -> tuple[str, str | None]:
    """Send Email via SMTP (STARTTLS on 587 or SSL on 465). Returns (status, error_message)."""
    host = os.environ.get("SMTP_HOST", "").strip()
    port = int(os.environ.get("SMTP_PORT", "587") or 587)
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASS", "").strip()
    sender = os.environ.get("SMTP_FROM", "").strip() or user

    if not (host and user and password and sender):
        return "not_configured", "Set SMTP_HOST, SMTP_USER, and SMTP_PASS to send emails."

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_addr.strip()
    msg.set_content(body)

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=15) as server:
                server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(user, password)
                server.send_message(msg)
        return "sent", None
    except Exception as exc:
        return "failed", str(exc)
