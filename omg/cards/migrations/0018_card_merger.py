# Generated by Django 4.2.7 on 2024-07-16 11:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0017_alter_card_owner'),
    ]

    operations = [
        migrations.AddField(
            model_name='card',
            name='merger',
            field=models.IntegerField(blank=True, default=None, null=True, verbose_name='Количество слияний'),
        ),
    ]