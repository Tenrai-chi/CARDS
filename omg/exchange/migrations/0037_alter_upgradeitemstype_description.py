# Generated by Django 4.2.7 on 2024-07-30 11:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exchange', '0036_upgradeitemstype_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='upgradeitemstype',
            name='description',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Описание'),
        ),
    ]