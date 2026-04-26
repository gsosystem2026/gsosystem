from django.test import SimpleTestCase

from apps.gso_reports.views import IPMTReportView


class IPMTPreviewMergeTests(SimpleTestCase):
    def test_merge_keeps_draft_and_appends_new_preview_content(self):
        view = IPMTReportView()
        draft_rows = [
            {
                "indicator": "Indicator A",
                "accomplishments": ["Edited draft accomplishment"],
                "comment": "Edited",
            }
        ]
        preview_rows = [
            {
                "indicator": "Indicator A",
                "accomplishments": ["Edited draft accomplishment", "New WAR item"],
                "comment": "Complied",
            },
            {
                "indicator": "Indicator B",
                "accomplishments": ["Brand new indicator item"],
                "comment": "Complied",
            },
        ]

        merged = view._merge_draft_with_preview(draft_rows=draft_rows, preview_rows=preview_rows)

        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["indicator"], "Indicator A")
        self.assertEqual(
            merged[0]["accomplishments"],
            ["Edited draft accomplishment", "New WAR item"],
        )
        self.assertEqual(merged[0]["comment"], "Edited")
        self.assertEqual(merged[1]["indicator"], "Indicator B")

    def test_merge_handles_empty_draft(self):
        view = IPMTReportView()
        preview_rows = [
            {
                "indicator": "Indicator A",
                "accomplishments": ["Item 1"],
                "comment": "Complied",
            }
        ]
        merged = view._merge_draft_with_preview(draft_rows=[], preview_rows=preview_rows)
        self.assertEqual(merged, preview_rows)
