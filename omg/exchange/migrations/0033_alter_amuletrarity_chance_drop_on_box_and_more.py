# Generated by Django 4.2.7 on 2024-07-26 08:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('exchange', '0032_amuletitem_upgrades'),
    ]

    operations = [
        migrations.AlterField(
            model_name='amuletrarity',
            name='chance_drop_on_box',
            field=models.IntegerField(blank=True, null=True, verbose_name='Шанс выпадения в сундуке %'),
        ),
        migrations.AlterField(
            model_name='amuletrarity',
            name='chance_drop_on_fight',
            field=models.IntegerField(blank=True, null=True, verbose_name='Шанс выпадения после битвы %'),
        ),
        migrations.AlterField(
            model_name='amulettype',
            name='rarity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='rarity', to='exchange.amuletrarity', verbose_name='Редкость'),
        ),
        migrations.AlterField(
            model_name='experienceitems',
            name='chance_drop_on_box',
            field=models.IntegerField(blank=True, null=True, verbose_name='Шанс выпадения в сундуке %'),
        ),
    ]