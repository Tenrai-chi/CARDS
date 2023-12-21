from django import forms
from django.core import validators
from django.forms import widgets


from .models import HistoryPurchaseItems


class BuyItemForm(forms.ModelForm):
    """ Форма покупки предмета """

    amount = forms.IntegerField(label='Количество',
                                validators=[validators.MinValueValidator(1)],
                                )

    class Meta:
        model = HistoryPurchaseItems
        fields = ['amount']
