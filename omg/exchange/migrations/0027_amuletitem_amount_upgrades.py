# Generated by Django 4.2.7 on 2024-07-26 07:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exchange', '0026_remove_amuletitem_upgrades'),
    ]

    operations = [
        migrations.AddField(
            model_name='amuletitem',
            name='amount_upgrades',
            field=models.IntegerField(blank=True, null=True, verbose_name='Количество улучшений'),
        ),
    ]