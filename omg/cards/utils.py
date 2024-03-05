from random import randint

import pytz

from datetime import datetime

from django.contrib.auth.models import User

from cards.models import Card, CardStore, HistoryReceivingCards, ClassCard, Type, Rarity
from exchange.models import AmuletItem


def fight_now(attacker, protector):
    """ Битва """

    attacker_damage, protector_damage, attacker_hp, protector_hp = stats_calculation(attacker, protector)

    # Начисление статов от амулета карте защиты
    amulet_protector = AmuletItem.objects.filter(card=protector.profile.current_card).last()
    if amulet_protector:
        protector_hp, protector_damage = stat_amulet_calculation(amulet_protector, protector_hp, protector_damage)

    # Начисление статов от амулета карте нападения
    amulet_attacker = AmuletItem.objects.filter(card=attacker.profile.current_card).last()
    if amulet_attacker:
        attacker_hp, attacker_damage = stat_amulet_calculation(amulet_attacker, attacker_hp, attacker_damage)


    # Битва
    can_fight_now = True
    history_fight = []
    turn = -1
    while can_fight_now:
        # Ход нападающего
        turn += 1
        history_fight.append([None for _ in range(6)])
        history_fight[turn][0] = f'Ход {turn + 1} {attacker.username}'

        #  Использование способности дриады
        if attacker.profile.current_card.class_card.name == 'Дриада':
            attacker_hp += attacker.profile.current_card.class_card.numeric_value
            history_fight[turn][2] = (f'Используется способность {attacker.username}-' +
                                      f'{attacker.profile.current_card.class_card.name} ' +
                                      f'"{attacker.profile.current_card.class_card.skill}" и ' +
                                      f'{attacker.profile.current_card.class_card.description_for_history_fight} ' +
                                      f'{attacker.profile.current_card.class_card.numeric_value}')

        # Нанесение урона
        protector_hp -= attacker_damage
        history_fight[turn][1] = f'{attacker.username} наносит {attacker_damage} урона'

        #  Использование способности Демона
        if attacker.profile.current_card.class_card.name == 'Демон':
            chance = randint(1, 100)
            if chance <= attacker.profile.current_card.class_card.chance_use:
                damage = round(attacker_damage * attacker.profile.current_card.class_card.numeric_value / 100)
                protector_hp -= damage
                history_fight[turn][2] = (f'Используется способность {attacker.username}-' +
                                          f'{attacker.profile.current_card.class_card.name} ' +
                                          f'"{attacker.profile.current_card.class_card.skill}" и ' +
                                          f'{attacker.profile.current_card.class_card.description_for_history_fight} ' +
                                          f'{damage}')

        # Использование способности оборотня
        if attacker.profile.current_card.class_card.name == 'Оборотень':
            chance = randint(1, 100)
            if chance <= attacker.profile.current_card.class_card.chance_use:
                regen_hp = round(attacker_damage * attacker.profile.current_card.class_card.numeric_value / 100)
                attacker_hp += regen_hp
                history_fight[turn][2] = (f'Используется способность {attacker.username}-' +
                                          f'{attacker.profile.current_card.class_card.name} ' +
                                          f'"{attacker.profile.current_card.class_card.skill}" и ' +
                                          f'{attacker.profile.current_card.class_card.description_for_history_fight} ' +
                                          f'{regen_hp}')

        #  Использование способности Призрака
        if protector.profile.current_card.class_card.name == 'Призрак':
            chance = randint(1, 100)
            if chance <= protector.profile.current_card.class_card.chance_use:
                protector_hp += attacker_damage
                history_fight[turn][3] = (f'Используется способность {protector.username}-' +
                                          f'{protector.profile.current_card.class_card.name} ' +
                                          f'"{protector.profile.current_card.class_card.skill}" и ' +
                                          f'{protector.profile.current_card.class_card.description_for_history_fight} ' +
                                          f'{attacker_damage}')

        #  Использование способности Бога Императора
        if protector.profile.current_card.class_card.name == 'Бог Император':
            return_damage = round(attacker.profile.current_card.class_card.numeric_value * attacker_damage / 100)
            attacker_hp -= return_damage
            history_fight[turn][3] = (f'Используется способность {protector.username}-' +
                                      f'{protector.profile.current_card.class_card.name} ' +
                                      f'"{protector.profile.current_card.class_card.skill}" и ' +
                                      f'{protector.profile.current_card.class_card.description_for_history_fight} ' +
                                      f'{return_damage}')

        history_fight[turn][4] = f'Здоровье {attacker.username} {attacker_hp}'
        history_fight[turn][5] = f'Здоровье {protector.username} {protector_hp}'

        if protector_hp <= 0:
            winner = attacker
            loser = protector
            can_fight_now = False

        else:
            # Ход защищающегося
            turn += 1
            history_fight.append([None for _ in range(6)])
            history_fight[turn][0] = f'Ход {turn + 1} {protector.username}'

            # Использование способности дриады
            if protector.profile.current_card.class_card.name == 'Дриада':
                protector_hp += protector.profile.current_card.class_card.numeric_value
                history_fight[turn][2] = (f'Используется способность {protector.username}-' +
                                          f'{protector.profile.current_card.class_card.name} ' +
                                          f'"{protector.profile.current_card.class_card.skill}" и ' +
                                          f'{protector.profile.current_card.class_card.description_for_history_fight} ' +
                                          f'{protector.profile.current_card.class_card.numeric_value}')

            # Нанесение урона
            attacker_hp -= protector_damage
            history_fight[turn][1] = f'{protector.username} наносит {protector_damage} урона'

            #  Использование способности Демона
            if protector.profile.current_card.class_card.name == 'Демон':
                chance = randint(1, 100)
                if chance <= protector.profile.current_card.class_card.chance_use:
                    damage = round(protector_damage * protector.profile.current_card.class_card.numeric_value / 100)
                    attacker_hp -= damage
                    history_fight[turn][2] = (f'Используется способность {protector.username}-' +
                                              f'{protector.profile.current_card.class_card.name} ' +
                                              f'"{protector.profile.current_card.class_card.skill}" и ' +
                                              f'{protector.profile.current_card.class_card.description_for_history_fight} ' +
                                              f'{damage}')

            # Использование способности оборотня
            if protector.profile.current_card.class_card.name == 'Оборотень':
                chance = randint(1, 100)
                if chance <= protector.profile.current_card.class_card.chance_use:
                    regen_hp = round(protector_damage * protector.profile.current_card.class_card.numeric_value / 100)
                    protector_hp += regen_hp
                    history_fight[turn][2] = (f'Используется способность {protector.username}-' +
                                              f'{protector.profile.current_card.class_card.name} ' +
                                              f'"{protector.profile.current_card.class_card.skill}" и ' +
                                              f'{protector.profile.current_card.class_card.description_for_history_fight} ' +
                                              f'{regen_hp}')

            #  Использование способности Призрака
            if attacker.profile.current_card.class_card.name == 'Призрак':
                chance = randint(1, 100)
                if chance <= attacker.profile.current_card.class_card.chance_use:
                    attacker_hp += protector_damage
                    history_fight[turn][3] = (f'Используется способность {attacker.username}-' +
                                              f'{attacker.profile.current_card.class_card.name} ' +
                                              f'"{attacker.profile.current_card.class_card.skill}" и ' +
                                              f'{attacker.profile.current_card.class_card.description_for_history_fight} ' +
                                              f'{protector_damage}')

            #  Использование способности Бога Императора
            if attacker.profile.current_card.class_card.name == 'Бог Император':
                return_damage = round(protector.profile.current_card.class_card.numeric_value * protector_damage / 100)
                protector_hp -= return_damage
                history_fight[turn][3] = (f'Используется способность {attacker.username}-' +
                                          f'{attacker.profile.current_card.class_card.name} ' +
                                          f'"{attacker.profile.current_card.class_card.skill}" и ' +
                                          f'{attacker.profile.current_card.class_card.description_for_history_fight} ' +
                                          f'{return_damage}')

            history_fight[turn][4] = f'Здоровье {protector.username} {protector_hp}'
            history_fight[turn][5] = f'Здоровье {attacker.username} {attacker_hp}'

            if attacker_hp <= 0:
                winner = protector
                loser = attacker
                can_fight_now = False

    return winner, loser, history_fight



