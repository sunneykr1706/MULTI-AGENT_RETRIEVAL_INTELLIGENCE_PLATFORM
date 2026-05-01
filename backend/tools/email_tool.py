"""Email tool — sends email via SendGrid REST API."""
import logging
import requests

logger = logging.getLogger(__name__)

SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"


def send_email(to: str, subject: str, body: str, api_key: str, from_email: str) -> str:
    """
    Send a plain-text email via SendGrid.

    Requirements:
    - SENDGRID_API_KEY in .env  (free tier: 100 emails/day)
    - SENDGRID_FROM_EMAIL must be a verified sender in your SendGrid account
    """
    if not api_key:
        return (
            "Email not sent: SENDGRID_API_KEY is not configured. "
            "Get a free key at https://sendgrid.com (100 emails/day free)."
        )
    if not from_email:
        return "Email not sent: SENDGRID_FROM_EMAIL is not configured."
    if not to or "@" not in to:
        return f"Email not sent: invalid recipient address '{to}'."

    payload = {
        "personalizations": [{"to": [{"email": to}]}],
        "from": {"email": from_email},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(SENDGRID_API_URL, json=payload, headers=headers, timeout=15)
        if resp.status_code in (200, 202):
            logger.info("Email sent to %s via SendGrid", to)
            return f"Email sent successfully to {to} with subject '{subject}'."
        else:
            logger.warning("SendGrid error %s: %s", resp.status_code, resp.text[:200])
            return f"SendGrid error {resp.status_code}: {resp.text[:200]}"
    except Exception as exc:
        logger.error("Email tool error: %s", exc)
        return f"Failed to send email: {exc}"
