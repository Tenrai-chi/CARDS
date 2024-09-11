# Generated by Django 4.2.7 on 2024-07-26 08:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('exchange', '0030_amuletrarity'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='amuletrarity',
            options={'verbose_name': 'Редкость амулета', 'verbose_name_plural': 'Редкость амулетов'},
        ),
        migrations.RemoveField(
            model_name='amulettype',
            name='chance_drop_on_box',
        ),
        migrations.RemoveField(
            model_name='amulettype',
            name='chance_drop_on_fight',
        ),
        migrations.AlterField(
            model_name='amulettype',
            name='rarity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='exchange.amuletrarity', verbose_name='Редкость'),
        ),
    ]
