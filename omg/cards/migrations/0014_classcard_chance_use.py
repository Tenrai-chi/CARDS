# Generated by Django 4.2.7 on 2024-02-03 03:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0013_classcard_description_classcard_numeric_value'),
    ]

    operations = [
        migrations.AddField(
            model_name='classcard',
            name='chance_use',
            field=models.IntegerField(blank=True, null=True, verbose_name='Шанс использования'),
        ),
    ]