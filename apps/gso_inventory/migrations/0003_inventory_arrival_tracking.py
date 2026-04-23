from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gso_inventory', '0002_add_material_request'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventoryitem',
            name='arrival_date',
            field=models.DateField(
                blank=True,
                help_text='Most recent date this item arrived (updated on stock-in).',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='inventorytransaction',
            name='arrival_date',
            field=models.DateField(
                blank=True,
                help_text='Date this stock batch arrived (for stock-in).',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='inventorytransaction',
            name='delivery_reference',
            field=models.CharField(blank=True, help_text='DR/PO/reference number', max_length=120),
        ),
        migrations.AddField(
            model_name='inventorytransaction',
            name='supplier_name',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
