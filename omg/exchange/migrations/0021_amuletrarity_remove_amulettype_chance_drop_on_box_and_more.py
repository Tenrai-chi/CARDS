# Generated by Django 4.2.7 on 2024-07-26 07:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('exchange', '0020_alter_amulettype_discount'),
    ]

    operations = [
        migrations.CreateModel(
            name='AmuletRarity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30, verbose_name='Название')),
                ('chance_drop_on_fight', models.IntegerField(blank=True, null=True, verbose_name='Шанс выпадения после битвы')),
                ('chance_drop_on_box', models.IntegerField(blank=True, null=True, verbose_name='Шанс выпадения в сундуке')),
                ('max_upgrade', models.IntegerField(blank=True, null=True, verbose_name='Максимальное количество улучшений')),
            ],
        ),
        migrations.RemoveField(
            model_name='amulettype',
            name='chance_drop_on_box',
        ),
        migrations.RemoveField(
            model_name='amulettype',
            name='chance_drop_on_fight',
        ),
        migrations.AddField(
            model_name='amuletitem',
            name='upgrades',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='Количество улучшений'),
        ),
        migrations.AlterField(
            model_name='amulettype',
            name='rarity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='exchange.amuletrarity', verbose_name='Редкость'),
        ),
    ]