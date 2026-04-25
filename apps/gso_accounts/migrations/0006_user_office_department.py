from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gso_accounts', '0005_passwordresetotp'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='office_department',
            field=models.CharField(blank=True, default='', help_text='Office/Department for requestor accounts.', max_length=150),
        ),
    ]

