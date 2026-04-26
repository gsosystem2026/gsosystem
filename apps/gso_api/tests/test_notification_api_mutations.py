from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.gso_notifications.models import Notification


class NotificationApiMutationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='notif_api_user',
            password='Pass1234!',
            role=User.Role.REQUESTOR,
        )
        self.other_user = User.objects.create_user(
            username='notif_api_other',
            password='Pass1234!',
            role=User.Role.REQUESTOR,
        )
        self.mine = Notification.objects.create(
            user=self.user,
            title='Mine',
            message='My notification',
            read=False,
        )
        self.other = Notification.objects.create(
            user=self.other_user,
            title='Other',
            message='Other notification',
            read=False,
        )

    def test_mark_read_updates_own_notification(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(f'/api/v1/notifications/{self.mine.pk}/mark_read/', {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.mine.refresh_from_db()
        self.assertTrue(self.mine.read)

    def test_mark_read_cannot_update_others_notification(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(f'/api/v1/notifications/{self.other.pk}/mark_read/', {}, format='json')
        self.assertEqual(response.status_code, 404)
        self.other.refresh_from_db()
        self.assertFalse(self.other.read)

    def test_mark_all_read_updates_all_for_current_user_only(self):
        self.client.force_authenticate(self.user)
        response = self.client.post('/api/v1/notifications/mark_all_read/', {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.mine.refresh_from_db()
        self.other.refresh_from_db()
        self.assertTrue(self.mine.read)
        self.assertFalse(self.other.read)

