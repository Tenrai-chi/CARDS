from datetime import date, datetime
from random import choice, randint
from typing import Optional
from math import ceil

from celery.utils.functional import pass1
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import Card, Rarity, FightHistory, Type, ClassCard, News
from .utils import calculate_need_exp, fight_now

from common.utils import time_difference_check, date_time_now
from exchange.models import (UsersInventory, ExperienceItems, AmuletItem, AmuletType,
                             InitialEventAwards, BattleEventParticipants, TeamsForBattleEvent, BattleEventAwards)
from users.models import Transactions, Profile


class BattleEventData:
    """ Класс для структурирования данных, необходимых для вывода информации о боевом событии.
        С 1 по 10 день (активная фаза события):
            - user_event_participant Участник (Пользователь)
            - enemy_user Противник в этот день
            - team_user, team_enemy Команды обоих участников
            - points Очки пользователя
            - rating Таблица рейтинга и наградами
            - can_fight Возможность бросить вызов (если битва уже состоялась can_fight - False)
        С 11 по конец месяца (стадия подготовки):
            - user_team_template Шаблон команды для участия в следующем сезоне.
        Общее:
            - message_info - Сообщение для пользователя
    """

    # Общие лдя всех дней
    message_info: Optional[str]

    # Параметры для дней с 1 по 10
    user_event_participant: Optional[BattleEventParticipants]
    enemy_user: Optional[BattleEventParticipants]
    team_user: Optional[list[Card]]
    team_enemy: Optional[list[Card]]
    points: Optional[int]
    rating: Optional[list[list]]
    can_fight: Optional[bool]

    # Параметры для дней с 11 по 31
    user_team_template: Optional[list[Card]]

    def __init__(self,
                 user_event_participant: Optional[BattleEventParticipants] = None,
                 enemy_user: Optional[BattleEventParticipants] = None,
                 team_user: Optional[list[Card]] = None,
                 team_enemy: Optional[list[Card]] = None,
                 points: Optional[int] = None,
                 rating: Optional[list[list]] = None,
                 can_fight: Optional[bool] = None,
                 message_info: Optional[str] = None,
                 user_team_template: Optional[list[Card]] = None):

        self.user_event_participant = user_event_participant
        self.enemy_user = enemy_user
        self.team_user = team_user
        self.team_enemy = team_enemy
        self.points = points
        self.rating = rating
        self.can_fight = can_fight
        self.message_info = message_info
        self.user_team_template = user_team_template


class FightBattleEventData:
    """ Класс для структурирования данных о прошедшей битве в боевом событии.
        При возникновении ошибки:
            - error_message Сообщение об ошибке
        При успешной битве:
            - result_fight результат всех битв между пользователями (3 пары)
            - add_points Полученные очки события
    """

    result_fight: Optional[list[list]]
    add_points: Optional[int]
    error_message: Optional[str]

    def __init__(self,
                 result_fight: Optional[list[list]] = None,
                 add_points: Optional[int] = None,
                 error_message: Optional[str] = None):

        self.result_fight = result_fight
        self.add_points = add_points
        self.error_message = error_message


class FightData:
    """ Класс для структурирования данных, для вывода информации о битве между игроками.
        Общие параметры:
            - history_fight История битвы
            - reward_item_user Выпавшие предметы
            - reward_amulet_user Выпавшие амулеты
            - is_victory Есть ли победитель
        Если была ничья is_victory - False:
            - user Напавший пользователь
            - enemy Противник в битве
        Если победитель определен:
            - winner Победитель
            - loser Проигравший
    """

    reward_item_user: Optional[list]
    reward_amulet_user: Optional[list]
    history_fight: Optional[list[list]]
    is_victory: Optional[bool]

    winner: Optional[User]
    loser: Optional[User]
    user: Optional[User]
    enemy: Optional[User]

    def __init__(self,
                 reward_item_user: Optional[list] = None,
                 reward_amulet_user: Optional[list] = None,
                 history_fight: Optional[list[list]] = None,
                 is_victory: Optional[bool] = None,
                 winner: Optional[User] = None,
                 loser: Optional[User] = None,
                 user: Optional[User] = None,
                 enemy: Optional[User] = None,
                 error_message: Optional[str] = None):

        self.reward_item_user = reward_item_user
        self.reward_amulet_user = reward_amulet_user
        self.history_fight = history_fight
        self.is_victory = is_victory

        self.winner = winner
        self.loser = loser
        self.user = user
        self.enemy = enemy
        self.error_message = error_message


