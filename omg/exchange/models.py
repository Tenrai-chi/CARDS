from django.db import models
from django.contrib.auth.models import User

from cards.models import Card
from users.models import Transactions


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
    rarity = models.CharField(null=True, blank=True, max_length=3, verbose_name='Редкость')
    experience_amount = models.IntegerField(blank=True, null=True, verbose_name='Количество опыта')
    chance_drop_on_fight = models.IntegerField(blank=True, null=True, verbose_name='Шанс выпадения после битвы %')
    chance_drop_on_box = models.IntegerField(blank=True, null=True, verbose_name='Шанс выпадения в сундуке %')
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
    """ Инвентарь предметов опыта всех пользователей """

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
        verbose_name_plural = 'Инвентари предметов опыта'
        verbose_name = 'Инвентарь предметов опыта'

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


class AmuletRarity(models.Model):
    """ Редкость амулетов """

    name = models.CharField(max_length=30, verbose_name='Название')
    chance_drop_on_fight = models.IntegerField(blank=True, null=True, verbose_name='Шанс выпадения после битвы %')
    chance_drop_on_box = models.IntegerField(blank=True, null=True, verbose_name='Шанс выпадения в сундуке %')
    max_upgrade = models.IntegerField(blank=True, null=True, verbose_name='Максимальное количество улучшений')

    class Meta:
        verbose_name_plural = 'Редкость амулетов'
        verbose_name = 'Редкость амулета'

    def __str__(self):
        return self.name


class AmuletType(models.Model):
    """ Типы амулетов """

    name = models.CharField(max_length=30, verbose_name='Название')
    bonus_hp = models.FloatField(blank=True, null=True, verbose_name='Бонус здоровья')
    bonus_damage = models.FloatField(blank=True, null=True, verbose_name='Бонус урона')
    price = models.IntegerField(blank=True, null=True, verbose_name='Цена')
    sale_now = models.BooleanField(blank=True, null=True, default=True, verbose_name='Продажа')
    image = models.ImageField(blank=True, null=True, upload_to='image/amulet/', verbose_name='Изображение')
    discount = models.IntegerField(blank=True, null=True, default=0, verbose_name='Скидка %')
    discount_now = models.BooleanField(blank=True, null=True, default=False, verbose_name='Действие скидки')
    rarity = models.ForeignKey(AmuletRarity,
                               blank=True,
                               null=True,
                               on_delete=models.CASCADE,
                               related_name='rarity',
                               verbose_name='Редкость')

    class Meta:
        verbose_name_plural = 'Типы амулетов'
        verbose_name = 'Тип амулета'

    def __str__(self):
        return self.name


class AmuletItem(models.Model):
    """ Амулеты в инвентаре пользователей """

    amulet_type = models.ForeignKey(AmuletType,
                                    blank=True,
                                    null=True,
                                    on_delete=models.CASCADE,
                                    verbose_name='Тип амулета')
    owner = models.ForeignKey(User,
                              on_delete=models.CASCADE,
                              verbose_name='Владелец')
    card = models.ForeignKey(Card,
                             on_delete=models.CASCADE,
                             blank=True,
                             null=True,
                             verbose_name='Карта',
                             related_name='amulet_card')
    upgrades = models.IntegerField(blank=True, null=True, default=0, verbose_name='Количество улучшений')

    class Meta:
        verbose_name_plural = 'Амулеты'
        verbose_name = 'Амулет'

    def __str__(self):
        return f'{self.amulet_type.name} пользователя {self.owner.username}'


class UpgradeItemsType(models.Model):
    """ Типы предметов, позволяющих улучшать амулеты """

    name = models.CharField(max_length=30, verbose_name='Название')
    description = models.CharField(max_length=100, blank=True, null=True, verbose_name='Описание')
    type = models.CharField(max_length=30, blank=True, null=True, verbose_name='Тип предмета')
    amount_up = models.IntegerField(blank=True, null=True, verbose_name='Значение улучшения характеристик')
    image = models.ImageField(blank=True, null=True, upload_to='image/upgrade_items/', verbose_name='Изображение')

    class Meta:
        verbose_name_plural = 'Типы предметов улучшения'
        verbose_name = 'Тип предметов улучшения'

    def __str__(self):
        return self.name


class UpgradeItemsUsers(models.Model):
    """ Предметы улучшения в инвентаре пользователей """

    upgrade_item_type = models.ForeignKey(UpgradeItemsType,
                                          blank=True,
                                          null=True,
                                          on_delete=models.CASCADE,
                                          verbose_name='Тип предмета улучшения')
    owner = models.ForeignKey(User,
                              on_delete=models.CASCADE,
                              verbose_name='Владелец')
    amount = models.IntegerField(blank=True, null=True, verbose_name='Количество')

    class Meta:
        verbose_name_plural = 'Предметы улучшения в инвентаре пользователя'
        verbose_name = 'Предмет улучшения в инвентаре пользователя'

    def __str__(self):
        return f'{self.upgrade_item_type.name} пользователя {self.owner.username}'
