from django.db import models
from django.contrib.auth.models import User

from random import choice


class ClassCard(models.Model):
    """ Класс карты. Отвечает за способности и изображение """

    name = models.CharField(max_length=50, verbose_name='Класс')
    skill = models.CharField(max_length=200, blank=True, verbose_name='Навык')
    description = models.CharField(max_length=500, blank=True, null=True, verbose_name='Описание')
    description_for_history_fight = models.CharField(max_length=500, blank=True, null=True, verbose_name='Описание для истории')
    numeric_value = models.FloatField(null=True, blank=True, verbose_name='Числовое значение')
    chance_use = models.IntegerField(null=True, blank=True, verbose_name='Шанс использования')
    image = models.ImageField(null=True, blank=True, upload_to='image/class/', verbose_name='Изображение')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Классы'
        verbose_name = 'Класс'


class Type(models.Model):
    """ Тип карты. Отвечает за урон карты по цветовой схеме """

    name = models.CharField(max_length=10, verbose_name='Тип')
    better = models.ForeignKey('self',
                               on_delete=models.CASCADE,
                               blank=True,
                               null=True,
                               verbose_name='Лучше против',
                               related_name='better_vs')
    worst = models.ForeignKey('self',
                              on_delete=models.CASCADE,
                              blank=True,
                              null=True,
                              verbose_name='Хуже против',
                              related_name='worst_vs')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Типы'
        verbose_name = 'Тип'


class Rarity(models.Model):
    """ Редкость карты. Отвечает за максимально возможный уровень,
        разброс здоровья и урона при генерации карты и
        возрастание характеристик с ростом уровня
    """

    name = models.CharField(max_length=2, verbose_name='Редкость')
    max_level = models.IntegerField(null=True, blank=True, verbose_name='Максимальный уровень')
    coefficient_damage_for_level = models.FloatField(null=True, blank=True, verbose_name='Урон за уровень')
    coefficient_hp_for_level = models.FloatField(null=True, blank=True, verbose_name='Здоровье за уровень')

    min_hp = models.IntegerField(null=True, blank=True, verbose_name='Минимальное здоровье')
    max_hp = models.IntegerField(null=True, blank=True, verbose_name='Максимальное здоровье')

    min_damage = models.IntegerField(null=True, blank=True, verbose_name='Минимальный урон')
    max_damage = models.IntegerField(null=True, blank=True, verbose_name='Максимальный урон')

    drop_chance = models.IntegerField(null=True, blank=True, verbose_name='Шанс выпадения')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Редкость'
        verbose_name = 'Редкость'


class Card(models.Model):
    """ Карты пользователей
        Class -> способности карты в бою и картинка
        Type -> цвет карты (зеленый, синий, красный) по принципу камень-ножницы-бумага
        Rarity -> максимальный уровень, разброс характеристик начального уровня при генерации, увеличение характеристик с уровнем
        Damage -> базовый урон
        Hp -> базовое здоровье
        Enhancement -> количество использований увеличения здоровья и урона
        Merger -> количество использованных копий карты, усиливает на навык карты в бою (изначально 0)
    """

    owner = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE, verbose_name='Владелец')
    class_card = models.ForeignKey(ClassCard, on_delete=models.SET_NULL, null=True, verbose_name='Класс')
    type = models.ForeignKey(Type, on_delete=models.SET_NULL, null=True, verbose_name='Тип')
    hp = models.FloatField(verbose_name='Здоровье')
    damage = models.FloatField(verbose_name='Урон')
    level = models.IntegerField(default=1, verbose_name='Уровень')
    experience_bar = models.IntegerField(default=0, blank=True, null=True, verbose_name='Текущий опыт')
    rarity = models.ForeignKey(Rarity, on_delete=models.SET_NULL, null=True, verbose_name='Редкость')
    sale_status = models.BooleanField(default=False, blank=True, null=True, verbose_name='Продажа')
    price = models.IntegerField(default=None, blank=True, null=True, verbose_name='Цена продажи')

    enhancement = models.IntegerField(default=0, blank=True, null=True, verbose_name='Количество усилений')
    max_enhancement = models.IntegerField(default=20, blank=True, null=True, verbose_name='Максимальное количество усилений')

    merger = models.IntegerField(default=0, blank=True, null=True, verbose_name='Количество слияний')
    max_merger = models.IntegerField(default=10, blank=True, null=True, verbose_name='Максимальное количество слияний')

    class Meta:
        verbose_name_plural = 'Карты'
        verbose_name = 'Карта'

    def __str__(self):
        return f'Карта пользователя {self.owner.username} ID {self.id}'

    def increase_stats(self, new_level=1):
        """ Увеличение характеристик карты с повышением уровня """

        self.damage += self.rarity.coefficient_damage_for_level * new_level
        self.hp += self.rarity.coefficient_hp_for_level * new_level

        self.save()

    def enhance_hp(self):
        """ Усиление здоровья """

        if self.enhancement < self.max_enhancement:
            self.hp += 3
            self.enhancement += 1
            self.save()

    def enhance_attack(self):
        """ Усиление атаки """

        if self.enhancement < self.max_enhancement:
            self.damage += 3
            self.enhancement += 1
            self.save()

    def enhance_random(self):
        """ Усиление случайной характеристики """

        if self.enhancement < self.max_enhancement:
            hp_or_damage = choice([0, 1])
            if hp_or_damage == 0:
                self.hp += 5
                self.enhancement += 1
            else:
                self.damage += 5
                self.enhancement += 1
            self.save()

    def merge(self):
        """ Слияние карты """

        if self.merger < self.max_merger:
            self.merger += 1
            self.save()

    def remove_from_sale(self):
        """ Удаляет карту с торговой площадки """

        if self.sale_status is True:
            self.sale_status = False
            self.price = None
            self.save()


