"""Permission helpers for staff features (integration API keys, etc.)."""


def can_manage_integration_api_keys(user):
    """Director, GSO Office, or superuser may create/revoke integration API keys."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    role = getattr(user, 'role', None)
    from apps.gso_accounts.models import User

    return role in (User.Role.DIRECTOR, User.Role.GSO_OFFICE)


def is_account_management_director_ui(user):
    """Director-level UI on Account Management (OIC, add user, edit user, lifecycle)."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    return getattr(user, 'is_director', False)
