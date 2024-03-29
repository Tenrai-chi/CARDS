# Generated by Django 4.2.7 on 2024-02-03 06:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exchange', '0012_remove_amuletitem_sale_status_alter_amuletitem_card'),
    ]

    operations = [
        migrations.AddField(
            model_name='amulettype',
            name='chance_drop_on_fight',
            field=models.IntegerField(blank=True, null=True, verbose_name='Шанс выпадения после битвы'),
        ),
        migrations.AlterField(
            model_name='amuletitem',
            name='price',
            field=models.IntegerField(blank=True, null=True, verbose_name='Цена продажи'),
        ),
    ]
