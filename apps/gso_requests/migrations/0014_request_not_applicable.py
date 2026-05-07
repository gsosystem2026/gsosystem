from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gso_requests', '0013_alter_request_attachment_motorpooltripdata'),
    ]

    operations = [
        migrations.AddField(
            model_name='request',
            name='not_applicable_reason',
            field=models.TextField(
                blank=True,
                help_text='Reason/remarks when Director or OIC marks request as not applicable.',
            ),
        ),
        migrations.AlterField(
            model_name='request',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', 'Draft'),
                    ('SUBMITTED', 'Submitted'),
                    ('ASSIGNED', 'Assigned'),
                    ('DIRECTOR_APPROVED', 'Approved'),
                    ('NOT_APPLICABLE', 'Not Applicable'),
                    ('INSPECTION', 'Inspection'),
                    ('IN_PROGRESS', 'In Progress'),
                    ('ON_HOLD', 'On Hold'),
                    ('DONE_WORKING', 'Done working'),
                    ('COMPLETED', 'Completed'),
                    ('CANCELLED', 'Cancelled'),
                ],
                default='DRAFT',
                max_length=32,
            ),
        ),
    ]
