"""Throttling scoped to integration API key authentication."""

from rest_framework.throttling import SimpleRateThrottle

from apps.gso_accounts.models import UserAPIKey


class IntegrationApiKeyThrottle(SimpleRateThrottle):
    """Separate bucket for requests authenticated via ``UserAPIKey``."""

    scope = 'api_key'

    def get_cache_key(self, request, view):
        auth = getattr(request, 'auth', None)
        if not isinstance(auth, UserAPIKey):
            return None
        ident = auth.pk
        return self.cache_format % {'scope': self.scope, 'ident': ident}
