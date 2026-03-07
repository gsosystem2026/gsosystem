"""
Reset passwords for sample users to sample123. Use if login fails.
Usage: python manage.py reset_sample_passwords
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

SAMPLE_USERNAMES = ["requestor", "unithead", "personnel", "gsooffice", "director"]
SAMPLE_PASSWORD = "sample123"


class Command(BaseCommand):
    help = "Reset passwords for sample users to 'sample123' (use if login fails)"

    def handle(self, *args, **options):
        for username in SAMPLE_USERNAMES:
            try:
                user = User.objects.get(username=username)
                user.set_password(SAMPLE_PASSWORD)
                user.save()
                self.stdout.write(self.style.SUCCESS(f"  Password reset for: {username}"))
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"  User '{username}' not found. Run: python manage.py create_sample_users")
                )
        self.stdout.write("")
        self.stdout.write("Try logging in with username: requestor  password: sample123")
