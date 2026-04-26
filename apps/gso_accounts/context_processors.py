"""Context processors for requestor layout (notifications + profile modal)."""

import logging

from django.core.cache import cache

from .forms import RequestorProfileForm

logger = logging.getLogger(__name__)
UNREAD_NOTIFICATION_CACHE_TTL_SECONDS = 30


def _unread_notification_cache_key(user_id):
    return f"notif_unread_count:{user_id}"


def requestor_notifications(request):
    """Add requestor_notifications and user_notifications for header dropdowns (requestor + staff)."""
    user = getattr(request, 'user', None)
    if not user or not getattr(user, 'is_authenticated', False):
        return {'requestor_notifications': [], 'user_notifications': [], 'unread_notification_count': 0}
    try:
        from apps.gso_notifications.models import Notification
        cache_key = _unread_notification_cache_key(user.id)
        unread_count = cache.get(cache_key)
        if unread_count is None:
            unread_count = Notification.objects.filter(user=user, read=False).count()
            cache.set(cache_key, unread_count, UNREAD_NOTIFICATION_CACHE_TTL_SECONDS)
        return {
            # Notification list is loaded lazily from API when dropdown opens.
            'requestor_notifications': [],
            'user_notifications': [],
            'unread_notification_count': unread_count,
        }
    except Exception:
        logger.exception(
            'Failed to load notification context (user_id=%s)',
            getattr(user, 'id', None),
        )
        return {'requestor_notifications': [], 'user_notifications': [], 'unread_notification_count': 0}


def requestor_profile_form(request):
    """Add requestor_profile_form for profile modal (Edit profile) on requestor layout."""
    user = getattr(request, 'user', None)
    if not user or not getattr(user, 'is_authenticated', False):
        return {}
    if getattr(user, 'role', None) != 'REQUESTOR':
        return {}
    try:
        return {'requestor_profile_form': RequestorProfileForm(instance=user)}
    except Exception:
        logger.exception(
            'Failed to build requestor profile form context (user_id=%s)',
            getattr(user, 'id', None),
        )
        return {}