def get_info_battle_event(today: int, user_id: int) -> BattleEventData:
    """ Возвращает информацию о боевом событии в зависимости от текущего дня события """

    if today <= 10:
        battle_event_data: BattleEventData = battle_event_fight_stage(today, user_id)

    elif today <= 31:
        battle_event_data: BattleEventData = battle_event_prepare_stage(user_id)

    else:
        raise ValueError(f'Принят неверный день месяца today: {today}')
    return battle_event_data


def get_news_with_pagination(page_num: int = 1, item_per_page: int = 10) -> dict:
    """ Возвращает список новостей с учетом пагинации """

    news = News.objects.all().order_by('-date_time_create')
    paginator = Paginator(news, item_per_page)
    page = paginator.get_page(page_num)
    answer_data = {'news': page.object_list,
                   'page': page
                   }

    return answer_data


def get_info_start_event(user_id: int) -> dict:
    """ Возвращает информацию о стартовом событии """

    answer_data = {}
    user_profile = Profile.objects.get(user=user_id)
    answer_data['user_profile'] = user_profile
    answer_data['event_awards'] = InitialEventAwards.objects.all().order_by('id')
    if user_profile.date_event_visit is None or user_profile.date_event_visit < datetime.now().date():
        answer_data['show_button'] = True
    else:
        answer_data['show_button'] = False

    return answer_data


def set_card_in_template_team(user_id: int, place: int, current_card_id: int) -> dict:
    """ Устанавливает текущую карту на выбранное место в команде.
        Если карта уже была в команде, то она меняет свое положение в отряде,
        а занимаемое ею место становится пустым.
        При ошибке возвращает сообщение для пользователя.
    """

    answer_data = {}
    current_card = get_object_or_404(Card, pk=current_card_id)
    if current_card.owner.id != user_id:
        answer_data['error_message'] = 'Вы не можете добавить эту карту в команду'
        return answer_data

    user = User.objects.get(pk=user_id)
    user_team, _ = TeamsForBattleEvent.objects.get_or_create(user=user)
    if current_card == user_team.first_card:
        user_team.first_card = None
        user_team.save()
    elif current_card == user_team.second_card:
        user_team.second_card = None
        user_team.save()
    elif current_card == user_team.third_card:
        user_team.third_card = None
        user_team.save()

    if place == 1:
        user_team.first_card = current_card
        user_team.save()
    elif place == 2:
        user_team.second_card = current_card
        user_team.save()
    elif place == 3:
        user_team.third_card = current_card
        user_team.save()
    else:
        answer_data['error_message'] = 'Неправильная позиция в команде'
    return answer_data


def fight_battle_event(user_id: int, enemy_id: int) -> FightBattleEventData:
    """ Битва в боевом событии.
        Проверяет возможность бросить вызов,
        Если вызов возможен, то начисляет очки в зависимости от исходов боев,
        отмечает факт битвы и возвращает команды противников и итоги каждого боя
        При невозможности состязания, возвращает сообщение об ошибке.
        При удаче возвращает данные о битве.
    """

    today = date.today().day
    if today > 10:
        error_message = 'Событие завершилось, дождитесь следующего сезона, чтобы участвовать'
        return FightBattleEventData(error_message=error_message)

    user_info = BattleEventParticipants.objects.filter(user=user_id).last()
    if user_info is None:
        error_message = 'Вы не участвуете в событии'
        return FightBattleEventData(error_message=error_message)

    enemy_info = BattleEventParticipants.objects.filter(user__id=enemy_id).last()
    if enemy_info is None:
        error_message = 'Противник не участвует в событии'
        return FightBattleEventData(error_message=error_message)

    if user_info.enemies.get(str(today)) != enemy_id:
        error_message = 'Вы не можете сразиться с этим участником'
        return FightBattleEventData(error_message=error_message)

    if user_info.battle_progress.get(str(today)):
        error_message = 'Вы уже сражались сегодня с этим участником'
        return FightBattleEventData(error_message=error_message)

    team_user: list[Card] = get_team_battle_event(user_id)
    team_enemy: list[Card] = get_team_battle_event(enemy_id)

    all_results = [fight_now(team_user[pair], team_enemy[pair]) for pair in range(3)]

    points_user = 0
    points_enemy = 0
    result_fight = []
    result_fight_ind = -1
    for result in all_results:
        result_fight_ind += 1
        is_victory = result.get('is_victory')
        winner = result.get('winner')
        if not is_victory:
            points_user += 2
            points_enemy += 2
            result_fight.append([team_user[result_fight_ind], team_enemy[result_fight_ind], 'Ничья'])
        else:
            if winner.pk == user_id:
                points_user += 3
                points_enemy += 1
                result_fight.append([team_user[result_fight_ind], team_enemy[result_fight_ind], 'Победа'])
            else:
                points_enemy += 3
                points_user += 1
                result_fight.append([team_user[result_fight_ind], team_enemy[result_fight_ind], 'Поражение'])

    add_points = None
    if points_user > points_enemy:
        add_points = 100
    elif points_user < points_enemy:
        add_points = 40
    elif points_user == points_enemy:
        add_points = 60
    user_info.points += add_points
    user_info.battle_progress[str(today)] = True
    user_info.save()

    return FightBattleEventData(result_fight=result_fight,
                                add_points=add_points)


