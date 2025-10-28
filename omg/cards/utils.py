import pytz

from datetime import datetime
from django.contrib.auth.models import User
from random import randint

from cards.models import Card, CardStore, HistoryReceivingCards, ClassCard, Type, Rarity
from exchange.models import AmuletItem


def stats_calculation(user_card: Card, enemy_card: Card) -> tuple[float, float, float, float]:
    """ Вычисление боевых характеристик карт.
        Базовые характеристики на основе типа обеих карт.
        Дополнительные характеристики на основе амулета при наличии.
    """

    user_card_hp = round(user_card.hp, 2)
    user_card_damage = round(user_card.damage, 2)
    enemy_card_hp = round(enemy_card.hp, 2)
    enemy_card_damage = round(enemy_card.damage, 2)

    # Если карта пользователя лучше карты противника
    if user_card.type.better == enemy_card.type:
        user_card_damage = round(user_card_damage * 1.2, 2)
        enemy_card_damage = round(enemy_card_damage * 0.8, 2)
    # Если карта противника лучше карты пользователя
    elif enemy_card.type.better == user_card.type:
        enemy_card_damage = round(enemy_card_damage * 1.2, 2)
        user_card_damage = round(user_card_damage * 0.8, 2)

    try:
        amulet_user_card = user_card.amulet_card.get()
        user_card_hp += amulet_user_card.amulet_type.bonus_hp
        user_card_damage += amulet_user_card.amulet_type.bonus_damage
    except AmuletItem.DoesNotExist:
        pass

    try:
        amulet_enemy_card = enemy_card.amulet_card.get()
        enemy_card_hp += amulet_enemy_card.amulet_type.bonus_hp
        enemy_card_damage += amulet_enemy_card.amulet_type.bonus_damage
    except AmuletItem.DoesNotExist:
        pass

    return user_card_hp, user_card_damage, enemy_card_hp, enemy_card_damage


