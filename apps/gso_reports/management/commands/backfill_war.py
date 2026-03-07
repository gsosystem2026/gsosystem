from django.core.management.base import BaseCommand

from apps.gso_requests.models import Request
from apps.gso_reports.models import ensure_war_for_request


class Command(BaseCommand):
    help = "Backfill Work Accomplishment Reports (WAR) for existing completed requests."

    def handle(self, *args, **options):
        qs = Request.objects.filter(status=Request.Status.COMPLETED)
        total = qs.count()
        created_for = 0
        for idx, req in enumerate(qs, start=1):
            before = req.work_accomplishment_reports.count()
            ensure_war_for_request(req, created_by=None)
            after = req.work_accomplishment_reports.count()
            if after > before:
                created_for += 1
            if idx % 50 == 0:
                self.stdout.write(f"Processed {idx}/{total} requests...")
        self.stdout.write(self.style.SUCCESS(f"Backfill complete. WARs created/updated for {created_for} request(s)."))

