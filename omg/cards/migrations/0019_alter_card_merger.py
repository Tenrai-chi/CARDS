# Generated by Django 4.2.7 on 2024-07-16 11:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0018_card_merger'),
    ]

    operations = [
        migrations.AlterField(
            model_name='card',
            name='merger',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='Количество слияний'),
        ),
    ]