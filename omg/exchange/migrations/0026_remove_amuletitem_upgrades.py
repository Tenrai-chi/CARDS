# Generated by Django 4.2.7 on 2024-07-26 07:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exchange', '0025_amuletitem_upgrades'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='amuletitem',
            name='upgrades',
        ),
    ]
