import logging

import requests
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_gso_email(
    *,
    subject,
    message,
    recipient_list,
    from_email=None,
    html_message=None,
    fail_silently=False,
):
    """
    Send email via SendGrid API when configured; fallback to Django SMTP.
    """
    sender = (from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "") or "").strip()
    recipients = [r for r in (recipient_list or []) if (r or "").strip()]

    if not recipients:
        return 0

    try:
        sendgrid_api_key = (getattr(settings, "SENDGRID_API_KEY", "") or "").strip()
        if sendgrid_api_key:
            payload = {
                "personalizations": [{"to": [{"email": addr} for addr in recipients]}],
                "from": {"email": sender},
                "subject": subject,
                "content": [{"type": "text/plain", "value": message or ""}],
            }
            if html_message:
                payload["content"].append({"type": "text/html", "value": html_message})

            timeout = int(getattr(settings, "EMAIL_TIMEOUT", 10))
            response = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {sendgrid_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=timeout,
            )
            if response.status_code >= 400:
                body_preview = (response.text or "")[:300]
                raise RuntimeError(
                    f"SendGrid API error: status={response.status_code}, body={body_preview}"
                )
            return len(recipients)

        return send_mail(
            subject=subject,
            message=message,
            from_email=sender or None,
            recipient_list=recipients,
            fail_silently=fail_silently,
            html_message=html_message,
        )
    except Exception:
        if fail_silently:
            logger.exception("Email send failed silently.")
            return 0
        raise
