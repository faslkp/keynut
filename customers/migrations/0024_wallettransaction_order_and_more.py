# Generated by Django 5.1.6 on 2025-03-26 08:45

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0023_alter_wallettransaction_transaction_id'),
        ('orders', '0018_alter_order_status_alter_payment_payment_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='wallettransaction',
            name='order',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='orders.order'),
        ),
        migrations.AlterField(
            model_name='wallettransaction',
            name='transaction_id',
            field=models.UUIDField(default=uuid.UUID('978e229e-0a1a-46ce-8b42-3aafe35f8354'), unique=True),
        ),
    ]
