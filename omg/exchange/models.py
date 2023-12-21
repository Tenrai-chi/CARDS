from django.db import models
from cards.models import Card
from users.models import Transactions
from django.contrib.auth.models import User


class SaleUserCards(models.Model):
    """ История покупок карт между пользователями """

    date_and_time = models.DateTimeField(blank=True, null=True, verbose_name='Дата и время')
    buyer = models.ForeignKey(User,
                              null=True,
                              blank=True,
                              verbose_name='Покупатель',
                              on_delete=models.SET_NULL,
                              related_name='buyer'
                              )
    salesman = models.ForeignKey(User,
                                 null=True,
                                 blank=True,
                                 verbose_name='Продавец',
                                 on_delete=models.SET_NULL,
                                 related_name='salesman'
                                 )
    card = models.ForeignKey(Card,
                             null=True,
                             blank=True,
                             verbose_name='Карта',
                             on_delete=models.SET_NULL
                             )
    price = models.IntegerField(null=True, blank=True, verbose_name='Цена')
    transaction_buyer = models.ForeignKey(Transactions,
                                          null=True,
                                          blank=True,
                                          verbose_name='Транзакция покупателя',
                                          on_delete=models.SET_NULL,
                                          related_name='transaction_buyer'
                                          )
    transaction_salesman = models.ForeignKey(Transactions,
                                             null=True,
                                             blank=True,
                                             verbose_name='Транзакция продавца',
                                             on_delete=models.SET_NULL,
                                             related_name='transaction_salesman'
                                             )

    class Meta:
        verbose_name_plural = 'Продажи карт пользователей'
        verbose_name = 'Продажа карты пользователя'

    def __str__(self):
        return f'Покупка {self.buyer} у {self.salesman}'


class ExperienceItems(models.Model):
    """ Предметы опыта """

    name = models.CharField(null=True, blank=True, max_length=50, verbose_name='Название')
    experience_amount = models.IntegerField(blank=True, null=True, verbose_name='Количество опыта')
    chance_drop_on_fight = models.IntegerField(blank=True, null=True, verbose_name='Шанс выпадения после битвы %')
    price = models.IntegerField(blank=True, null=True, verbose_name='Цена')
    image = models.ImageField(null=True, blank=True, upload_to='image/items/', verbose_name='Изображение')
    gold_for_use = models.IntegerField(blank=True, null=True, verbose_name='Плата за использование')
    sale_now = models.BooleanField(blank=True, default=True, null=True, verbose_name='Продается')

    class Meta:
        verbose_name_plural = 'Предметы опыта'
        verbose_name = 'Предмет опыта'

    def __str__(self):
        return self.name


class UsersInventory(models.Model):
    """ Инвентарь всех пользователей """

    owner = models.ForeignKey(User,
                              on_delete=models.CASCADE,
                              blank=True,
                              null=True,
                              verbose_name='Владелец'
                              )
    item = models.ForeignKey(ExperienceItems,
                             blank=True,
                             null=True,
                             on_delete=models.CASCADE,
                             verbose_name='Предмет'
                             )
    amount = models.IntegerField(null=True,
                                 blank=True,
                                 verbose_name='Количество')

    class Meta:
        verbose_name_plural = 'Инвентари'
        verbose_name = 'Инвентарь'

    def __str__(self):
        return f'Предмет "{self.item}" пользователя {self.owner.username}'


class HistoryPurchaseItems(models.Model):
    """ История покупок в магазине """

    date_and_time = models.DateTimeField(blank=True, null=True, verbose_name='Дата и время')
    user = models.ForeignKey(User,
                             on_delete=models.CASCADE,
                             blank=True,
                             null=True,
                             verbose_name='Покупатель')
    item = models.ForeignKey(ExperienceItems,
                             on_delete=models.CASCADE,
                             blank=True,
                             null=True,
                             verbose_name='Предмет')
    amount = models.IntegerField(blank=True, null=True, verbose_name='Количество')
    transaction = models.ForeignKey(Transactions,
                                    null=True,
                                    blank=True,
                                    verbose_name='Транзакция',
                                    on_delete=models.SET_NULL)

    class Meta:
        verbose_name_plural = 'Покупки в магазине предметов'
        verbose_name = 'Покупка в магазине предметов'

    def __str__(self):
        return f'Покупка пользователя {self.user}'