@transaction.atomic
def fight_users(attacker_id: int, protector_id: int) -> FightData:
    """ Рейтинговый бой между двумя игроками с использованием избранных карт.
        Запускает сервисы:
            - Проверка возможности битвы.
            - Ход и результат битвы.
            - Начисление награды (золото) за участие в битве.
            - Начисление опыта карте пользователя.
            - Обновление статистики побед и поражений у обоих пользователей.
            - Начисление очков гильдии пользователю
            - Начисление награды за бой (выпадение лута)
        Создает запись в FightHistory о прошедшем бое.
    """

    # Проверка возможности битвы между пользователями
    validate_result: dict = validate_battle_preconditions(attacker_id, protector_id)
    if validate_result.get('error_message'):
        return FightData(error_message=validate_result['error_message'])
    else:
        attacker = validate_result.get('attacker')
        protector = validate_result.get('protector')

    # 2. Битва и ее итог
    result_fight: dict = fight_now(attacker.profile.current_card, protector.profile.current_card)
    is_victory = result_fight.get('is_victory')
    history_fight = result_fight.get('history_fight')
    winner = result_fight.get('winner')
    loser = result_fight.get('loser')
    user = result_fight.get('user')
    enemy = result_fight.get('enemy')

    # 3. Изменение статистики win\lose
    update_win_lose(winner, loser, is_victory)

    # 4. Увеличение характеристик карты пользователя
    update_card_experience(attacker.profile.current_card)

    # 5. Начисление золота и очков гильдии в зависимости от исхода битвы
    if is_victory:
        if attacker == winner:
            award_gold_for_attack(attacker, 2)
            award_guild_points(attacker.profile, 2)
        else:
            award_gold_for_attack(attacker, 0)
            award_guild_points(attacker.profile, 0)
    else:
        award_gold_for_attack(attacker, 1)
        award_guild_points(attacker.profile, 1)

    # 6. Выпадение предметов после боя
    loot: dict = award_loot_items(attacker.profile)
    reward_item_user = loot.get('reward_item_user')
    reward_amulet_user = loot.get('reward_amulet_user')

    # 7. Создание записи о бое в истории
    new_record = FightHistory.objects.create(date_and_time=date_time_now(),
                                             winner=winner,
                                             loser=loser,
                                             card_winner=winner.profile.current_card,
                                             card_loser=loser.profile.current_card
                                             )

    fight_data = FightData(reward_item_user=reward_item_user,
                           reward_amulet_user=reward_amulet_user,
                           history_fight=history_fight,
                           is_victory=is_victory,
                           winner=winner,
                           loser=loser,
                           user=user,
                           enemy=enemy)

    return fight_data


