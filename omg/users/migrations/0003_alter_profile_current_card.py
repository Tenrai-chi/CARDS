# Generated by Django 4.2.7 on 2023-12-04 15:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0002_card_experience_bar_card_sale_status'),
        ('users', '0002_transactions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='current_card',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='cards.card', verbose_name='Выбранная карта'),
        ),
    ]
