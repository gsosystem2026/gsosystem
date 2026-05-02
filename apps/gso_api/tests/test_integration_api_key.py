"""Tests for integration API key authentication."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from django.utils import timezone

from apps.gso_accounts.models import issue_user_api_key, resolve_user_api_key_from_raw, _api_key_hmac_digest

User = get_user_model()


class IntegrationApiKeyAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='api_test_user',
            email='api@test.local',
            password='test-pass-123',
            role=User.Role.REQUESTOR,
        )

    def test_resolve_and_revoke(self):
        _, raw = issue_user_api_key(self.user, created_by=self.user, label='t')
        self.assertTrue(raw.startswith('gso_'))
        obj = resolve_user_api_key_from_raw(raw)
        self.assertIsNotNone(obj)
        obj.revoked_at = timezone.now()
        obj.save(update_fields=['revoked_at'])
        self.assertIsNone(resolve_user_api_key_from_raw(raw))

    def test_wrong_key_digest_no_match(self):
        fake = 'gso_' + 'x' * 40
        self.assertIsNone(resolve_user_api_key_from_raw(fake))

    def test_requests_list_with_api_key_header(self):
        _, raw = issue_user_api_key(self.user, created_by=self.user, label='curl')
        url = reverse('api-requests-list')
        r = self.client.get(url, HTTP_AUTHORIZATION=f'Api-Key {raw}')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_requests_list_rejects_revoked_key(self):
        obj, raw = issue_user_api_key(self.user, created_by=self.user, label='x')
        obj.revoked_at = timezone.now()
        obj.save(update_fields=['revoked_at'])
        url = reverse('api-requests-list')
        r = self.client.get(url, HTTP_AUTHORIZATION=f'Api-Key {raw}')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_digest_is_stable(self):
        _, raw = issue_user_api_key(self.user, created_by=self.user)
        d1 = _api_key_hmac_digest(raw)
        d2 = _api_key_hmac_digest(raw)
        self.assertEqual(d1, d2)
