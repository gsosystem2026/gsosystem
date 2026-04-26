from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.gso_requests.models import Request
from apps.gso_units.models import Unit


class RequestLifecycleApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.client = APIClient()

        self.unit = Unit.objects.create(name='Repair and Maintenance', code='repair', is_active=True)

        self.requestor = User.objects.create_user(
            username='req_api_user',
            password='Pass1234!',
            role=User.Role.REQUESTOR,
            unit=self.unit,
        )
        self.unit_head = User.objects.create_user(
            username='uh_api_user',
            password='Pass1234!',
            role=User.Role.UNIT_HEAD,
            unit=self.unit,
        )
        self.personnel = User.objects.create_user(
            username='personnel_api_user',
            password='Pass1234!',
            role=User.Role.PERSONNEL,
            unit=self.unit,
        )
        self.director = User.objects.create_user(
            username='director_api_user',
            password='Pass1234!',
            role=User.Role.DIRECTOR,
        )

        self.request_obj = Request.objects.create(
            requestor=self.requestor,
            unit=self.unit,
            title='Fix classroom door',
            description='Door hinge issue',
            location='Building A',
            status=Request.Status.SUBMITTED,
        )

    def test_full_lifecycle_assign_approve_status(self):
        # Unit Head assigns personnel.
        self.client.force_authenticate(self.unit_head)
        assign_response = self.client.post(
            f'/api/v1/requests/{self.request_obj.pk}/assign/',
            {'personnel_ids': [self.personnel.pk]},
            format='json',
        )
        self.assertEqual(assign_response.status_code, 200)
        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.status, Request.Status.ASSIGNED)

        # Director approves request.
        self.client.force_authenticate(self.director)
        approve_response = self.client.post(
            f'/api/v1/requests/{self.request_obj.pk}/approve/',
            {},
            format='json',
        )
        self.assertEqual(approve_response.status_code, 200)
        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.status, Request.Status.DIRECTOR_APPROVED)

        # Personnel moves status to IN_PROGRESS.
        self.client.force_authenticate(self.personnel)
        status_response = self.client.post(
            f'/api/v1/requests/{self.request_obj.pk}/status/',
            {'status': Request.Status.IN_PROGRESS},
            format='json',
        )
        self.assertEqual(status_response.status_code, 200)
        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.status, Request.Status.IN_PROGRESS)

