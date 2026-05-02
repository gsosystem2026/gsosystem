import os
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from openpyxl import Workbook

from apps.gso_accounts.models import User
from apps.gso_reports.models import IPMTDraft
from apps.gso_units.models import Unit


class LegacyIPMTImportCommandTests(TestCase):
    def _build_ipmt_workbook(self, unit_text="Electrical", employee_name="Sam Personnel"):
        wb = Workbook()
        ws = wb.active
        ws.title = "IPMT 2025-04"
        ws.append([None, "INDIVIDUAL PERFORMANCE MONITORING TOOLS"])
        ws.append([None, None])
        ws.append([None, None])
        ws.append([None, None])
        ws.append(["College/Campus/Department/Unit :", unit_text])
        ws.append(["Name of Employee :", employee_name])
        ws.append(["Status of Employment :", "Job Order"])
        ws.append(["Position :", "Maintainer"])
        ws.append(["Month:", "APRIL 1-30, 2025"])
        ws.append(["*Success Indicators", "Actual Accomplishments", "Comments / Remarks"])
        ws.append(["Indicator A", "Did A1", "Complied"])
        ws.append([None, "Did A2", "Complied"])
        ws.append(["Indicator B", "Did B1", "Complied"])
        ws.append(["*Based on the IPCR", None, None])
        return wb

    def setUp(self):
        self.unit = Unit.objects.create(name="Electrical", code="electrical", is_active=True)
        Unit.objects.create(name="Utility", code="utility", is_active=True)
        self.personnel = User.objects.create_user(
            username="sam_personnel",
            password="Pass1234!",
            role=User.Role.PERSONNEL,
            first_name="Sam",
            last_name="Personnel",
            unit=self.unit,
            email="sam@example.com",
            is_active=True,
        )

    def test_dry_run_does_not_write(self):
        wb = self._build_ipmt_workbook()
        fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        path = Path(temp_path)
        try:
            wb.save(path)
            wb.close()
            call_command(
                "gso_import_legacy_ipmt",
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
        self.assertEqual(IPMTDraft.objects.count(), 0)

    def test_apply_creates_ipmt_draft(self):
        wb = self._build_ipmt_workbook()
        fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        path = Path(temp_path)
        try:
            wb.save(path)
            wb.close()
            call_command(
                "gso_import_legacy_ipmt",
                str(path),
                "--unit-code",
                "electrical",
            )
        finally:
            try:
                path.unlink(missing_ok=True)
            except PermissionError:
                pass
        draft = IPMTDraft.objects.get()
        self.assertEqual(draft.personnel_id, self.personnel.id)
        self.assertEqual(draft.year, 2025)
        self.assertEqual(draft.month, 4)
        self.assertEqual(len(draft.rows_json), 2)
        self.assertEqual(draft.rows_json[0]["indicator"], "Indicator A")
        self.assertEqual(draft.rows_json[0]["accomplishments"], ["Did A1", "Did A2"])

    def test_apply_blocks_conflicting_unit(self):
        wb = self._build_ipmt_workbook(unit_text="Utility")
        fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        path = Path(temp_path)
        try:
            wb.save(path)
            wb.close()
            with self.assertRaises(CommandError):
                call_command(
                    "gso_import_legacy_ipmt",
                    str(path),
                    "--unit-code",
                    "electrical",
                )
        finally:
            try:
                path.unlink(missing_ok=True)
            except PermissionError:
                pass

    def test_command_rejects_war_workbook(self):
        from apps.gso_accounts.tests.test_legacy_war_import_command import LegacyWarImportCommandTests

        wb = LegacyWarImportCommandTests()._build_legacy_war_workbook()
        fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
        os.close(fd)
        path = Path(temp_path)
        try:
            wb.save(path)
            wb.close()
            with self.assertRaises(CommandError) as ctx:
                call_command(
                    "gso_import_legacy_ipmt",
                    str(path),
                    "--unit-code",
                    "electrical",
                    "--dry-run",
                )
            self.assertIn("WAR", str(ctx.exception))
        finally:
            try:
                path.unlink(missing_ok=True)
            except PermissionError:
                pass
