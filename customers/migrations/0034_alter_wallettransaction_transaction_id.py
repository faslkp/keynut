# Generated by Django 5.1.6 on 2025-03-29 04:32

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0033_alter_wallettransaction_transaction_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wallettransaction',
            name='transaction_id',
            field=models.UUIDField(default=uuid.UUID('f9a1e269-ab7d-41d0-9ed1-94aeac984e2e'), unique=True),
        ),
    ]