def fight_now(user_card: Card, enemy_card: Card) -> tuple[User, User, bool, list[list[str]]]:
    """ Битва возвращает победителя, проигравшего и итог боя """

    user_card_hp, user_card_damage, enemy_card_hp, enemy_card_damage = stats_calculation(user_card, enemy_card)

    can_fight_now = True
    history_fight = []
    turn = -1
    winner = None
    loser = None
    is_victory = False
    while can_fight_now:
        """ Ход пользователя """
        turn += 1
        # Перезапись информации о ходе
        history_fight_turn = [f'Ход {turn + 1} {user_card.owner.username}']

        # Использование способности Дриады защиты
        if enemy_card.class_card.name == 'Дриада':
            enemy_card_hp, heal = use_spell_dryad(enemy_card, enemy_card_hp)
            history_fight_turn.append(formation_of_history(enemy_card, heal))

        # Использование способности Жнеца атаки
        if user_card.class_card.name == 'Жнец':
            answer = use_spell_reaper(user_card, user_card_damage, enemy_card_damage)
            if answer:
                user_card_damage, enemy_card_damage, change = answer
                history_fight_turn.append(formation_of_history(user_card, change))

        enemy_card_hp = round(enemy_card_hp - user_card_damage, 2)
        history_fight_turn.append(f'{user_card.owner.username} наносит {user_card_damage} урона')

        # Использование способности Берсерка атаки
        if user_card.class_card.name == 'Берсерк':
            user_card_damage, change = use_spell_berserk(user_card, user_card_damage)
            history_fight_turn.append(formation_of_history(user_card, change))

        # Использование способности Демона атаки
        if user_card.class_card.name == 'Демон':
            answer = use_spell_demon(user_card, user_card_damage, enemy_card_hp)
            if answer:
                enemy_card_hp, add_damage = answer
                history_fight_turn.append(formation_of_history(user_card, add_damage))

        # Использование способности Оборотня атаки
        if user_card.class_card.name == 'Оборотень':
            answer = use_spell_werewolf(user_card, user_card_hp, user_card_damage)
            if answer:
                user_card_hp, regen_hp = answer
                history_fight_turn.append(formation_of_history(user_card, regen_hp))

        # Использование способности Призрака защиты
        if enemy_card.class_card.name == 'Призрак':
            answer = use_spell_ghost(enemy_card, enemy_card_hp, user_card_damage)
            if answer:
                user_card_hp, evade_damage = answer
                history_fight_turn.append(formation_of_history(enemy_card, evade_damage))

        # Использование способности Бога Императора защиты
        if enemy_card.class_card.name == 'Бог Император':
            user_card_hp, return_damage = use_spell_emperor_mankind(enemy_card, user_card_damage, user_card_hp)
            history_fight_turn.append(formation_of_history(enemy_card, return_damage))

        history_fight_turn.append(f'Здоровье {user_card.owner.username} {user_card_hp}')
        history_fight_turn.append(f'Здоровье {enemy_card.owner.username} {enemy_card_hp}')
        history_fight.append(history_fight_turn)

        """ Проверка на проигравшего """
        if user_card_hp <= 0 and enemy_card_hp <= 0:
            can_fight_now = False
            winner = None
            loser = None
            break
        elif user_card_hp <= 0 or enemy_card_hp <= 0:
            is_victory = True
            loser_hp, winner_hp = sorted([user_card_hp, enemy_card_hp])
            if loser_hp == enemy_card_hp:
                winner, loser = user_card.owner, enemy_card.owner
            else:
                loser, winner = user_card.owner, enemy_card.owner
            break

        """ Ход противника """
        turn += 1
        # Перезапись информации о ходе
        history_fight_turn = [f'Ход {turn + 1} {enemy_card.owner.username}']

        # Использование способности Дриады атаки
        if user_card.class_card.name == 'Дриада':
            user_card_hp, heal = use_spell_dryad(user_card, user_card_hp)
            history_fight_turn.append(formation_of_history(user_card, heal))

        # Использование способности Дриады защиты
        if enemy_card.class_card.name == 'Жнец':
            answer = use_spell_reaper(enemy_card, enemy_card_damage, user_card_damage)
            if answer:
                enemy_card_damage, user_card_damage, change = answer
                history_fight_turn.append(formation_of_history(enemy_card, change))

        user_card_hp = round(user_card_hp - enemy_card_damage, 2)
        history_fight_turn.append(f'{enemy_card.owner.username} наносит {enemy_card_damage} урона')

        # Использование способности Берсерка защиты
        if enemy_card.class_card.name == 'Берсерк':
            enemy_card_damage, change = use_spell_berserk(enemy_card, enemy_card_damage)
            history_fight_turn.append(formation_of_history(enemy_card, change))

        # Использование способности Демона защиты
        if enemy_card.class_card.name == 'Демон':
            answer = use_spell_demon(enemy_card, enemy_card_damage, user_card_hp)
            if answer:
                user_card_hp, add_damage = answer
                history_fight_turn.append(formation_of_history(enemy_card, add_damage))

        # Использование способности Оборотня защиты
        if enemy_card.class_card.name == 'Оборотень':
            answer = use_spell_werewolf(enemy_card, enemy_card_hp, enemy_card_damage)
            if answer:
                enemy_card_hp, regen_hp = answer
                history_fight_turn.append(formation_of_history(enemy_card, regen_hp))

        # Использование способности Призрака атаки
        if user_card.class_card.name == 'Призрак':
            answer = use_spell_ghost(user_card, user_card_hp, enemy_card_damage)
            if answer:
                enemy_card_hp, evade_damage = answer
                history_fight_turn.append(formation_of_history(user_card, evade_damage))

        # Использование способности Бога Императора атаки
        if user_card.class_card.name == 'Бог Император':
            enemy_card_hp, return_damage = use_spell_emperor_mankind(user_card, enemy_card_damage, enemy_card_hp)
            history_fight_turn.append(formation_of_history(user_card, return_damage))

        history_fight_turn.append(f'Здоровье {enemy_card.owner.username} {enemy_card_hp}')
        history_fight_turn.append(f'Здоровье {user_card.owner.username} {user_card_hp}')
        history_fight.append(history_fight_turn)

        """ Проверка на проигравшего """
        if user_card_hp <= 0 and enemy_card_hp <= 0:
            can_fight_now = False
            winner = None
            loser = None
            break
        elif user_card_hp <= 0 or enemy_card_hp <= 0:
            is_victory = True
            loser_hp, winner_hp = sorted([user_card_hp, enemy_card_hp])
            if loser_hp == enemy_card_hp:
                winner, loser = user_card.owner, enemy_card.owner
            else:
                loser, winner = user_card.owner, enemy_card.owner
            break

    return winner, loser, is_victory, history_fight


def use_spell_dryad(card: Card, card_hp: float) -> tuple[float, float]:
    """ Использование способности дриады.
        Восстанавливает свое здоровье в зависимости от уровня слияния.
        Возвращает итоговое количество своего здоровья и полученное лечение.
    """

    heal_hp = card.class_card.numeric_value + 5 * card.merger
    card_hp += heal_hp

    return card_hp, heal_hp


