from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from apps.gso_notifications.models import Notification
from apps.gso_accounts.views import _invite_email_preflight_issues
from apps.gso_reports.models import WorkAccomplishmentReport
from apps.gso_requests.models import Request, RequestAssignment
from apps.gso_units.models import Unit


class NotificationFlowSafetyTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.unit = Unit.objects.create(name='Repair and Maintenance', code='repair', is_active=True)
        self.requestor = User.objects.create_user(
            username='requestor1',
            password='Pass1234!',
            role=User.Role.REQUESTOR,
        )
        self.staff = User.objects.create_user(
            username='staff1',
            password='Pass1234!',
            role=User.Role.GSO_OFFICE,
            unit=self.unit,
        )
        self.notification = Notification.objects.create(
            user=self.requestor,
            title='Test Notification',
            message='Please check update',
            link='https://evil.example/phish',
            read=False,
        )

    def test_notification_go_requires_post(self):
        self.client.force_login(self.requestor)
        url = reverse('gso_accounts:notification_go', args=[self.notification.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_notification_go_marks_read_and_falls_back_on_unsafe_link(self):
        self.client.force_login(self.requestor)
        url = reverse('gso_accounts:notification_go', args=[self.notification.pk])
        response = self.client.post(url, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('gso_accounts:requestor_dashboard'))
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.read)

    def test_mark_all_read_requires_post(self):
        self.client.force_login(self.requestor)
        url = reverse('gso_accounts:notification_mark_all_read')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)


class ProfileRedirectSafetyTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username='requestor2',
            password='Pass1234!',
            role=User.Role.REQUESTOR,
            email='initial@example.com',
            first_name='First',
            last_name='User',
        )

    def test_profile_edit_ignores_unsafe_referer(self):
        self.client.force_login(self.user)
        url = reverse('gso_accounts:requestor_profile_edit')
        payload = {
            'first_name': 'Updated',
            'last_name': 'User',
            'email': 'updated@example.com',
            'avatar_code': 'man1',
        }
        response = self.client.post(
            url,
            payload,
            HTTP_REFERER='https://evil.example/steal',
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('gso_accounts:requestor_dashboard'))


class StaffHistoryAndWarPermissionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.unit = Unit.objects.create(name='Repair and Maintenance', code='repair', is_active=True)
        self.requestor = User.objects.create_user(
            username='requestor-history',
            password='Pass1234!',
            role=User.Role.REQUESTOR,
        )
        self.personnel = User.objects.create_user(
            username='personnel-history',
            password='Pass1234!',
            role=User.Role.PERSONNEL,
            unit=self.unit,
        )
        self.gso = User.objects.create_user(
            username='gso-history',
            password='Pass1234!',
            role=User.Role.GSO_OFFICE,
            unit=self.unit,
        )
        self.completed_request = Request.objects.create(
            requestor=self.requestor,
            unit=self.unit,
            title='Completed request',
            description='Done task',
            status=Request.Status.COMPLETED,
        )
        self.other_request = Request.objects.create(
            requestor=self.requestor,
            unit=self.unit,
            title='Not assigned to personnel',
            description='Done task 2',
            status=Request.Status.COMPLETED,
        )
        RequestAssignment.objects.create(
            request=self.completed_request,
            personnel=self.personnel,
            assigned_by=self.gso,
        )

    def test_personnel_history_shows_only_assigned_requests(self):
        self.client.force_login(self.personnel)
        response = self.client.get(reverse('gso_accounts:staff_request_history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.completed_request.display_id)
        self.assertNotContains(response, self.other_request.display_id)

    def test_personnel_cannot_create_war(self):
        self.client.force_login(self.personnel)
        response = self.client.get(
            reverse('gso_accounts:staff_war_add', args=[self.completed_request.pk]),
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse('gso_accounts:staff_request_detail', args=[self.completed_request.pk]),
        )
        self.assertFalse(
            WorkAccomplishmentReport.objects.filter(request=self.completed_request, personnel=self.personnel).exists()
        )

    def test_gso_can_open_war_create_page(self):
        self.client.force_login(self.gso)
        response = self.client.get(
            reverse('gso_accounts:staff_war_add', args=[self.completed_request.pk]),
            follow=False,
        )
        self.assertEqual(response.status_code, 200)


class InviteEmailPreflightTests(TestCase):
    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST='smtp.example.com',
        EMAIL_HOST_USER='mailer@example.com',
        EMAIL_HOST_PASSWORD='secret',
        DEFAULT_FROM_EMAIL='mailer@example.com',
        GSO_SITE_URL='https://gso.example.com',
    )
    def test_preflight_passes_for_valid_smtp_settings(self):
        issues = _invite_email_preflight_issues()
        self.assertEqual(issues, [])

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend',
        DEFAULT_FROM_EMAIL='',
        GSO_SITE_URL='bad-url',
    )
    def test_preflight_reports_expected_issues(self):
        issues = _invite_email_preflight_issues()
        self.assertTrue(any('development backend' in issue for issue in issues))
        self.assertTrue(any('DEFAULT_FROM_EMAIL' in issue for issue in issues))
        self.assertTrue(any('absolute URL' in issue for issue in issues))

    @override_settings(
        DEBUG=False,
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST='smtp.example.com',
        EMAIL_HOST_USER='mailer@example.com',
        EMAIL_HOST_PASSWORD='secret',
        DEFAULT_FROM_EMAIL='mailer@example.com',
        GSO_SITE_URL='http://gso.example.com',
    )
    def test_preflight_requires_https_when_debug_false(self):
        issues = _invite_email_preflight_issues()
        self.assertTrue(any('must use https' in issue for issue in issues))

