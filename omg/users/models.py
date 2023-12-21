from django.db import models
from django.contrib.auth.models import User
from cards.models import Card, CardStore


class Profile(models.Model):
    """ Профиль """

    user = models.OneToOneField(User, null=True, on_delete=models.CASCADE, verbose_name='Пользователь')
    about_user = models.TextField(null=True, blank=True, max_length=300, verbose_name='Информация')
    gold = models.IntegerField(blank=True, null=True, default=2000, verbose_name='Деньги')
    receiving_timer = models.DateTimeField(blank=True, null=True, verbose_name='Последнее получение')
    win = models.IntegerField(blank=True, null=True, default=0, verbose_name='Победы')
    lose = models.IntegerField(blank=True, null=True, default=0, verbose_name='Поражения')
    current_card = models.ForeignKey(Card, null=True, blank=True, default=None, on_delete=models.SET_NULL, verbose_name='Выбранная карта')
    is_activated = models.BooleanField(null=True, blank=True, default=True, verbose_name='Активен')
    profile_pic = models.ImageField(null=True,
                                    blank=True,
                                    default='image/profile/avatar.jpg',
                                    upload_to='image/profile/',
                                    verbose_name='Аватарка')

    class Meta:
        verbose_name_plural = 'Профили'
        verbose_name = 'Профиль'

    def __str__(self):
        return f'Профиль пользователя {self.user.username}'


class Transactions(models.Model):
    """ Транзакции пользователей """

    date_and_time = models.DateTimeField(blank=True, null=True, verbose_name='Дата и время')
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, verbose_name='Пользователь')
    before = models.IntegerField(null=True, blank=True, verbose_name='До')
    after = models.IntegerField(null=True, blank=True, verbose_name='После')
    comment = models.CharField(null=True, blank=True, max_length=300, verbose_name='Комментарий')

    class Meta:
        verbose_name_plural = 'Транзакции'
        verbose_name = 'Транзакция'

    def __str__(self):
        return f'Транзакция пользователя {self.user.username} от {self.date_and_time}'


class SaleStoreCards(models.Model):
    """ История покупок в магазине карт """

    date_and_time = models.DateTimeField(verbose_name='Дата и время')
    sold_card = models.ForeignKey(CardStore,
                                  null=True,
                                  blank=True,
                                  verbose_name='Проданная карта',
                                  on_delete=models.SET_NULL)
    transaction = models.ForeignKey(Transactions,
                                    null=True,
                                    blank=True,
                                    verbose_name='Транзакция',
                                    on_delete=models.SET_NULL)

    class Meta:
        verbose_name_plural = 'Покупки в магазине карт'
        verbose_name = 'Покупка в магазине карт'

    def __str__(self):
        return f'Покупка пользователя {self.transaction.user.username} от {self.date_and_time}'
