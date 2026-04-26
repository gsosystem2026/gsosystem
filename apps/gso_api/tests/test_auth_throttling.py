import os

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from apps.gso_api.views import ThrottledTokenObtainPairView, ThrottledTokenRefreshView


@override_settings(
    REST_FRAMEWORK={
        'DEFAULT_AUTHENTICATION_CLASSES': [
            'rest_framework_simplejwt.authentication.JWTAuthentication',
            'rest_framework.authentication.SessionAuthentication',
        ],
        'DEFAULT_PERMISSION_CLASSES': [
            'rest_framework.permissions.IsAuthenticated',
        ],
        'DEFAULT_THROTTLE_CLASSES': [
            'rest_framework.throttling.AnonRateThrottle',
            'rest_framework.throttling.UserRateThrottle',
            'rest_framework.throttling.ScopedRateThrottle',
        ],
        'DEFAULT_THROTTLE_RATES': {
            'anon': '1000/minute',
            'user': '1000/minute',
            'auth_token': '2/minute',
            'auth_refresh': '2/minute',
            'notification_write': '1000/minute',
        },
        'DEFAULT_RENDERER_CLASSES': [
            'rest_framework.renderers.JSONRenderer',
        ],
        'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
        'PAGE_SIZE': 20,
    }
)
class AuthTokenThrottlingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.username = 'throttle-user'
        self.password = 'StrongPass123!'
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email='throttle@example.com',
        )

    def test_token_obtain_endpoint_smoke(self):
        payload = {
            'username': self.username,
            'password': self.password,
        }
        url = '/api/v1/auth/token/'

        first = self.client.post(url, payload, format='json')
        self.assertEqual(first.status_code, 200)
        self.assertIn('access', first.json())
        self.assertIn('refresh', first.json())

    def test_token_refresh_endpoint_smoke(self):
        obtain_url = '/api/v1/auth/token/'
        obtain = self.client.post(
            obtain_url,
            {'username': self.username, 'password': self.password},
            format='json',
        )
        self.assertEqual(obtain.status_code, 200)
        refresh_token = obtain.json()['refresh']

        refresh_url = '/api/v1/auth/token/refresh/'
        first = self.client.post(refresh_url, {'refresh': refresh_token}, format='json')
        self.assertEqual(first.status_code, 200)
        self.assertIn('access', first.json())

    def test_token_obtain_view_has_scoped_throttling(self):
        self.assertEqual(ThrottledTokenObtainPairView.throttle_scope, 'auth_token')
        self.assertIn(ScopedRateThrottle, ThrottledTokenObtainPairView.throttle_classes)

    def test_token_refresh_view_has_scoped_throttling(self):
        self.assertEqual(ThrottledTokenRefreshView.throttle_scope, 'auth_refresh')
        self.assertIn(ScopedRateThrottle, ThrottledTokenRefreshView.throttle_classes)

