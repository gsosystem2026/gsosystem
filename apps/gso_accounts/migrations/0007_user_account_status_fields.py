from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gso_accounts', '0006_user_office_department'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='account_status',
            field=models.CharField(choices=[('ACTIVE', 'Active'), ('SUSPENDED', 'Suspended'), ('DEACTIVATED', 'Deactivated')], default='ACTIVE', help_text='Lifecycle status for login access control.', max_length=16),
        ),
        migrations.AddField(
            model_name='user',
            name='restriction_reason_category',
            field=models.CharField(blank=True, default='', help_text='Reason category when account is suspended/deactivated.', max_length=32),
        ),
        migrations.AddField(
            model_name='user',
            name='restriction_reason_details',
            field=models.TextField(blank=True, default='', help_text='Detailed reason when account is suspended/deactivated.'),
        ),
        migrations.AddField(
            model_name='user',
            name='status_changed_at',
            field=models.DateTimeField(blank=True, help_text='Timestamp when account status last changed.', null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='status_changed_by',
            field=models.ForeignKey(blank=True, help_text='Director who changed this account status.', null=True, on_delete=models.SET_NULL, related_name='status_changed_users', to='gso_accounts.user'),
        ),
        migrations.AddField(
            model_name='user',
            name='suspended_until',
            field=models.DateTimeField(blank=True, help_text='Optional end time for suspension.', null=True),
        ),
    ]

