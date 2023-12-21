# Generated by Django 4.2.7 on 2023-12-07 14:04

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cards', '0007_rarity_drop_chance'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoryReceivingCards',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_and_time', models.DateTimeField(blank=True, null=True, verbose_name='Дата и время')),
                ('method_receiving', models.CharField(blank=True, max_length=20, null=True, verbose_name='Метод получения')),
                ('card', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cards.card', verbose_name='Карта')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
        ),
    ]
