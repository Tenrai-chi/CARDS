from PIL import Image
from os import path

from django.db import models
from django.contrib.auth.models import User
from cards.models import Card, CardStore

from .utils import new_size


class GuildBuff(models.Model):
    """ Все доступные усиления гильдии.
    """
    name = models.CharField(max_length=50, verbose_name='Название')
    description = models.CharField(max_length=200, verbose_name='Описание')
    numeric_value = models.FloatField(verbose_name='Числовое значение')

    class Meta:
        verbose_name = 'Усиление гильдии'
        verbose_name_plural = 'Усиления гильдии'

    def __str__(self):
        return self.name


class Guild(models.Model):
    """ Гильдия пользователей.
    """

    name = models.CharField(unique=True, max_length=50, verbose_name='Название')
    leader = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Лидер')
    number_of_participants = models.IntegerField(default=1, verbose_name='Количество участников')
    guild_pic = models.ImageField(null=True,
                                  blank=True,
                                  default='image/guild/avatar.png',
                                  upload_to='image/guild/',
                                  verbose_name='Аватарка')
    date_create = models.DateTimeField(blank=True, null=True, verbose_name='Дата создания')
    rating = models.IntegerField(verbose_name='Рейтинг')
    buff = models.ForeignKey(GuildBuff, on_delete=models.SET_NULL, blank=True, null=True, verbose_name='Усиление гильдии')
    date_last_change_buff = models.DateTimeField(blank=True, null=True, verbose_name='Дата и время смены усиления')

    class Meta:
        verbose_name = 'Гильдия'
        verbose_name_plural = 'Гильдии'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save()
        img = Image.open(self.guild_pic.path)
        if img.width != img.height:
            img = new_size(img)
            img.save(self.guild_pic.path)


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
    guild = models.ForeignKey(Guild, on_delete=models.SET_NULL, blank=True, null=True, verbose_name='Гильдия')
    date_guild_accession = models.DateField(blank=True, null=True, verbose_name='Дата присоединения к гильдии')
    guild_point = models.IntegerField(blank=True, null=True, default=0, verbose_name='Очки гильдии')

    class Meta:
        verbose_name_plural = 'Профили'
        verbose_name = 'Профиль'

    def __str__(self):
        return f'Профиль пользователя {self.user.username}'

    def save(self, *args, **kwargs):
        super().save()
        img = Image.open(self.profile_pic.path)
        if img.width != img.height:
            img = new_size(img)
            img.save(self.profile_pic.path)


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


class FavoriteUsers(models.Model):
    """ Список избранных пользователей у пользователей.
    """

    user = models.ForeignKey(User,
                             on_delete=models.CASCADE,
                             verbose_name='Пользователь',
                             related_name='user')
    favorite_user = models.ForeignKey(User,
                                      on_delete=models.CASCADE,
                                      verbose_name='Избранный',
                                      related_name='favorite_user')

    class Meta:
        verbose_name_plural = 'Избранные пользователи'
        verbose_name = 'Избранный пользователь'

    def __str__(self):
        return f'Избранный {self.favorite_user.username} пользователя {self.user.username}'
