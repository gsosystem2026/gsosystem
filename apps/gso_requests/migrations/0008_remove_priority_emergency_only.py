# Generated migration: merge priority into emergency-only (Unit Head decides)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gso_requests', '0007_add_is_emergency'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='request',
            name='priority',
        ),
    ]
