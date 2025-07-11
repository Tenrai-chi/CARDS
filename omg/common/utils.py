import pytz

from datetime import datetime
from random import choice, randint

from django.contrib.auth.models import User

from cards.models import Card, CardStore, HistoryReceivingCards, ClassCard, Type, Rarity


def date_time_now() -> datetime:
    """ Возвращает текущее время по Московскому часовому поясу """

    date_time = datetime.now(pytz.timezone('Europe/Moscow'))

    return date_time


def time_difference_check(check_time: datetime, need_hours: int) -> tuple[bool, float]:
    """ Проверяет прошло ли необходимое количество часов для действия """

    difference = date_time_now() - check_time
    hours = difference.total_seconds() // 3600

    return hours >= need_hours, hours


def create_new_card(user: User, ur_box=None, max_attribute=None):
    """ Создание карты. Возвращает айди только что созданной карты
        TODO ur_box, max_attribute
    """

    class_card = choice(ClassCard.objects.all())
    type_card = choice(Type.objects.all())

    r = Rarity.objects.get(name='R')
    sr = Rarity.objects.get(name='SR')
    ur = Rarity.objects.get(name='UR')

    if not ur_box:
        random_rarity = randint(1, r.drop_chance + sr.drop_chance + ur.drop_chance)
        if random_rarity <= r.drop_chance:
            rarity_card = r
        elif random_rarity <= (r.drop_chance + sr.drop_chance):
            rarity_card = sr
        else:
            rarity_card = ur
    else:
        rarity_card = ur

    if max_attribute == 'damage':
        damage = rarity_card.max_damage
        hp = randint(rarity_card.min_hp, rarity_card.max_hp)

    elif max_attribute == 'hp':
        damage = randint(rarity_card.min_damage, rarity_card.max_damage)
        hp = rarity_card.max_hp

    else:
        damage = randint(rarity_card.min_damage, rarity_card.max_damage)
        hp = randint(rarity_card.min_hp, rarity_card.max_hp)

    new_card = Card.objects.create(owner=user,
                                   level=1,
                                   class_card=class_card,
                                   type=type_card,
                                   rarity=rarity_card,
                                   hp=hp,
                                   damage=damage
                                   )

    return new_card
