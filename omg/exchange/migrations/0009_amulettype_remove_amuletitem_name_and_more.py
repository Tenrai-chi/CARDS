# Generated by Django 4.2.7 on 2024-01-28 15:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('exchange', '0008_amuletstore_alter_usersinventory_options_amuletitem'),
    ]

    operations = [
        migrations.CreateModel(
            name='AmuletType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30, verbose_name='Название')),
                ('image', models.ImageField(blank=True, null=True, upload_to='image/amulet/', verbose_name='Изображение')),
                ('rarity', models.CharField(max_length=3, verbose_name='Редкость')),
            ],
            options={
                'verbose_name': 'Тип амулета',
                'verbose_name_plural': 'Типы амулетов',
            },
        ),
        migrations.RemoveField(
            model_name='amuletitem',
            name='name',
        ),
        migrations.RemoveField(
            model_name='amuletitem',
            name='rarity',
        ),
        migrations.RemoveField(
            model_name='amuletstore',
            name='name',
        ),
        migrations.AddField(
            model_name='amuletitem',
            name='amulet_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='exchange.amulettype'),
        ),
        migrations.AddField(
            model_name='amuletstore',
            name='amulet_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='exchange.amulettype'),
        ),
    ]