@transaction.atomic
def get_user_award_start_event(user_id) -> dict:
    """ Начисление награды пользователю в стартовом событии.
        Пользователь получает награду за отметку дня, если она еще не получена.
        Количество совершенных входов пользователя увеличивается.
        Если награда 30 дня (UR карта), то создает ее и присваивает пользователю.
        Возвращает сообщение об успехе или ошибке
    """

    answer_data = {}
    user_profile = Profile.objects.get(user=user_id)
    if user_profile.event_visit >= 30:
        answer_data['error_message'] = 'Вы получили все награды из этого события)'
        return answer_data

    if user_profile.date_event_visit is None or user_profile.date_event_visit < datetime.now().date():

        award = InitialEventAwards.objects.get(day_event_visit=user_profile.event_visit + 1)
        if award.type_award in ['Маленькая книга опыта', 'Средняя книга опыта', 'Большая книга опыта']:
            try:
                books_user = UsersInventory.objects.get(owner=user_id, item__name=award.type_award)
                books_user.amount += int(award.amount_or_rarity_award)
                books_user.save()
            except UsersInventory.DoesNotExist:
                book = ExperienceItems.objects.get(name=award.type_award)
                books_user = UsersInventory.objects.create(owner=user_profile.user,
                                                           item=book,
                                                           amount=int(award.amount_or_rarity_award))
                books_user.save()

            answer_data['success_message'] = f'Вы получили награду! {award.type_award} {award.amount_or_rarity_award}'

        elif award.type_award == 'Золото':
            user_profile.get_gold(int(award.amount_or_rarity_award))
            new_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                          user=user_profile.user,
                                                          before=user_profile.gold,
                                                          after=user_profile.gold + int(award.amount_or_rarity_award),
                                                          comment='Награда стартового события'
                                                          )
            new_transaction.save()
            answer_data['success_message'] = f'Вы получили награду! {award.type_award} {award.amount_or_rarity_award}'

        elif award.type_award == 'Амулет':
            amulet = AmuletType.objects.get(name=award.amount_or_rarity_award)
            user_amulet = AmuletItem.objects.create(owner=user_profile.user, amulet_type=amulet)
            user_amulet.save()
            answer_data['success_message'] = f'Вы получили награду! {award.amount_or_rarity_award}'

        elif award.type_award == 'Карта':
            type_card = choice(Type.objects.all())
            class_card = choice(ClassCard.objects.all())
            rarity = Rarity.objects.get(name=award.amount_or_rarity_award)

            user_card = Card.objects.create(owner=user_profile.user,
                                            level=1,
                                            class_card=class_card,
                                            type=type_card,
                                            rarity=rarity,
                                            hp=rarity.max_hp,
                                            damage=rarity.max_damage)
            user_card.save()
            user_profile.add_event_visit()
            answer_data['success_message'] = f'Вы получили карту {award.amount_or_rarity_award} с максимальными характеристиками!'
            answer_data['card_id'] = user_card.id
            return answer_data

        else:
            answer_data['error_message'] = 'Что-то пошло не так... Упс'
            return answer_data

        user_profile.add_event_visit()
        return answer_data
    else:
        answer_data['error_message'] = 'Вы уже получили награду за сегодня'
        return answer_data


def select_favorite_card_service(user_id: int, card_id: int) -> dict:
    """ Установка избранной карты пользователя.
        Изменяет current_card в профиле пользователя на выбранную карту.
        Возвращает сообщение об успехе или ошибке.
    """

    answer_data = {}
    card = get_object_or_404(Card, pk=card_id)
    if card.owner.id != user_id:
        answer_data['error_message'] = 'Вы не являетесь владельцем карты!'
        return answer_data

    user_profile = Profile.objects.get(user=user_id)
    user_profile.current_card = card
    user_profile.save()

    answer_data['success_message'] = 'Вы успешно установили избранную карту'
    return answer_data


def battle_event_fight_stage(today: int, user_id: int) -> BattleEventData:
    """ Информация во время основного этапа боевого события с 1 по 10 день.
        - Если пользователь не участвует, то возвращает сообщение об этом.
        - Если участвует, то возвращает текущего противника, команды обоих пользователей
        и таблицу текущего рейтинга события с наградами.
    """

    user = User.objects.get(pk=user_id)

    if len(BattleEventParticipants.objects.all()) < 2:
        battle_event_data = BattleEventData(message_info='В этом сезоне недостаточно участников(')
        return battle_event_data

    user_event_participant = BattleEventParticipants.objects.filter(user=user).last()
    if user_event_participant is None:
        battle_event_data = BattleEventData(message_info='Вы не участвуете в этом сезоне')
        return battle_event_data

    enemy_id = user_event_participant.enemies.get(str(today))
    enemy = BattleEventParticipants.objects.get(user=enemy_id)

    team_user: list[Card] = get_team_battle_event(user_id)
    team_enemy: list[Card] = get_team_battle_event(enemy_id)

    battle_progress_this_day = user_event_participant.battle_progress.get(str(today))

    top_list: list = get_info_top_battle_event()
    can_fight = not battle_progress_this_day

    battle_event_data = BattleEventData(team_user=team_user,
                                        team_enemy=team_enemy,
                                        points=user_event_participant.points,
                                        rating=top_list,
                                        enemy_user=enemy,
                                        can_fight=can_fight)

    return battle_event_data


