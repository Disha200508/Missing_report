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

    # Support WhatsApp messages (which bypass India TRAI DLT trial SMS template restrictions)
    is_whatsapp = from_num.startswith("whatsapp:") or os.environ.get("TWILIO_WHATSAPP", "").lower() in ("1", "true")
    dest = f"whatsapp:{to_num}" if (is_whatsapp and not to_num.startswith("whatsapp:")) else to_num
    sender = from_num if from_num.startswith("whatsapp:") else (f"whatsapp:{from_num}" if is_whatsapp else from_num)

    try:
        from twilio.rest import Client
        Client(sid, token).messages.create(body=body, from_=sender, to=dest)
        return "sent", None
    except Exception as exc:
        err_msg = str(exc)
        if "Invalid template name" in err_msg or "predefined SMS templates" in err_msg:
            err_msg += " (India TRAI regulation requires DLT templates for SMS. To deliver free without templates, use Twilio WhatsApp Sandbox by setting TWILIO_FROM=whatsapp:+14155238886)."
        return "failed", err_msg


def send_email_via_api(to_addr: str, subject: str, body: str) -> tuple[str, str | None] | None:
    """Send email via HTTP API (Resend or SendGrid) over port 443 to bypass cloud SMTP port blocks."""
    resend_key = os.environ.get("RESEND_API_KEY", "").strip()
    if resend_key:
        try:
            import requests
            sender = os.environ.get("RESEND_FROM", "").strip() or "MPIS Alerts <onboarding@resend.dev>"
            r = requests.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                json={"from": sender, "to": [to_addr.strip()], "subject": subject, "text": body},
                timeout=15,
            )
            if r.status_code in (200, 201):
                return "sent", None
            return "failed", f"Resend API error ({r.status_code}): {r.text}"
        except Exception as exc:
            return "failed", f"Resend error: {exc}"

    sendgrid_key = os.environ.get("SENDGRID_API_KEY", "").strip()
    if sendgrid_key:
        try:
            import requests
            sender = os.environ.get("SENDGRID_FROM", "").strip() or os.environ.get("SMTP_FROM", "").strip()
            if not sender:
                return "not_configured", "Set SENDGRID_FROM with your verified sender email address."
            r = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {sendgrid_key}", "Content-Type": "application/json"},
                json={
                    "personalizations": [{"to": [{"email": to_addr.strip()}]}],
                    "from": {"email": sender},
                    "subject": subject,
                    "content": [{"type": "text/plain", "value": body}],
                },
                timeout=15,
            )
            if r.status_code in (200, 202):
                return "sent", None
            return "failed", f"SendGrid error ({r.status_code}): {r.text}"
        except Exception as exc:
            return "failed", f"SendGrid error: {exc}"

    return None


def send_email(to_addr: str, subject: str, body: str) -> tuple[str, str | None]:
    """Send Email via HTTP API or SMTP (forcing IPv4). Returns (status, error_message)."""
    # Prefer HTTP API (Resend / SendGrid) if configured, as cloud providers like Render block raw SMTP ports
    api_result = send_email_via_api(to_addr, subject, body)
    if api_result is not None:
        return api_result

    host = os.environ.get("SMTP_HOST", "").strip()
    port = int(os.environ.get("SMTP_PORT", "587") or 587)
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASS", "").strip()
    sender = os.environ.get("SMTP_FROM", "").strip() or user

    if not (host and user and password and sender):
        return "not_configured", "Set SMTP_HOST, SMTP_USER, and SMTP_PASS (or RESEND_API_KEY) to send emails."

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_addr.strip()
    msg.set_content(body)

    # Force IPv4 socket binding to avoid [Errno 101] Network is unreachable on cloud IPv6 containers
    source_addr = ("0.0.0.0", 0)

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=15, source_address=source_addr) as server:
                server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15, source_address=source_addr) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(user, password)
                server.send_message(msg)
        return "sent", None
    except Exception as exc:
        err_msg = str(exc)
        if "Network is unreachable" in err_msg or "101" in err_msg or "timed out" in err_msg.lower():
            err_msg += " (Note: Render free tier blocks outbound SMTP ports. To bypass, add RESEND_API_KEY from resend.com in Render Environment)."
        return "failed", err_msg
