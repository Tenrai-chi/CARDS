# Generated by Django 4.2.7 on 2024-07-26 07:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exchange', '0021_amuletrarity_remove_amulettype_chance_drop_on_box_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='amulettype',
            name='chance_drop_on_box',
            field=models.IntegerField(blank=True, null=True, verbose_name='Шанс выпадения в сундуке'),
        ),
        migrations.AddField(
            model_name='amulettype',
            name='chance_drop_on_fight',
            field=models.IntegerField(blank=True, null=True, verbose_name='Шанс выпадения после битвы'),
        ),
        migrations.AlterField(
            model_name='amulettype',
            name='rarity',
            field=models.CharField(blank=True, max_length=3, null=True, verbose_name='Редкость'),
        ),
    ]