def use_spell_dryad(user_hp, user_info):
    """ Использование способности дриады.
        Восстанавливает свое здоровье.
        Возвращает итоговое количество своего здоровья
    """
    user_hp += user_info.profile.current_card.class_card.numeric_value

    return user_hp


def use_spell_werewolf():
    """ Использование способности оборотня.
        Восстанавливает свое здоровье в зависимости от нанесенного урона.
        Возвращает итоговое количество своего здоровья
    """

    pass


def use_spell_emperor_mankind():
    """ Использование способности императора человечества.
        Наносит часть полученного урона атаковавшему.
        Возвращает итоговое количество здоровья нападающего
    """

    pass


def use_spell_ghost():
    """ Использование способности призрака.
        Избегает урон от атаки противника.
        Возвращает итоговое количество своего здоровья
    """

    pass


def use_spell_demon():
    """ Использование способности демона.
        Наносит дополнительный урон, в зависимости от своей атаки.
        Возвращает итоговое количество вражеского здоровья
    """

    pass


def use_spell_elf():
    """ Использование способности эльфа.
        Увеличивает шанс выпадения предметов после битвы.
        Возвращает итоговый шанс выпадения предмета.
    """

    pass


def get_exp_card_after_fight(user_info):
    """ Начисляет опыт избранной карте пользователя.
        Возвращает информацию о текущем уровне и прогрессе опыта.
    """

    pass