def use_spell_demon(card: Card, card_damage: float, enemy_card_hp: float) -> tuple[float, float] | None:
    """ Использование способности демона.
        Если сработал шанс, то наносит дополнительный урон, в зависимости от своей атаки и уровня слияния.
        Возвращает итоговое количество вражеского здоровья и дополнительный урон или None при неудаче.
    """

    chance = randint(1, 100)
    if chance <= card.class_card.chance_use:
        additional_damage = round(card_damage * (card.class_card.numeric_value + 5 * card.merger) / 100, 2)
        enemy_card_hp = round(enemy_card_hp - additional_damage, 2)

        return enemy_card_hp, additional_damage


def use_spell_werewolf(card: Card, card_hp: float, card_damage: float) -> tuple[float, float] | None:
    """ Использование способности оборотня.
        Если сработал шанс, то восстанавливает свое здоровье в зависимости от базового урона.
        Возвращает итоговое количество своего здоровья и количество восполненного здоровья или None при неудаче.
    """

    chance = randint(1, 100)
    if chance <= card.class_card.chance_use:
        regen_hp = round(card_damage * (card.class_card.numeric_value + 2 * card.merger) / 100, 2)
        card_hp = round(card_hp + regen_hp, 2)

        return card_hp, regen_hp


def use_spell_ghost(card: Card, card_hp: float, enemy_damage: float) -> tuple[float, float] | None:
    """ Использование способности призрака.
        Если сработал шанс, избегает урон от атаки противника (восполнятся здоровье)
        Возвращает итоговое количество своего здоровья или None при неудаче.
    """

    chance = randint(1, 100)
    if chance <= card.class_card.chance_use + 2.5 * card.merger:
        card_hp = round(card_hp + enemy_damage, 2)

        return card_hp, enemy_damage


def use_spell_emperor_mankind(card: Card, enemy_damage: float, enemy_hp: float) -> tuple[float, float]:
    """ Использование способности императора человечества.
        Наносит часть полученного урона атаковавшему.
        Возвращает итоговое количество здоровья нападающего, и количество возвращенного урона.
    """

    return_damage = round((card.class_card.numeric_value + 3 * card.merger) * enemy_damage / 100, 2)
    enemy_hp = round(enemy_hp - return_damage, 2)

    return enemy_hp, return_damage


def use_spell_berserk(card: Card, card_damage: float) -> tuple[float, float]:
    """ Использование способности берсерка.
        Увеличивает свой урон.
        Возвращает итоговое значение своего урона.
    """

    change = round(1 + 0.5 * card.merger, 2)
    up_damage = round(card_damage + change, 2)

    return up_damage, change


def use_spell_reaper(card: Card, card_damage: float, enemy_card_damage: float) -> tuple[float, float, float] | None:
    """ Использование способности жнеца.
        Если сработал шанс, понижает урон противника и повышает свой.
        Возвращает итоговые значения урона карты пользователя и карты противника или None при неудаче.
    """

    chance = randint(1, 100)
    if chance <= card.class_card.chance_use + 0.8 * card.merger:
        change = round(enemy_card_damage * (card.class_card.numeric_value + 2 * card.merger) / 100, 2)
        card_damage = round(card_damage + change, 2)
        enemy_card_damage = round(enemy_card_damage - change, 2)

        return card_damage, enemy_card_damage, change


def formation_of_history(card: Card, value: float) -> str:
    """ Создание текста для записи в историю ходов
        при использовании способности карты
    """

    description_move = (f'Используется способность {card.owner.username}-' +
                        f'{card.class_card.name} ' +
                        f'"{card.class_card.skill}" и ' +
                        f'{card.class_card.description_for_history_fight} ' +
                        f'{value}')

    return description_move


def filling_missing_data():
    """ Заполнение данных о создании у карт, созданных изначально.
        Для разработки
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


def delete_all_record() -> None:
    """ Удаление всех записей в таблице с историей получения карт """

    table = HistoryReceivingCards.objects.all()
    for a in table:
        a.delete()


def accrue_experience(accrued_experience: float, current_level: int, max_level: int,
                      expended_experience: int = 0, current_exp: int = 0):
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


def calculate_need_exp(level: int) -> float:
    """ Вычисление необходимого уровня для получения следующего уровня """

    return round(1000 + 100 * 1.15 ** level, 2)
