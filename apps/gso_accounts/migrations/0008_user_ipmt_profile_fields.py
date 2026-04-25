from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gso_accounts', '0007_user_account_status_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='employment_status',
            field=models.CharField(blank=True, default='', help_text='Employment status for staff/personnel reports, e.g. Job Order, Permanent.', max_length=100),
        ),
        migrations.AddField(
            model_name='user',
            name='position_title',
            field=models.CharField(blank=True, default='', help_text='Position title for staff/personnel reports, e.g. Admin Aide-III.', max_length=150),
        ),
    ]

