import logging

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
    Send email via Django SMTP backend (production path).
    """
    sender = (from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "") or "").strip()
    recipients = [r for r in (recipient_list or []) if (r or "").strip()]

    if not recipients:
        return 0

    try:
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
