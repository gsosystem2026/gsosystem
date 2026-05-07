from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from apps.gso_requests.models import Request, MotorpoolTripData
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
            "custom_full_name": "Requestor Test",
            "custom_contact_number": "09123456789",
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

    def test_motorpool_submission_without_location_or_request_type(self):
        payload = {
            "description": "Official travel to PSU campus.",
            "units": "motorpool",
            "custom_full_name": "Requestor Test",
            "custom_contact_number": "09123456789",
            "motorpool_places_to_be_visited": "PSU Main Campus",
            "motorpool_itinerary_of_travel": "Campus visit and return",
            "motorpool_trip_datetime": "2030-06-01T09:30",
            "motorpool_number_of_days": "1",
            "motorpool_number_of_passengers": "3",
        }
        response = self.client.post(reverse("gso_requests:requestor_request_new"), data=payload)
        self.assertEqual(response.status_code, 302)
        location = response.get("Location", "")
        self.assertIn("motorpool_print=1", location)
        self.assertIn("request_pk=", location)
        req = Request.objects.get(requestor=self.requestor)
        self.assertEqual(req.unit_id, self.motorpool.id)
        self.assertEqual(req.location, "")
        self.assertFalse(req.labor)
        self.assertFalse(req.materials)
        self.assertFalse(req.others)
        self.assertEqual(req.title, "Official travel to PSU campus.")
        self.assertTrue(MotorpoolTripData.objects.filter(request=req).exists())

    def test_motorpool_validation_error_keeps_modal_units_from_post_body(self):
        """Invalid POST from dashboard modal has units only in POST, not GET; context must stay Motorpool."""
        payload = {
            "description": "",
            "units": "motorpool",
            "custom_full_name": "Requestor Test",
            "custom_contact_number": "09123456789",
        }
        response = self.client.post(reverse("gso_requests:requestor_request_new"), data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Motorpool Trip Plan")

    def test_motorpool_submit_accepts_datetime_local_format(self):
        """HTML datetime-local submits YYYY-MM-DDTHH:MM; Django must parse it (was failing validation)."""
        payload = {
            "description": "Field work",
            "units": "motorpool",
            "custom_full_name": "Requestor Test",
            "custom_contact_number": "09123456789",
            "motorpool_places_to_be_visited": "PSU Main Campus",
            "motorpool_itinerary_of_travel": "Field work and return",
            "motorpool_trip_datetime": "2030-06-01T09:30",
            "motorpool_number_of_days": "2",
            "motorpool_number_of_passengers": "5",
        }
        response = self.client.post(reverse("gso_requests:requestor_request_new"), data=payload)
        self.assertEqual(response.status_code, 302)
        req = Request.objects.get(requestor=self.requestor)
        trip = MotorpoolTripData.objects.get(request=req)
        self.assertIsNotNone(trip.trip_datetime)
        self.assertEqual(trip.number_of_days, 2)

    def test_blocks_motorpool_transport_mixed_with_other_units(self):
        Unit.objects.filter(code="motorpool").update(code="motorpool-legacy")  # free slug
        mp = Unit.objects.create(name="Motorpool", code="motorpool-transport", is_active=True)
        payload = self._base_payload()
        payload["units"] = "motorpool-transport,utility"

        response = self.client.post(reverse("gso_requests:requestor_request_new"), data=payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Motorpool requests must be submitted separately because they use a different request form.",
        )
