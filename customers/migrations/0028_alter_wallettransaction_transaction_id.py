# Generated by Django 5.1.6 on 2025-03-28 08:22

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0027_alter_wallettransaction_transaction_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wallettransaction',
            name='transaction_id',
            field=models.UUIDField(default=uuid.UUID('2bfa73f2-595a-423c-895e-91f21878ea76'), unique=True),
        ),
    ]
