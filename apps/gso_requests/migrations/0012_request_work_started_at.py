from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gso_requests', '0011_request_location'),
    ]

    operations = [
        migrations.AddField(
            model_name='request',
            name='work_started_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
