"""DRF authentication for integration API keys (besides JWT)."""

from django.utils import timezone

from rest_framework import authentication, exceptions

from apps.gso_accounts.models import UserAPIKey, resolve_user_api_key_from_raw, user_allow_api_credentials


def _extract_raw_key(request):
    """Parse Authorization: Api-Key <key> or X-Api-Key header."""
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if isinstance(auth, str) and auth.lower().startswith('api-key '):
        return auth[8:].strip()
    x_key = request.META.get('HTTP_X_API_KEY')
    if x_key:
        return x_key.strip()
    return None


class IntegrationAPIKeyAuthentication(authentication.BaseAuthentication):
    """
    Clients send either:
    - ``Authorization: Api-Key <full_secret>``
    - ``X-Api-Key: <full_secret>``
    """

    keyword = 'Api-Key'

    def authenticate(self, request):
        raw = _extract_raw_key(request)
        if not raw:
            return None

        key_obj = resolve_user_api_key_from_raw(raw)
        if key_obj is None:
            raise exceptions.AuthenticationFailed('Invalid API key.')

        user = key_obj.user
        if not user_allow_api_credentials(user):
            raise exceptions.AuthenticationFailed('API key user account is inactive or restricted.')

        UserAPIKey.objects.filter(pk=key_obj.pk).update(last_used_at=timezone.now())

        request.integration_api_key = key_obj
        return (user, key_obj)

    def authenticate_header(self, request):
        return self.keyword
