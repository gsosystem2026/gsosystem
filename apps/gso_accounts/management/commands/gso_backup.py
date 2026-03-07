"""
Phase 9.1: Backup SQLite database and optionally export critical data to JSON.
Uses SQLite when DATABASE_URL is not set. For PostgreSQL, only JSON export is done.

Usage:
  python manage.py gso_backup              # SQLite copy + JSON export
  python manage.py gso_backup --db-only   # SQLite file copy only
  python manage.py gso_backup --json-only # JSON export only (works with any DB)

Backup directory: set GSO_BACKUP_DIR in .env or defaults to project_root/backups
Schedule: run daily via cron/Task Scheduler, e.g. 0 2 * * * (2 AM)
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Backup SQLite DB and/or export critical data to JSON (Phase 9.1)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--db-only',
            action='store_true',
            help='Only copy the SQLite database file (no JSON export).',
        )
        parser.add_argument(
            '--json-only',
            action='store_true',
            help='Only export data to JSON (no DB file copy).',
        )

    def handle(self, *args, **options):
        db_only = options['db_only']
        json_only = options['json_only']

        backup_dir = self._backup_dir()
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')

        if not options['json_only']:
            self._backup_sqlite(backup_dir, ts)
        if not options['db_only']:
            self._export_json(backup_dir, ts)

        self.stdout.write(self.style.SUCCESS(f'Backup completed. Directory: {backup_dir}'))

    def _backup_dir(self):
        path = getattr(settings, 'GSO_BACKUP_DIR', None)
        return Path(path) if path else Path(settings.BASE_DIR) / 'backups'

    def _backup_sqlite(self, backup_dir, ts):
        db = settings.DATABASES.get('default', {})
        if db.get('ENGINE') != 'django.db.backends.sqlite3':
            self.stdout.write('Database is not SQLite; skipping DB file copy. Use --json-only for data export.')
            return
        name = db.get('NAME')
        if not name:
            self.stdout.write(self.style.WARNING('No database NAME configured.'))
            return
        src = Path(name)
        if not src.is_absolute():
            src = Path(settings.BASE_DIR) / name
        if not src.exists():
            self.stdout.write(self.style.WARNING(f'SQLite file not found: {src}'))
            return
        dest = backup_dir / f'db_{ts}.sqlite3'
        shutil.copy2(src, dest)
        self.stdout.write(f'Copied DB to {dest}')

    def _export_json(self, backup_dir, ts):
        from django.contrib.auth import get_user_model
        from apps.gso_requests.models import Request, RequestFeedback
        from apps.gso_reports.models import WorkAccomplishmentReport
        from apps.gso_inventory.models import InventoryItem

        User = get_user_model()
        data = {'exported_at': datetime.now().isoformat(), 'version': getattr(settings, 'GSO_APP_VERSION', '1.0')}

        # Users: id, username, role, unit_id, is_active (no passwords)
        data['users'] = list(
            User.objects.values('id', 'username', 'first_name', 'last_name', 'role', 'unit_id', 'is_active', 'date_joined')
        )
        # Requests: minimal for recovery reference
        data['requests'] = list(
            Request.objects.values(
                'id', 'requestor_id', 'unit_id', 'title', 'status', 'is_emergency', 'created_at', 'updated_at'
            )
        )
        # Request feedback (CSM)
        data['request_feedback'] = list(
            RequestFeedback.objects.values(
                'id', 'request_id', 'user_id', 'cc1', 'cc2', 'cc3',
                'sqd1', 'sqd2', 'sqd3', 'sqd4', 'sqd5', 'sqd6', 'sqd7', 'sqd8', 'sqd9',
                'suggestions', 'created_at'
            )
        )
        # WAR
        data['war'] = list(
            WorkAccomplishmentReport.objects.values(
                'id', 'request_id', 'personnel_id', 'period_start', 'period_end', 'summary', 'accomplishments', 'created_at'
            )
        )
        # Inventory items
        data['inventory'] = list(
            InventoryItem.objects.values('id', 'unit_id', 'name', 'quantity', 'unit_of_measure', 'updated_at')
        )

        dest = backup_dir / f'data_{ts}.json'
        with open(dest, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        self.stdout.write(f'Exported JSON to {dest}')
