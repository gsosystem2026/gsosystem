"""
Verify database connectivity (SQLite or PostgreSQL / Neon via DATABASE_URL).

Usage:
  python manage.py gso_db_check

Exit code 0 if the connection works, 1 on failure.

Local dev: leave DATABASE_URL unset → SQLite.
Neon / production: set DATABASE_URL in .env, then run this command before migrate.
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Test DB connection (SQLite or PostgreSQL e.g. Neon). Exit 1 on failure.'

    def handle(self, *args, **options):
        cfg = connection.settings_dict
        engine = cfg.get('ENGINE', '')
        if 'sqlite' in engine:
            self.stdout.write(self.style.NOTICE('Engine: SQLite'))
            self.stdout.write(f"  File: {cfg.get('NAME')}")
        else:
            self.stdout.write(self.style.NOTICE('Engine: PostgreSQL'))
            self.stdout.write(f"  Host: {cfg.get('HOST') or '(default)'}")
            self.stdout.write(f"  Port: {cfg.get('PORT') or '(default)'}")
            self.stdout.write(f"  Name: {cfg.get('NAME')}")

        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            one = cursor.fetchone()[0]
        if one != 1:
            self.stderr.write(self.style.ERROR('Unexpected SELECT 1 result.'))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS('Connection OK (SELECT 1).'))
        self.stdout.write('Next: python manage.py migrate')
