# Generated by Django 4.2.7 on 2024-02-14 19:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_guildbuff_guild_profile_guild'),
    ]

    operations = [
        migrations.AlterField(
            model_name='guild',
            name='date_create',
            field=models.DateTimeField(verbose_name='Дата создания'),
        ),
    ]
