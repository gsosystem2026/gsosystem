"""
Verify email invite readiness for production.

Usage:
  python manage.py gso_email_check
  python manage.py gso_email_check --to admin@example.com

Exit code:
  0 when preflight checks pass (and optional test email succeeds).
  1 when checks fail or test email send fails.
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.gso_accounts.views import _invite_email_preflight_issues
from core.emailing import send_gso_email


class Command(BaseCommand):
    help = 'Validate SMTP + GSO_SITE_URL for invite emails; optional test send.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            dest='to_email',
            default='',
            help='Optional test recipient email for a real send check.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Checking invite email readiness...'))
        self.stdout.write(f"  EMAIL_BACKEND: {getattr(settings, 'EMAIL_BACKEND', '')}")
        self.stdout.write(f"  DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', '')}")
        self.stdout.write(f"  GSO_SITE_URL: {getattr(settings, 'GSO_SITE_URL', '') or '(empty)'}")

        issues = _invite_email_preflight_issues()
        if issues:
            self.stderr.write(self.style.ERROR('Preflight issues found:'))
            for issue in issues:
                self.stderr.write(f'  - {issue}')
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS('Preflight checks passed.'))

        to_email = (options.get('to_email') or '').strip()
        if not to_email:
            self.stdout.write('Tip: pass --to you@example.com to verify real send.')
            return

        send_gso_email(
            subject='GSO Email Check - Invite Delivery Test',
            message='This is a test email from gso_email_check.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        self.stdout.write(self.style.SUCCESS(f'Test email sent to {to_email}.'))
