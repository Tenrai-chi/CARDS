# Generated by Django 4.2.7 on 2024-02-06 08:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exchange', '0017_remove_amuletitem_bonus_damage_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='experienceitems',
            name='rarity',
            field=models.CharField(blank=True, max_length=3, null=True, verbose_name='Редкость'),
        ),
    ]