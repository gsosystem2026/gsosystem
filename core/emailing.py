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
    Send email using configured provider.
    - smtp (default): Django email backend
    - resend: Resend HTTP API
    """
    provider = (getattr(settings, "EMAIL_PROVIDER", "smtp") or "smtp").strip().lower()
    sender = (from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "") or "").strip()
    recipients = [r for r in (recipient_list or []) if (r or "").strip()]

    if not recipients:
        return 0

    try:
        if provider == "resend":
            api_key = (getattr(settings, "RESEND_API_KEY", "") or "").strip()
            api_url = (getattr(settings, "RESEND_API_URL", "") or "").strip()
            if not api_key:
                raise RuntimeError("RESEND_API_KEY is missing.")
            if not api_url:
                raise RuntimeError("RESEND_API_URL is missing.")
            if not sender:
                raise RuntimeError("DEFAULT_FROM_EMAIL is required for Resend.")

            payload = {
                "from": sender,
                "to": recipients,
                "subject": subject,
                "text": message or "",
            }
            if html_message:
                payload["html"] = html_message

            timeout = int(getattr(settings, "EMAIL_TIMEOUT", 10))
            response = requests.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=timeout,
            )
            if response.status_code >= 400:
                body_preview = (response.text or "")[:300]
                raise RuntimeError(
                    f"Resend API error: status={response.status_code}, body={body_preview}"
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
            logger.exception("Email send failed silently (provider=%s).", provider)
            return 0
        raise
