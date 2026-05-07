from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.gso_reports.models import WorkAccomplishmentReport, ensure_war_for_request
from apps.gso_requests.models import Request
from apps.gso_units.models import Unit


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class NotApplicableFlowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.unit = Unit.objects.create(name="Utility", code="utility", is_active=True)
        self.requestor = User.objects.create_user(
            username="na_requestor",
            password="Pass1234!",
            role=User.Role.REQUESTOR,
            office_department="Registrar",
        )
        self.director = User.objects.create_user(
            username="na_director",
            password="Pass1234!",
            role=User.Role.DIRECTOR,
            is_staff=True,
        )
        self.req = Request.objects.create(
            requestor=self.requestor,
            unit=self.unit,
            title="Fix sink",
            description="Leaking sink in building A.",
            location="Building A",
            status=Request.Status.ASSIGNED,
            custom_full_name="Requestor Name",
            custom_contact_number="09123456789",
        )

    def test_director_can_mark_not_applicable_with_reason(self):
        self.client.force_login(self.director)
        response = self.client.post(
            reverse("gso_accounts:staff_request_not_applicable", args=[self.req.pk]),
            data={"reason": "Request duplicates an already completed maintenance ticket."},
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, Request.Status.NOT_APPLICABLE)
        self.assertIn("duplicates", self.req.not_applicable_reason)
        self.assertEqual(WorkAccomplishmentReport.objects.filter(request=self.req).count(), 0)

    def test_not_applicable_requires_reason(self):
        self.client.force_login(self.director)
        response = self.client.post(
            reverse("gso_accounts:staff_request_not_applicable", args=[self.req.pk]),
            data={"reason": "   "},
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, Request.Status.ASSIGNED)
        self.assertEqual(self.req.not_applicable_reason, "")

    def test_ensure_war_does_not_create_for_not_applicable(self):
        self.req.status = Request.Status.NOT_APPLICABLE
        self.req.not_applicable_reason = "No longer relevant."
        self.req.save(update_fields=["status", "not_applicable_reason", "updated_at"])

        ensure_war_for_request(self.req, created_by=self.director)
        self.assertFalse(WorkAccomplishmentReport.objects.filter(request=self.req).exists())
