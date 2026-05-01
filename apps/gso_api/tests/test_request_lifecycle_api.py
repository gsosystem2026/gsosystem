from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.gso_requests.models import Request
from apps.gso_units.models import Unit
from apps.gso_inventory.models import InventoryItem


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
        self.inventory_item = InventoryItem.objects.create(
            unit=self.unit,
            name='Cement',
            quantity=10,
            unit_of_measure='pcs',
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

    def test_personnel_my_tasks_lists_active_assigned_only(self):
        self.client.force_authenticate(self.unit_head)
        self.client.post(
            f'/api/v1/requests/{self.request_obj.pk}/assign/',
            {'personnel_ids': [self.personnel.pk]},
            format='json',
        )
        self.client.force_authenticate(self.director)
        self.client.post(f'/api/v1/requests/{self.request_obj.pk}/approve/', {}, format='json')

        self.client.force_authenticate(self.personnel)
        r = self.client.get('/api/v1/requests/my-tasks/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 1)
        self.assertEqual(r.data[0]['id'], self.request_obj.pk)
        self.assertEqual(r.data[0]['status'], Request.Status.DIRECTOR_APPROVED)

    def test_non_personnel_my_tasks_forbidden(self):
        self.client.force_authenticate(self.requestor)
        r = self.client.get('/api/v1/requests/my-tasks/')
        self.assertEqual(r.status_code, 403)

    def test_request_chat_post_and_fetch_for_staff(self):
        self.client.force_authenticate(self.unit_head)
        self.client.post(
            f'/api/v1/requests/{self.request_obj.pk}/assign/',
            {'personnel_ids': [self.personnel.pk]},
            format='json',
        )
        self.request_obj.status = Request.Status.DIRECTOR_APPROVED
        self.request_obj.save(update_fields=['status', 'updated_at'])

        self.client.force_authenticate(self.personnel)
        post_res = self.client.post(
            f'/api/v1/requests/{self.request_obj.pk}/messages/',
            {'message': 'Started inspection on-site.'},
            format='json',
        )
        self.assertEqual(post_res.status_code, 201)
        self.assertEqual(post_res.data['message'], 'Started inspection on-site.')

        get_res = self.client.get(f'/api/v1/requests/{self.request_obj.pk}/messages/')
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(len(get_res.data), 1)
        self.assertEqual(get_res.data[0]['message'], 'Started inspection on-site.')

    def test_request_chat_forbidden_for_requestor(self):
        self.request_obj.status = Request.Status.DIRECTOR_APPROVED
        self.request_obj.save(update_fields=['status', 'updated_at'])
        self.client.force_authenticate(self.requestor)
        res = self.client.get(f'/api/v1/requests/{self.request_obj.pk}/messages/')
        self.assertEqual(res.status_code, 403)

    def test_personnel_submit_material_request(self):
        self.client.force_authenticate(self.unit_head)
        self.client.post(
            f'/api/v1/requests/{self.request_obj.pk}/assign/',
            {'personnel_ids': [self.personnel.pk]},
            format='json',
        )
        self.request_obj.status = Request.Status.DIRECTOR_APPROVED
        self.request_obj.save(update_fields=['status', 'updated_at'])

        self.client.force_authenticate(self.personnel)
        post_res = self.client.post(
            f'/api/v1/requests/{self.request_obj.pk}/material-requests/',
            {'item_id': self.inventory_item.pk, 'quantity': 2, 'notes': 'For repaint prep'},
            format='json',
        )
        self.assertEqual(post_res.status_code, 201)
        self.assertEqual(post_res.data['item_name'], 'Cement')
        self.assertEqual(post_res.data['quantity'], 2)

        list_res = self.client.get(f'/api/v1/requests/{self.request_obj.pk}/material-requests/')
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(len(list_res.data), 1)

