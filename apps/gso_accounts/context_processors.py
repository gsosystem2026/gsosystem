"""Context processors for requestor layout (notifications + profile modal)."""

from .forms import RequestorProfileForm


def requestor_notifications(request):
    """Add requestor_notifications and user_notifications for header dropdowns (requestor + staff)."""
    try:
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            return {'requestor_notifications': [], 'user_notifications': [], 'unread_notification_count': 0}
    except Exception:
        return {'requestor_notifications': [], 'user_notifications': [], 'unread_notification_count': 0}
    from apps.gso_notifications.models import Notification
    qs = list(Notification.objects.filter(user=request.user).order_by('-created_at')[:50])
    unread_count = Notification.objects.filter(user=request.user, read=False).count()
    return {
        'requestor_notifications': qs,
        'user_notifications': qs,
        'unread_notification_count': unread_count,
    }


def requestor_profile_form(request):
    """Add requestor_profile_form for profile modal (Edit profile) on requestor layout."""
    try:
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            return {}
        if getattr(request.user, 'role', None) != 'REQUESTOR':
            return {}
    except Exception:
        return {}
    return {'requestor_profile_form': RequestorProfileForm(instance=request.user)}
