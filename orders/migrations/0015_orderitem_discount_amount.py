# Generated by Django 5.1.6 on 2025-03-22 07:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0014_alter_order_status_alter_payment_payment_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='discount_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
