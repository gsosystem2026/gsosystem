from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.gso_requests.models import Request
from apps.gso_units.models import Unit


@override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }
)
class RequestReportViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.unit = Unit.objects.create(name='Test Unit', code='tu', is_active=True)
        self.requestor = User.objects.create_user(
            username='rr_requestor',
            password='Pass1234!',
            role=User.Role.REQUESTOR,
            office_department='Registrar',
            first_name='Pat',
            last_name='Lee',
        )
        self.director = User.objects.create_user(
            username='rr_director',
            password='Pass1234!',
            role=User.Role.DIRECTOR,
            is_staff=True,
        )
        self.req_done = Request.objects.create(
            requestor=self.requestor,
            unit=self.unit,
            title='Fix door hinge',
            description='Lab 2',
            status=Request.Status.COMPLETED,
            labor=True,
        )
        self.req_open = Request.objects.create(
            requestor=self.requestor,
            unit=self.unit,
            title='Paint hallway',
            status=Request.Status.SUBMITTED,
        )

    def test_redirects_unit_head_and_requestor(self):
        User = get_user_model()
        head = User.objects.create_user(
            username='rr_uhead',
            password='Pass1234!',
            role=User.Role.UNIT_HEAD,
            unit=self.unit,
        )
        url = reverse('gso_accounts:staff_work_reports_request_report')
        self.client.force_login(self.requestor)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 302)
        self.client.force_login(head)
        r2 = self.client.get(url)
        self.assertEqual(r2.status_code, 302)

    def test_lists_completed_only_and_filter_by_unit(self):
        url = reverse('gso_accounts:staff_work_reports_request_report')
        self.client.force_login(self.director)

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.req_done.display_id)
        self.assertNotContains(r, self.req_open.display_id)

        r2 = self.client.get(url, {'unit': self.unit.pk})
        self.assertEqual(r2.status_code, 200)
        self.assertContains(r2, self.req_done.display_id)

        other = Unit.objects.create(name='Other', code='ot', is_active=True)
        r3 = self.client.get(url, {'unit': other.pk})
        self.assertEqual(r3.status_code, 200)
        self.assertNotContains(r3, self.req_done.display_id)

    def test_excel_download(self):
        url = reverse('gso_accounts:staff_work_reports_request_report')
        self.client.force_login(self.director)
        r = self.client.get(url, {'download': 'excel', 'q': 'door'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertIn('attachment', r['Content-Disposition'])
