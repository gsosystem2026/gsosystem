from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.gso_requests.models import Request, MotorpoolTripData
from apps.gso_units.models import Unit


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class MotorpoolRequestorPrintAccessTests(TestCase):
    """Owning requestors can open Motorpool HTML print routes; others get 404."""

    def setUp(self):
        self.motorpool = Unit.objects.create(name="Motorpool", code="motorpool", is_active=True)
        self.utility = Unit.objects.create(name="Utility", code="utility", is_active=True)
        User = get_user_model()
        self.owner = User.objects.create_user(
            username="mp_owner",
            password="Pass1234!",
            role=User.Role.REQUESTOR,
            email="mp-owner@example.com",
        )
        self.other_requestor = User.objects.create_user(
            username="mp_other",
            password="Pass1234!",
            role=User.Role.REQUESTOR,
            email="mp-other@example.com",
        )
        self.req = Request.objects.create(
            requestor=self.owner,
            unit=self.motorpool,
            title="Trip for meeting",
            description="Campus visit",
            status=Request.Status.SUBMITTED,
        )
        MotorpoolTripData.objects.create(request=self.req)

    def test_owner_can_print_request_and_trip_ticket(self):
        self.client.login(username="mp_owner", password="Pass1234!")
        for name in ("gso_requests:motorpool_print_request", "gso_requests:motorpool_print_trip_ticket"):
            res = self.client.get(reverse(name, kwargs={"pk": self.req.pk}))
            self.assertEqual(res.status_code, 200, msg=name)

    def test_non_owner_requestor_gets_404(self):
        self.client.login(username="mp_other", password="Pass1234!")
        url = reverse("gso_requests:motorpool_print_request", kwargs={"pk": self.req.pk})
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_non_motorpool_request_404_even_for_owner(self):
        non_mp = Request.objects.create(
            requestor=self.owner,
            unit=self.utility,
            title="Leak fix",
            description="Washroom tap",
            location="Block A",
            status=Request.Status.SUBMITTED,
        )
        self.client.login(username="mp_owner", password="Pass1234!")
        url = reverse("gso_requests:motorpool_print_request", kwargs={"pk": non_mp.pk})
        self.assertEqual(self.client.get(url).status_code, 404)
