from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from apps.gso_requests.models import Request
from apps.gso_units.models import Unit


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class MultiUnitSubmissionRuleTests(TestCase):
    def setUp(self):
        self.utility = Unit.objects.create(name="Utility", code="utility", is_active=True)
        self.electrical = Unit.objects.create(name="Electrical", code="electrical", is_active=True)
        self.motorpool = Unit.objects.create(name="Motorpool", code="motorpool", is_active=True)
        User = get_user_model()
        self.requestor = User.objects.create_user(
            username="req_multi",
            password="Pass1234!",
            role=User.Role.REQUESTOR,
            email="req-multi@example.com",
        )
        self.client.login(username="req_multi", password="Pass1234!")

    def _base_payload(self):
        return {
            "description": "General service request for facilities support.",
            "location": "Main campus",
            "labor": "on",
        }

    def test_allows_multiple_non_motorpool_units(self):
        payload = self._base_payload()
        payload["units"] = "utility,electrical"

        response = self.client.post(reverse("gso_requests:requestor_request_new"), data=payload)

        self.assertEqual(response.status_code, 302)
        created = Request.objects.filter(requestor=self.requestor).order_by("unit__code")
        self.assertEqual(created.count(), 2)
        self.assertEqual([r.unit.code for r in created], ["electrical", "utility"])

    def test_blocks_motorpool_mixed_with_other_units(self):
        payload = self._base_payload()
        payload["units"] = "motorpool,utility"

        response = self.client.post(reverse("gso_requests:requestor_request_new"), data=payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Motorpool requests must be submitted separately because they use a different request form.",
        )
        self.assertEqual(Request.objects.filter(requestor=self.requestor).count(), 0)
