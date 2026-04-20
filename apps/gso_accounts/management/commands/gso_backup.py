"""
Backup database (SQLite file copy or PostgreSQL pg_dump) and optional JSON export.

Usage:
  python manage.py gso_backup              # DB backup + JSON export
  python manage.py gso_backup --db-only    # DB backup only (SQLite copy or pg_dump)
  python manage.py gso_backup --json-only  # JSON export only (any DB engine)
  python manage.py gso_backup --keep 10    # override retention (default: GSO_BACKUP_KEEP env or 7)

After each run, old dated files are pruned per type: keep the newest N files
(db_*.sqlite3, pg_*.dump, data_*.json). Rotating N files is safer than a single
"replace" file — you can roll back to a previous day.

PostgreSQL requires `pg_dump` on PATH (PostgreSQL client tools).
Backup directory: GSO_BACKUP_DIR in .env or project_root/backups

Schedule daily (e.g. 2 AM): cron / Task Scheduler
"""
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Backup SQLite or PostgreSQL database and/or export critical data to JSON."

    def add_arguments(self, parser):
        parser.add_argument(
            '--db-only',
            action='store_true',
            help='Only backup database (no JSON export).',
        )
        parser.add_argument(
            '--json-only',
            action='store_true',
            help='Only export data to JSON (no DB backup).',
        )
        parser.add_argument(
            '--keep',
            type=int,
            default=None,
            metavar='N',
            help='Keep N newest files per backup type (db/pg/json). Overrides GSO_BACKUP_KEEP env.',
        )

    def handle(self, *args, **options):
        db_only = options['db_only']
        json_only = options['json_only']
        keep = options['keep']
        if keep is None:
            keep = getattr(settings, 'GSO_BACKUP_KEEP', 7)
        keep = max(1, min(100, int(keep)))

        backup_dir = self._backup_dir()
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')

        if not options['json_only']:
            self._backup_database(backup_dir, ts)
        if not options['db_only']:
            self._export_json(backup_dir, ts)

        self._prune_rotations(backup_dir, keep)

        self.stdout.write(self.style.SUCCESS(f'Backup completed. Directory: {backup_dir}'))

    def _prune_rotations(self, backup_dir: Path, keep: int):
        """Keep the newest `keep` files for each backup family; delete older ones."""
        families = [
            ('db_*.sqlite3', 'SQLite DB copies'),
            ('pg_*.dump', 'PostgreSQL dumps'),
            ('data_*.json', 'JSON exports'),
        ]
        for pattern, label in families:
            paths = sorted(backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
            for old in paths[keep:]:
                try:
                    old.unlink()
                    self.stdout.write(f'Pruned old {label}: {old.name}')
                except OSError as e:
                    self.stdout.write(self.style.WARNING(f'Could not remove {old}: {e}'))

    def _backup_dir(self):
        path = getattr(settings, 'GSO_BACKUP_DIR', None)
        return Path(path) if path else Path(settings.BASE_DIR) / 'backups'

    def _backup_database(self, backup_dir, ts):
        db = settings.DATABASES.get('default', {})
        engine = (db.get('ENGINE') or '').lower()
        if 'sqlite' in engine:
            self._backup_sqlite(backup_dir, ts, db)
        elif 'postgresql' in engine or 'postgres' in engine:
            self._backup_postgresql(backup_dir, ts)
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'Unknown database engine; skipping file backup. Engine: {db.get("ENGINE")}'
                )
            )

    def _backup_sqlite(self, backup_dir, ts, db):
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
        self.stdout.write(f'Copied SQLite DB to {dest}')

    def _pg_connection_uri(self):
        """Connection URI for pg_dump (DATABASE_URL or built from DATABASES)."""
        url = (os.environ.get('DATABASE_URL') or '').strip()
        if url:
            return url
        db = settings.DATABASES.get('default', {})
        name = db.get('NAME')
        if not name:
            return None
        user = db.get('USER') or ''
        password = db.get('PASSWORD') or ''
        host = db.get('HOST') or 'localhost'
        port = str(db.get('PORT') or '5432')
        u = quote(str(user), safe='')
        p = quote(str(password), safe='')
        if user and password:
            auth = f'{u}:{p}@'
        elif user:
            auth = f'{u}@'
        else:
            auth = ''
        return f'postgresql://{auth}{host}:{port}/{name}'

    def _backup_postgresql(self, backup_dir, ts):
        uri = self._pg_connection_uri()
        if not uri:
            self.stdout.write(self.style.WARNING('Could not build PostgreSQL connection URI; skipping pg_dump.'))
            return
        dest = backup_dir / f'pg_{ts}.dump'
        # Custom format (-Fc) for pg_restore; works with connection URI as last arg
        try:
            proc = subprocess.run(
                ['pg_dump', '-Fc', '-f', str(dest), uri],
                capture_output=True,
                text=True,
                timeout=3600,
            )
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(
                    'pg_dump not found. Install PostgreSQL client tools and ensure pg_dump is on PATH, '
                    'or use your host’s dashboard backups (Supabase/Neon). JSON export still ran if not --db-only.'
                )
            )
            return
        except subprocess.TimeoutExpired:
            self.stdout.write(self.style.ERROR('pg_dump timed out.'))
            return
        if proc.returncode != 0:
            self.stdout.write(self.style.ERROR(f'pg_dump failed (exit {proc.returncode}): {proc.stderr or proc.stdout}'))
            return
        self.stdout.write(f'PostgreSQL custom-format dump written to {dest}')

    def _export_json(self, backup_dir, ts):
        from django.contrib.auth import get_user_model
        from apps.gso_requests.models import Request, RequestFeedback
        from apps.gso_reports.models import WorkAccomplishmentReport
        from apps.gso_inventory.models import InventoryItem

        User = get_user_model()
        data = {'exported_at': datetime.now().isoformat(), 'version': getattr(settings, 'GSO_APP_VERSION', '1.0')}

        data['users'] = list(
            User.objects.values('id', 'username', 'first_name', 'last_name', 'role', 'unit_id', 'is_active', 'date_joined')
        )
        data['requests'] = list(
            Request.objects.values(
                'id', 'requestor_id', 'unit_id', 'title', 'status', 'is_emergency', 'created_at', 'updated_at'
            )
        )
        data['request_feedback'] = list(
            RequestFeedback.objects.values(
                'id', 'request_id', 'user_id', 'cc1', 'cc2', 'cc3',
                'sqd1', 'sqd2', 'sqd3', 'sqd4', 'sqd5', 'sqd6', 'sqd7', 'sqd8', 'sqd9',
                'suggestions', 'created_at'
            )
        )
        data['war'] = list(
            WorkAccomplishmentReport.objects.values(
                'id', 'request_id', 'personnel_id', 'period_start', 'period_end', 'summary', 'accomplishments', 'created_at'
            )
        )
        data['inventory'] = list(
            InventoryItem.objects.values('id', 'unit_id', 'name', 'quantity', 'unit_of_measure', 'updated_at')
        )

        dest = backup_dir / f'data_{ts}.json'
        with open(dest, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        self.stdout.write(f'Exported JSON to {dest}')