def accrual_stats_with_level_up_card(user_info):
    """ Увеличение характеристики карт с повышением уровня.
        Возвращает новые значения hp и damage карты.
    """

    pass


def stats_calculation(attacker, protector):
    """ Вычисление первоначальных статов пользователей.
        Возвращает урон и здоровье защиты и нападения
    """

    if protector.profile.current_card.type != attacker.profile.current_card.type:
        if protector.profile.current_card.type.better == attacker.profile.current_card.type:

            # Если защита лучше нападения
            protector_damage = round(protector.profile.current_card.damage * 1.2)
            attacker_damage = round(attacker.profile.current_card.damage * 0.8)
        else:
            # Если нападение лучше защиты
            attacker_damage = round(attacker.profile.current_card.damage * 1.2)
            protector_damage = round(protector.profile.current_card.damage * 0.8)
    else:
        # Стандартные статы урона
        protector_damage = round(protector.profile.current_card.damage)
        attacker_damage = round(attacker.profile.current_card.damage)

    # Статы хп всегда одинаковы
    protector_hp = protector.profile.current_card.hp
    attacker_hp = attacker.profile.current_card.hp

    return attacker_damage, protector_damage, attacker_hp, protector_hp

def stat_amulet_calculation(user_amulet, user_hp, user_damage):
    """ Начисление статов от амулета.
        Возвращает итоговые значения здоровья и урона карты пользователя с амулетом.
    """

    user_damage += user_amulet.bonus_damage
    user_hp += user_amulet.bonus_hp

    return user_hp, user_damage

def filling_missing_data():
    """ Заполнение данных о создании карты у карт, созданных изначально.
    """

    date_and_time = datetime(year=2023, month=11, day=5, hour=13, minute=30, tzinfo=pytz.timezone('Europe/Moscow'))
    cards = Card.objects.all()
    card_store = CardStore.objects.all()
    admin = User.objects.get(pk=1)
    temp_info = []

    for card in cards:
        for card_in_store in card_store:
            if (card.class_card == card_in_store.class_card and card.type == card_in_store.type and
                    card.rarity == card_in_store.rarity and card.hp == card_in_store.hp and card.damage == card_in_store.damage):
                temp_info.append(card.id)

    for card in cards:
        if card.id in temp_info:
            method_receiving = 'Покупка в магазине'
            new_record = HistoryReceivingCards.objects.create(card=card,
                                                              date_and_time=date_and_time,
                                                              user=admin,
                                                              method_receiving=method_receiving)
            new_record.save()
        else:
            method_receiving = 'Бесплатная генерация'
            new_record = HistoryReceivingCards.objects.create(card=card,
                                                              date_and_time=date_and_time,
                                                              user=admin,
                                                              method_receiving=method_receiving)
            new_record.save()


def delete_all_record():
    """ Удаление всех записей в таблице с историей получения карт.
    """

    table = HistoryReceivingCards.objects.all()
    for a in table:
        a.delete()


def accrue_experience(accrued_experience, current_level, max_level, expended_experience=0, current_exp=0):
    """ Вычисляет итоговый уровень карты, текущее значение опыта и общий затраченный опыт.
        :param accrued_experience: Полученный опыт
        :param current_level: Текущий уровень
        :param max_level: Максимально доступный уровень
        :param expended_experience: Потраченный опыт
        :param current_exp: Текущий опыт
        :return: Текущее значение опыта, текущий уровень карты, затраченный опыт в целом
    """

    need_exp = calculate_need_exp(current_level)

    if need_exp - current_exp > accrued_experience:  # Если ддя достижения следующего уровня не хватает полученного опыта
        current_exp += accrued_experience  # Текущий опыт
        expended_experience += accrued_experience  # Затраченный опыт

        return current_exp, current_level, expended_experience

    else:
        if max_level - current_level == 1:  # Если достигает максимального уровня
            expended_experience += need_exp - current_exp  # Затраченный опыт
            current_level = max_level
            current_exp = 0

            return current_exp, current_level, expended_experience

        else:
            expended_experience += need_exp - current_exp  # Затраченный опыт
            accrued_experience -= need_exp - current_exp  # Оставшийся опыт
            current_level += 1  # Текущий уровень
            current_exp = 0

            return accrue_experience(accrued_experience, current_level, max_level, expended_experience, current_exp)


def calculate_need_exp(level):
    """ Вычисление необходимого уровня для получения следующего уровня.
    """

    return round(1000 + 100 * 1.15 ** level, 2)
