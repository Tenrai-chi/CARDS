from django import forms
from django.core import validators
from django.forms import widgets

from .models import Card

from exchange.models import UsersInventory


class SaleCardForm(forms.ModelForm):
    """ Форма выставления карты на продажу """

    #sale_status = forms.BooleanField(label='Статус продажи')
    price = forms.IntegerField(label='Цена',
                               min_value=1,
                               validators=[validators.MinValueValidator(1)],
                               )

    class Meta:
        model = Card
        fields = ['price']  # 'sale_status'


class UseItemForm(forms.ModelForm):
    """ Форма выбора количества используемого предмета """

    amount = forms.IntegerField(label='Количество',
                                validators=[validators.MinValueValidator(1)])

    class Meta:
        model = UsersInventory
        fields = ['amount']


