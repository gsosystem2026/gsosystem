from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gso_reports', '0004_successindicator_targeting'),
        ('gso_accounts', '0008_user_ipmt_profile_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='IPMTDraft',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.PositiveSmallIntegerField()),
                ('month', models.PositiveSmallIntegerField()),
                ('rows_json', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('personnel', models.ForeignKey(limit_choices_to={'role': 'PERSONNEL'}, on_delete=django.db.models.deletion.CASCADE, related_name='ipmt_drafts', to='gso_accounts.user')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ipmt_drafts_updated', to='gso_accounts.user')),
            ],
            options={
                'verbose_name': 'IPMT draft',
                'verbose_name_plural': 'IPMT drafts',
                'ordering': ['-updated_at'],
                'unique_together': {('personnel', 'year', 'month')},
            },
        ),
    ]