class CardStore(models.Model):
    """ Карты в продаже """

    class_card = models.ForeignKey(ClassCard, on_delete=models.SET_NULL, null=True, verbose_name='Класс')
    type = models.ForeignKey(Type, on_delete=models.SET_NULL, null=True, verbose_name='Тип')
    rarity = models.ForeignKey(Rarity, on_delete=models.SET_NULL, null=True, verbose_name='Редкость')
    hp = models.IntegerField(verbose_name='Здоровье')
    damage = models.IntegerField(verbose_name='Урон')
    sale_now = models.BooleanField(blank=True, verbose_name='Продается')
    price = models.IntegerField(default=0, blank=True, verbose_name='Цена')

    discount = models.IntegerField(default=0, blank=True, verbose_name='Скидка %')
    discount_now = models.BooleanField(blank=True, default=False, verbose_name='Действие скидки')

    class Meta:
        verbose_name_plural = 'Магазин карт'
        verbose_name = 'Карта в магазине'

    def __str__(self):
        return f'Карта в магазине ID {self.id}'


class FightHistory(models.Model):
    """ История боев """

    date_and_time = models.DateTimeField(blank=True, null=True, verbose_name='Дата и время')
    winner = models.ForeignKey(User,
                               blank=True,
                               null=True,
                               on_delete=models.CASCADE,
                               verbose_name='Победитель',
                               related_name='winner')
    loser = models.ForeignKey(User,
                              blank=True,
                              null=True,
                              on_delete=models.CASCADE,
                              verbose_name='Проигравший',
                              related_name='loser')
    card_winner = models.ForeignKey(Card,
                                    blank=True,
                                    null=True,
                                    on_delete=models.CASCADE,
                                    verbose_name='Карта победителя',
                                    related_name='card_winner')
    card_loser = models.ForeignKey(Card,
                                   blank=True,
                                   null=True,
                                   on_delete=models.CASCADE,
                                   verbose_name='Карта проигравшего',
                                   related_name='card_loser')

    class Meta:
        verbose_name_plural = 'Бои'
        verbose_name = 'Бой'

    def __str__(self):
        return f'Бой между {self.winner.username} и {self.loser.username}'


class HistoryReceivingCards(models.Model):
    """ История получения карт """

    card = models.ForeignKey(Card,
                             blank=True,
                             null=True,
                             on_delete=models.CASCADE,
                             verbose_name='Карта')
    date_and_time = models.DateTimeField(blank=True, null=True, verbose_name='Дата и время')
    user = models.ForeignKey(User,
                             blank=True,
                             null=True,
                             on_delete=models.CASCADE,
                             verbose_name='Пользователь')
    method_receiving = models.CharField(blank=True,
                                        null=True,
                                        max_length=20,
                                        verbose_name='Метод получения')

    class Meta:
        verbose_name_plural = 'Создание карт'
        verbose_name = 'Создание карты'

    def __str__(self):
        return f'Получение карты {self.card.id}'
