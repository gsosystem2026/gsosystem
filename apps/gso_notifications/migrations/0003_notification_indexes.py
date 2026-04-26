from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gso_notifications', '0002_add_device_token'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['user'], name='gso_notific_user_id_3f08da_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['user', 'read'], name='gso_notific_user_id_760dfa_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['user', '-created_at'], name='gso_notific_user_id_a6443f_idx'),
        ),
    ]