def get_team_battle_event(user_id) -> list[Card]:
    """ Возвращает список из карт в команде запрашиваемого пользователя.
        Гарантируется, что пользователь существует,
        а все карты в его команде не None.
    """

    participant = BattleEventParticipants.objects.select_related(
        'first_card', 'second_card', 'third_card').get(user_id=user_id)

    participant_team = [participant.first_card,
                        participant.second_card,
                        participant.third_card]

    return participant_team


def get_info_top_battle_event() -> list:
    """ Возвращает данные для таблицы рейтинга в боевом событии """

    max_top_rows = 5
    top_list = []
    rating = BattleEventParticipants.objects.filter(points__gt=0).order_by('-points')[:5]
    be_event_awards = BattleEventAwards.objects.all().order_by('rank')

    for ind in range(max_top_rows):
        try:
            place = [be_event_awards[ind].rank,
                     rating[ind].user.username,
                     rating[ind].points,
                     be_event_awards[ind].amount]
            top_list.append(place)
        except IndexError as _:
            place = [be_event_awards[ind].rank,
                     None,
                     None,
                     be_event_awards[ind].amount]
            top_list.append(place)

    return top_list


def battle_event_prepare_stage(user_id: int) -> BattleEventData:
    """ Информация во время подготовительного этапа боевого события с 11 по 31 день.
        Выводит шаблон команды для участия в боевом событии
    """

    user = User.objects.get(pk=user_id)
    user_team_template, _ = TeamsForBattleEvent.objects.get_or_create(user=user)
    team_template_ids = []
    if user_team_template.first_card:
        team_template_ids.append(user_team_template.first_card.id)
    else:
        team_template_ids.append(None)
    if user_team_template.second_card:
        team_template_ids.append(user_team_template.second_card.id)
    else:
        team_template_ids.append(None)
    if user_team_template.third_card:
        team_template_ids.append(user_team_template.third_card.id)
    else:
        team_template_ids.append(None)
    team_template = []
    for team_template_id in team_template_ids:
        team_template.append(Card.objects.filter(pk=team_template_id).last())
    battle_event_data = BattleEventData(user_team_template=team_template)
    return battle_event_data


def validate_battle_preconditions(attacker_id: int, protector_id: int) -> dict:
    """ Проверка на возможность проведения рейтингового боя между 2 участниками.
        Если проверки не прошли, возвращает error_message с сообщением об ошибке.
        Если битва может состояться, то возвращает объекты пользователя нападения и защиты.
    """

    answer_data = {}
    if attacker_id == protector_id:
        answer_data['error_message'] = 'Для боя необходимо выбрать противника!'
        return answer_data

    attacker = User.objects.get(pk=attacker_id)
    protector = get_object_or_404(User, pk=protector_id)

    last_fight = FightHistory.objects.filter(
        Q(winner=protector, loser=attacker) | Q(winner=attacker, loser=protector)).order_by('id').last()

    # Проверка есть ли в истории боев бой между этими пользователями
    if last_fight is not None:
        can_fight, hours = time_difference_check(last_fight.date_and_time, 6)

        # Если бой есть и прошло менее 6 часов, то нельзя
        if not can_fight:
            error_message = f'Вы пока не можете бросить вызов этому пользователю! Осталось времени: {6 - hours} часов'
            answer_data['error_message'] = error_message
            return answer_data

    if protector.profile.current_card is None or protector.profile.current_card is None:
        answer_data['error_message'] = 'Для боя необходимо чтобы у обоих соперников были выбраны карты'
        return answer_data

    answer_data['attacker'] = attacker
    answer_data['protector'] = protector

    return answer_data


