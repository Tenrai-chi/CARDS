# Generated by Django 4.2.7 on 2024-07-26 07:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exchange', '0022_amulettype_chance_drop_on_box_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='amuletitem',
            name='upgrades',
        ),
    ]