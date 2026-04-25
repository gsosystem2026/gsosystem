from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gso_units', '0001_initial'),
        ('gso_reports', '0003_workaccomplishmentreport_labor_cost_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='successindicator',
            name='target_position',
            field=models.CharField(blank=True, default='', help_text='Optional position this indicator applies to, e.g. Carpenter. Leave blank for all positions.', max_length=150),
        ),
        migrations.AddField(
            model_name='successindicator',
            name='target_unit',
            field=models.ForeignKey(blank=True, help_text='Optional GSO service unit this indicator applies to. Leave blank for all units.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='success_indicators', to='gso_units.unit'),
        ),
    ]

