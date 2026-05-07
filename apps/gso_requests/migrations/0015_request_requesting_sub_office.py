from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gso_requests', '0014_request_not_applicable'),
    ]

    operations = [
        migrations.AddField(
            model_name='request',
            name='requesting_sub_office',
            field=models.CharField(
                blank=True,
                help_text='Per-request sub office/department (e.g., IT, Marine Bio).',
                max_length=255,
            ),
        ),
    ]
