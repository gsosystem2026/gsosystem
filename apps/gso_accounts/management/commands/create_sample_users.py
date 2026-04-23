"""
Create sample users (one per role) and the 4 GSO units for testing.
Usage: python manage.py create_sample_users
All sample passwords: sample123
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model

from apps.gso_units.models import Unit

User = get_user_model()

# Unit name, code
UNITS = [
    ("Repair & Maintenance", "repair"),
    ("Utility", "utility"),
    ("Electrical", "electrical"),
    ("Motorpool", "motorpool"),
]

SAMPLE_PASSWORD = "sample123"

# username, role, unit_code (or None), first_name, last_name
USERS = [
    ("requestor", User.Role.REQUESTOR, "repair", "Alex", "Requestor"),
    ("unithead", User.Role.UNIT_HEAD, "repair", "Jordan", "Unit Head"),
    ("personnel", User.Role.PERSONNEL, "repair", "Sam", "Personnel"),
    ("gsooffice", User.Role.GSO_OFFICE, None, "Morgan", "GSO Office"),
    ("director", User.Role.DIRECTOR, None, "Casey", "Director"),
]


class Command(BaseCommand):
    help = "Create 4 GSO units and sample users (one per role). Passwords: sample123"

    @transaction.atomic
    def handle(self, *args, **options):
        # Create units
        created_units = {}
        for name, code in UNITS:
            unit, created = Unit.objects.get_or_create(
                code=code,
                defaults={"name": name, "is_active": True},
            )
            created_units[code] = unit
            if created:
                self.stdout.write(self.style.SUCCESS(f"  Unit: {name} ({code})"))
        self.stdout.write("Units ready.")

        # Create users
        for username, role, unit_code, first_name, last_name in USERS:
            if User.objects.filter(username=username).exists():
                self.stdout.write(self.style.WARNING(f"  User '{username}' already exists, skipped."))
                continue
            unit = created_units.get(unit_code) if unit_code else None
            User.objects.create_user(
                username=username,
                password=SAMPLE_PASSWORD,
                first_name=first_name,
                last_name=last_name,
                role=role,
                unit=unit,
                is_staff=(role in (User.Role.GSO_OFFICE, User.Role.DIRECTOR)),
                is_active=True,
            )
            self.stdout.write(self.style.SUCCESS(f"  User: {username} ({role}) - {first_name} {last_name}"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Done. Sample users (password: sample123):"))
        self.stdout.write("  requestor  -> Requestor (requestor dashboard)")
        self.stdout.write("  unithead   -> Unit Head (staff sidebar)")
        self.stdout.write("  personnel  -> Personnel (staff sidebar)")
        self.stdout.write("  gsooffice  -> GSO Office (staff sidebar)")
        self.stdout.write("  director   -> Director (staff sidebar)")
        self.stdout.write("  Log in at: http://127.0.0.1:8000/accounts/login/")
