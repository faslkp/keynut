# Generated by Django 5.1.6 on 2025-03-28 05:42

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0024_wallettransaction_order_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wallettransaction',
            name='transaction_id',
            field=models.UUIDField(default=uuid.UUID('83acd519-0db2-455e-b6ae-105a06d2f38a'), unique=True),
        ),
    ]
