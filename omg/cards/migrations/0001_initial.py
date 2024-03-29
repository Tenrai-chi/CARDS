# Generated by Django 4.2.7 on 2023-12-03 23:44

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ClassCard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='Класс')),
                ('skill', models.CharField(blank=True, max_length=200, verbose_name='Навык')),
                ('image', models.ImageField(blank=True, null=True, upload_to='image/class/', verbose_name='Изображение')),
            ],
            options={
                'verbose_name': 'Класс',
                'verbose_name_plural': 'Классы',
            },
        ),
        migrations.CreateModel(
            name='Rarity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=2, verbose_name='Редкость')),
                ('max_level', models.IntegerField(blank=True, null=True, verbose_name='Максимальный уровень')),
                ('coefficient_damage_for_level', models.FloatField(blank=True, null=True, verbose_name='Урон за уровень')),
                ('coefficient_hp_for_level', models.FloatField(blank=True, null=True, verbose_name='Здоровье за уровень')),
                ('min_hp', models.IntegerField(blank=True, null=True, verbose_name='Минимальное здоровье')),
                ('max_hp', models.IntegerField(blank=True, null=True, verbose_name='Максимальное здоровье')),
                ('min_damage', models.IntegerField(blank=True, null=True, verbose_name='Минимальный урон')),
                ('max_damage', models.IntegerField(blank=True, null=True, verbose_name='Максимальный урон')),
            ],
            options={
                'verbose_name': 'Редкость',
                'verbose_name_plural': 'Редкость',
            },
        ),
        migrations.CreateModel(
            name='Type',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=10, verbose_name='Тип')),
            ],
            options={
                'verbose_name': 'Тип',
                'verbose_name_plural': 'Типы',
            },
        ),
        migrations.CreateModel(
            name='CardStore',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hp', models.IntegerField(verbose_name='Здоровье')),
                ('damage', models.IntegerField(verbose_name='Урон')),
                ('sale_now', models.BooleanField(blank=True, verbose_name='Продается')),
                ('price', models.IntegerField(blank=True, default=0, verbose_name='Цена')),
                ('class_card', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='cards.classcard', verbose_name='Класс')),
                ('rarity', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='cards.rarity', verbose_name='Редкость')),
                ('type', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='cards.type', verbose_name='Тип')),
            ],
            options={
                'verbose_name': 'Карта',
                'verbose_name_plural': 'Магазин',
            },
        ),
        migrations.CreateModel(
            name='Card',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hp', models.IntegerField(verbose_name='Здоровье')),
                ('damage', models.IntegerField(verbose_name='Урон')),
                ('level', models.IntegerField(default=0, verbose_name='Уровень')),
                ('class_card', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='cards.classcard', verbose_name='Класс')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Владелец')),
                ('rarity', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='cards.rarity', verbose_name='Редкость')),
                ('type', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='cards.type', verbose_name='Тип')),
            ],
            options={
                'verbose_name': 'Карта',
                'verbose_name_plural': 'Карты',
            },
        ),
    ]
