import os
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from openpyxl import Workbook

from apps.gso_requests.models import Request
from apps.gso_reports.models import WorkAccomplishmentReport
from apps.gso_units.models import Unit
from apps.gso_accounts.models import User


class LegacyWarImportCommandTests(TestCase):
    def _build_legacy_war_workbook(
        self,
        requesting_office="CTE",
        assigned_personnel="",
        workbook_unit_hint="",
    ):
        wb = Workbook()
        ws = wb.active
        ws.title = "APRIL 2025"
        ws.append(["Republic of the Philippines"])
        ws.append(["WORK ACCOMPLISHMENT REPORT"])
        ws.append([workbook_unit_hint] if workbook_unit_hint else [])
        ws.append([])
        ws.append([])
        ws.append([])
        ws.append([])
        ws.append([])
        ws.append([])
        ws.append(
            [
                "Date Started",
                "Date Completed",
                "Name of Activity",
                "Description",
                "Requesting Office ",
                "Assigned Personnel",
                "Status",
                "Material Cost",
                "Labor Cost",
                "Total Cost",
                "Control #",
            ]
        )
        ws.append(
            [
                "04/01/2025",
                "04/02/2025",
                "Setup sound system",
                "Setup and testing at hall.",
                requesting_office,
                assigned_personnel,
                "Done",
                "100.50",
                "50.00",
                "150.50",
                "03-192",
            ]
        )
        ws.append(["Total", 0, 0, 0])
        return wb

    def setUp(self):
        Unit.objects.create(name="Electrical", code="electrical", is_active=True)
        Unit.objects.create(name="Utility", code="utility", is_active=True)
        User.objects.create_user(
            username="cte_requestor",
            password="Pass1234!",
            role=User.Role.REQUESTOR,
            office_department="CTE",
            email="cte-requestor@example.com",
        )

    def test_dry_run_does_not_write(self):
        wb = self._build_legacy_war_workbook()
        fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        path = Path(temp_path)
        try:
            wb.save(path)
            wb.close()
            call_command(
                "gso_import_legacy_war",
                str(path),
                "--unit-code",
                "electrical",
                "--dry-run",
            )
        finally:
            try:
                path.unlink(missing_ok=True)
            except PermissionError:
                pass
        self.assertEqual(Request.objects.count(), 0)
        self.assertEqual(WorkAccomplishmentReport.objects.count(), 0)

    def test_apply_creates_request_and_war(self):
        wb = self._build_legacy_war_workbook()
        fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        path = Path(temp_path)
        try:
            wb.save(path)
            wb.close()
            call_command(
                "gso_import_legacy_war",
                str(path),
                "--unit-code",
                "electrical",
            )
        finally:
            try:
                path.unlink(missing_ok=True)
            except PermissionError:
                pass

        req = Request.objects.get()
        war = WorkAccomplishmentReport.objects.get()
        User = get_user_model()
        self.assertTrue(User.objects.filter(username="migrated_legacy").exists())
        self.assertTrue(User.objects.filter(username="migrated_requestor").exists())
        self.assertIn("[MIGRATED-LEGACY-WAR", req.description)
        self.assertEqual(req.status, Request.Status.COMPLETED)
        self.assertEqual(war.request_id, req.id)
        self.assertNotIn("[MIGRATED-LEGACY|", war.accomplishments)
        self.assertEqual(war.accomplishments, "Setup and testing at hall.")
        self.assertEqual(req.requestor.username, "cte_requestor")
        self.assertEqual(war.personnel.username, "migrated_legacy")

    def test_apply_creates_requestor_from_non_blank_unmatched_office(self):
        wb = self._build_legacy_war_workbook(requesting_office="Dean Office")
        fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        path = Path(temp_path)
        try:
            wb.save(path)
            wb.close()
            call_command(
                "gso_import_legacy_war",
                str(path),
                "--unit-code",
                "electrical",
            )
        finally:
            try:
                path.unlink(missing_ok=True)
            except PermissionError:
                pass

        req = Request.objects.get()
        self.assertTrue(req.requestor.username.startswith("migrated_req_dean_office"))
        self.assertEqual(req.requestor.office_department, "Dean Office")

    def test_apply_uses_generic_fallback_when_office_blank(self):
        wb = self._build_legacy_war_workbook(requesting_office="")
        fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        path = Path(temp_path)
        try:
            wb.save(path)
            wb.close()
            call_command(
                "gso_import_legacy_war",
                str(path),
                "--unit-code",
                "electrical",
            )
        finally:
            try:
                path.unlink(missing_ok=True)
            except PermissionError:
                pass

        req = Request.objects.get()
        self.assertEqual(req.requestor.username, "migrated_requestor")

    def test_apply_creates_personnel_from_non_blank_unmatched_name(self):
        wb = self._build_legacy_war_workbook(assigned_personnel="Juan Dela Cruz")
        fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        path = Path(temp_path)
        try:
            wb.save(path)
            wb.close()
            call_command(
                "gso_import_legacy_war",
                str(path),
                "--unit-code",
                "electrical",
            )
        finally:
            try:
                path.unlink(missing_ok=True)
            except PermissionError:
                pass

        war = WorkAccomplishmentReport.objects.get()
        self.assertTrue(war.personnel.username.startswith("migrated_per_juan_dela_cruz"))
        self.assertEqual(war.personnel.first_name, "Juan Dela Cruz")

    def test_apply_uses_generic_personnel_fallback_when_name_blank(self):
        wb = self._build_legacy_war_workbook(assigned_personnel="")
        fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        path = Path(temp_path)
        try:
            wb.save(path)
            wb.close()
            call_command(
                "gso_import_legacy_war",
                str(path),
                "--unit-code",
                "electrical",
            )
        finally:
            try:
                path.unlink(missing_ok=True)
            except PermissionError:
                pass

        war = WorkAccomplishmentReport.objects.get()
        self.assertEqual(war.personnel.username, "migrated_legacy")

    def test_import_blocks_when_workbook_unit_conflicts_with_selected_unit(self):
        wb = self._build_legacy_war_workbook(workbook_unit_hint="Utility")
        fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        path = Path(temp_path)
        try:
            wb.save(path)
            wb.close()
            with self.assertRaises(CommandError):
                call_command(
                    "gso_import_legacy_war",
                    str(path),
                    "--unit-code",
                    "electrical",
                )
        finally:
            try:
                path.unlink(missing_ok=True)
            except PermissionError:
                pass