def award_gold_for_attack(user: User, result_battle: int) -> None:
    """ Начисление золота пользователю в рейтинговой битве.
        Начисляет золото в зависимости от итога боя и наличия усиления гильдии.
        Создает транзакцию.
        result_battle 0 - проигрыш, 1 - ничья, 2 - победа.
    """

    gold_for_win = 100
    gold_for_draw = 75
    gold_for_lose = 50

    old_user_gold = user.profile.gold
    if result_battle == 0:
        comment = 'Награда за поражение в битве'
        user.profile.get_gold(gold_for_lose)
    elif result_battle == 1:
        comment = 'Награда за ничью в битве'
        user.profile.get_gold(gold_for_draw)
    elif result_battle == 2:
        comment = 'Награда за победу в битве'
        if user.profile.guild.buff.name == 'Бандитский улов':
            user.profile.get_gold(ceil(gold_for_win * user.profile.guild.buff.numeric_value / 100))
        else:
            user.profile.get_gold(gold_for_win)
    else:
        raise ValueError(f'Принят неверный результат битвы result_battle: {result_battle}')

    transaction_user = Transactions.objects.create(date_and_time=date_time_now(),
                                                   user=user,
                                                   before=old_user_gold,
                                                   after=user.profile.gold,
                                                   comment=comment
                                                   )


def update_card_experience(card: Card) -> None:
    """ Получение опыта карты в битве """

    # Начисление опыта, если не достигнут максимальный уровень карты (вынести)
    if card.level < card.rarity.max_level:
        card.experience_bar += 75

    # Увеличение уровня карты победителя при достижении определенного опыта (вынести)
    if card.experience_bar >= calculate_need_exp(card.level):
        card.experience_bar -= calculate_need_exp(card.level)
        card.level += 1

        # Если достигнут максимальный уровень, прогресс опыта обнуляется
        if card.level == card.rarity.max_level:
            card.experience_bar = 0

        # Увеличение характеристик карты победителя (вынести)
        card.increase_stats()
        card.save()


def update_win_lose(winner: Optional[Profile], loser: Optional[Profile], is_victory: bool) -> None:
    """ Обновление статистики побед/поражений у обоих участников рейтинговой битвы.
        result_battle 0 - проигрыш, 1 - ничья, 2 - победа.
    """

    if is_victory:
        winner.profile.win += 1
        loser.profile.lose += 1

        winner.save()
        loser.save()


def award_guild_points(user: Profile, result_battle: str) -> None:
    """ Начисление очков гильдии за участие в рейтинговом бою """

    if user.guild is not None:
        if result_battle == 0:
            user.get_guild_point('lose')
            user.guild.add_guild_points('lose')
        elif result_battle == 1:
            user.get_guild_point('draw')
            user.guild.add_guild_points('draw')
        elif result_battle == 2:
            user.get_guild_point('win')
            user.guild.add_guild_points('win')
        else:
            raise ValueError(f'Принят неверный результат битвы result_battle: {result_battle}')


def award_loot_items(user: Profile) -> dict:
    """ Выпадение предметов за бой.
        Возвращает списки полученных амулетов и книг опыта.
    """

    answer_data = {}
    # Предметы падают только нападавшему
    items = ExperienceItems.objects.all()
    amulets = AmuletType.objects.exclude(rarity__chance_drop_on_fight=0)
    reward_item_user = []
    reward_amulet_user = []
    for item in items:  # Проверка выпадения предмета
        chance = randint(1, 100)

        # Использование способности эльфа
        if user.current_card.class_card.name == 'Эльф':
            chance_drop = item.chance_drop_on_fight + (
                    user.current_card.class_card.numeric_value + 4 * user.current_card.merger)
        else:
            chance_drop = item.chance_drop_on_fight

        if chance <= chance_drop:
            try:
                items_user = UsersInventory.objects.get(owner=user.user,
                                                        item=item)
                items_user.amount += 1
                items_user.save()
                reward_item_user.append(item)
            except UsersInventory.DoesNotExist:
                new_record_inventory = UsersInventory.objects.create(owner=user.user,
                                                                     item=item,
                                                                     amount=1
                                                                     )
                new_record_inventory.save()
                reward_item_user.append(item)
    if user.amulet_slots > AmuletItem.objects.filter(owner=user.user).count():
        for amulet in amulets:  # Проверка выпадения амулета
            # Использование способности эльфа
            if user.current_card.class_card.name == 'Эльф':
                chance_drop = amulet.rarity.chance_drop_on_fight + user.current_card.class_card.numeric_value
            else:
                chance_drop = amulet.rarity.chance_drop_on_fight

            chance = randint(1, 100)
            if chance <= chance_drop:
                new_amulet = AmuletItem.objects.create(amulet_type=amulet,
                                                       owner=user.user)
                new_amulet.save()
                reward_amulet_user.append(amulet)

    answer_data['reward_item_user'] = reward_item_user
    answer_data['reward_amulet_user'] = reward_amulet_user
    return answer_data
