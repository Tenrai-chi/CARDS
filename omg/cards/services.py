from datetime import datetime, date
from random import choice, randint
from typing import Optional

from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import Card, Rarity, CardStore, HistoryReceivingCards, FightHistory, Type, ClassCard, News
from .utils import calculate_need_exp, fight_now as f_n

from common.utils import time_difference_check, create_new_card, date_time_now
from exchange.models import (SaleUserCards, UsersInventory, ExperienceItems, AmuletItem, AmuletType,
                             InitialEventAwards, BattleEventParticipants, TeamsForBattleEvent, BattleEventAwards)
from users.models import Transactions, Profile, SaleStoreCards


class StartEventData:
    """ Класс для структурирования данных, необходимых для вывода информации о стартовом событии """

    user_profile: Profile
    event_awards: list[InitialEventAwards]
    show_button: bool = False

    def __init__(self, user_profile: Profile, event_awards: list[InitialEventAwards], show_button: bool):
        self.user_profile = user_profile
        self.event_awards = event_awards
        self.show_button = show_button


class BattleEventData:
    """ Класс для структурирования данных, необходимых для вывода информации о боевом событии """

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
    """ Класс для структурирования данных о прошедшей битве в боевом событии """

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
    """ Класс для структурирования данных, необходимых для вывода информации о битве между игроками """

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
    """ Возвращает информацию о боевом событии в зависимости от текущего дня события.
        С 1 по 10:
            - Если пользователь не участвует, то возвращает сообщение об этом.
            - Если участвует, то возвращает текущего противника, команды обоих пользователей
            и возможность бросить сопернику вызов, полученные очки и таблицу рейтинга
        С 11 по 31:
            - Выводит шаблон команды пользователя для изменения
    """

    user = User.objects.get(pk=user_id)
    if today <= 10:
        user_event_participant = BattleEventParticipants.objects.filter(user=user).last()
        if user_event_participant is None:
            battle_event_data = BattleEventData(message_info='Вы не участвуете в этом сезоне')
            return battle_event_data
        team_user_ids = (user_event_participant.first_card.id,
                         user_event_participant.second_card.id,
                         user_event_participant.third_card.id)
        enemy_id = user_event_participant.enemies.get(str(today))
        enemy = BattleEventParticipants.objects.get(user=enemy_id)
        team_enemy_ids = (enemy.first_card.id, enemy.second_card.id, enemy.third_card.id)
        team_user = []
        team_enemy = []
        for user_team_id in team_user_ids:
            team_user.append(Card.objects.get(pk=user_team_id))
        for team_enemy_id in team_enemy_ids:
            team_enemy.append(Card.objects.get(pk=team_enemy_id))
        battle_progress_this_day = user_event_participant.battle_progress.get(str(today))
        rating = BattleEventParticipants.objects.filter(points__gt=0).order_by('-points')[:5]
        be_event_awards = BattleEventAwards.objects.all().order_by('rank')

        top_list = []
        for ind in range(0, 5):
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
        can_fight = not battle_progress_this_day

        battle_event_data = BattleEventData(team_user=team_user,
                                            team_enemy=team_enemy,
                                            points=user_event_participant.points,
                                            rating=top_list,
                                            enemy_user=enemy,
                                            can_fight=can_fight)
    else:
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


def get_news_with_pagination(page_num: int = 1, item_per_page: int = 10) -> dict:
    """ Возвращает список новостей с учетом пагинации """

    news = News.objects.all().order_by('-date_time_create')
    paginator = Paginator(news, item_per_page)
    page = paginator.get_page(page_num)
    data = {'news': page.object_list,
            'page': page
            }

    return data


def get_info_start_event(user_id: int) -> StartEventData:
    """ Возвращает информацию о стартовом событии """

    user_profile = Profile.objects.get(user=user_id)
    event_awards = InitialEventAwards.objects.all().order_by('id')
    if user_profile.date_event_visit is None or user_profile.date_event_visit < datetime.now().date():
        show_button = True
    else:
        show_button = False

    return StartEventData(user_profile, event_awards, show_button)


def get_cards_with_pagination(page_num: int = 1, item_per_page: int = 21) -> dict:
    """ Возвращает список всех карт с учетом пагинации """

    cards = Card.objects.all().order_by('-pk')
    paginator = Paginator(cards, item_per_page)
    page = paginator.get_page(page_num)
    data = {'cards': page.object_list,
            'page': page
            }

    return data


@transaction.atomic
def create_free_card(user_id: int) -> dict:
    """ Генерация новой карты пользователя при бесплатном получении.
        Если возникла ошибка, то возвращает ошибку, сообщение об ошибке и имя для перенаправления
    """

    data = {}
    user = User.objects.get(pk=user_id)
    user_profile = Profile.objects.get(user=user)
    if Card.objects.filter(owner=user_id).count() == user_profile.card_slots:
        data['error'] = True
        data['message_error'] = 'У вас не хватает места для получения новой карты!'
        data['return_name'] = 'card_store'
        return data

    take_card, hours = time_difference_check(user_profile.receiving_timer, 6)

    if take_card:
        new_card = create_new_card(user_id=user_id)

        new_record = HistoryReceivingCards.objects.create(date_and_time=date_time_now(),
                                                          method_receiving='Бесплатная генерация',
                                                          card=new_card,
                                                          user=user
                                                          )
        new_record.save()

        user_profile.update_receiving_timer()
        data['new_card_id'] = new_card.id

    else:
        data['error'] = True
        data['message_error'] = 'Вы пока не можете получить бесплатную карту'
        data['return_name'] = 'home'
    return data


def set_card_in_template_team(user_id: int, place: int, current_card_id: int) -> dict:
    """ Устанавливает текущую карту на выбранное место в команде.
        Если карта уже была в команде, то она меняет свое положение в отряде,
        а занимаемое ею место становится пустым.
        При ошибке возвращает сообщение для пользователя.
    """

    data = {}
    current_card = get_object_or_404(Card, pk=current_card_id)
    if current_card.owner.id != user_id:
        data['error_message'] = 'Вы не можете добавить эту карту в команду'
        return data

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
        data['error_message'] = 'Неправильная позиция в команде'
    return data


@transaction.atomic
def purchase_card(user_id: int, card_id: int) -> dict:
    """ Процесс покупки карты.
        Создает карту по шаблону выбранной карты в магазине и присваивает ее текущему пользователю.
        У пользователя в Profile изменяется gold на значение равное цене карты.
    """

    data = {}
    user = User.objects.get(pk=user_id)
    user_profile = Profile.objects.get(user=user)
    selected_card = CardStore.objects.get(pk=card_id)

    if user_profile.gold < selected_card.price:
        data['error_message'] = 'У вас не хватает средств для покупки!'
        return data

    if Card.objects.filter(owner=user).count() >= user_profile.card_slots:
        data['error_message'] = 'У вас не хватает места для покупки новой карты!'
        return data

    new_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                  user=user,
                                                  before=user_profile.gold,
                                                  after=user_profile.gold - selected_card.price,
                                                  comment='Покупка в магазине карт'
                                                  )
    new_transaction.save()

    user_profile.gold -= selected_card.price
    user_profile.save()

    sale_card = SaleStoreCards.objects.create(date_and_time=date_time_now(),
                                              sold_card=selected_card,
                                              transaction=new_transaction
                                              )
    sale_card.save()

    new_card = Card.objects.create(owner=user,
                                   level=1,
                                   class_card=selected_card.class_card,
                                   type=selected_card.type,
                                   rarity=selected_card.rarity,
                                   hp=selected_card.hp,
                                   damage=selected_card.damage
                                   )

    new_record = HistoryReceivingCards.objects.create(date_and_time=date_time_now(),
                                                      method_receiving='Покупка в магазине',
                                                      card=new_card,
                                                      user=user
                                                      )
    new_record.save()
    data['new_card_id'] = new_card.id

    return data


def fight_battle_event(user_id: int, enemy_id: int) -> FightBattleEventData:
    """ Битва в боевом событии.
        Проверяет возможность бросить вызов,
        Если вызов возможен, то начисляет очки в зависимости от исходов боев,
        отмечает факт битвы и возвращает команды противников и итоги каждого боя
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

    user_first_card = Card.objects.get(pk=user_info.first_card.pk)
    user_second_card = Card.objects.get(pk=user_info.second_card.pk)
    user_third_card = Card.objects.get(pk=user_info.third_card.pk)

    enemy_first_card = Card.objects.get(pk=enemy_info.first_card.pk)
    enemy_second_card = Card.objects.get(pk=enemy_info.second_card.pk)
    enemy_third_card = Card.objects.get(pk=enemy_info.third_card.pk)

    all_results = [f_n(user_first_card, enemy_first_card),
                   f_n(user_second_card, enemy_second_card),
                   f_n(user_third_card, enemy_third_card)]

    team_user = [user_first_card, user_second_card, user_third_card]
    team_enemy = [enemy_first_card, enemy_second_card, enemy_third_card]
    points_user = 0
    points_enemy = 0
    result_fight = []
    result_fight_ind = -1
    for result in all_results:
        result_fight_ind += 1
        winner, loser, is_victory, _ = result
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
        Проверяет есть ли у обоих пользователей выбранная карта.
        Проверяет время последнего боя между двумя пользователями. Если прошло больше 6 часов, происходит битва.
        После битвы начисляются опыт в experience_bar карты пользователя.
        Если опыта достаточно, то увеличивается уровень карты и ее характеристики.
        В Profile пользователя увеличиваются gold, у обоих win, lose в зависимости от победителя.
        В Transactions появляются запись о начислении денег за победу и проигрыш.
        Создается новая запись в FightHistory.
        Обрабатывается возможность получения книг опыта нападавшему,
        если сработал шанс, то книги появляются в инвентаре.
    """

    attacker = User.objects.get(pk=attacker_id)
    protector = get_object_or_404(User, pk=protector_id)

    # Проверка не один и тот же это человек
    if protector == attacker:
        error_message = 'Для боя необходимо выбрать противника!'
        return FightData(error_message=error_message)

    last_fight = FightHistory.objects.filter(
        Q(winner=protector, loser=attacker) | Q(winner=attacker, loser=protector)).order_by('-id').first()

    # Проверка есть ли в истории боев бой между этими пользователями
    if last_fight is not None:
        can_fight, hours = time_difference_check(last_fight.date_and_time, 6)

        # Если бой есть и прошло менее 6 часов, то нельзя
        if not can_fight:
            error_message = f'Вы пока не можете бросить вызов этому пользователю! Осталось времени: {6 - hours} часов'
            return FightData(error_message=error_message)

    if protector.profile.current_card is None or protector.profile.current_card is None:
        error_message = 'Для боя необходимо чтобы у обоих соперников были выбраны карты'
        return FightData(error_message=error_message)

    #  Если все проверки пройдены, идет битва, где определяются победитель и проигравший, записывается история боя
    winner, loser, is_victory, history_fight = f_n(attacker.profile.current_card, protector.profile.current_card)

    old_user_gold = attacker.profile.gold
    if winner == attacker and winner.profile.guild.buff.name == 'Бандитский улов':
        attacker.profile.get_gold(200)
        comment = 'Награда за победу в битве'
    elif winner == attacker:
        attacker.profile.get_gold(100)
        comment = 'Награда за победу в битве'
    else:
        attacker.profile.get_gold(50)
        comment = 'Награда за проигрыш в битве'

    transaction_user = Transactions.objects.create(date_and_time=date_time_now(),
                                                   user=attacker,
                                                   before=old_user_gold,
                                                   after=attacker.profile.gold,
                                                   comment=comment
                                                   )
    transaction_user.save()

    # Начисление опыта, если не достигнут максимальный уровень карты (вынести)
    if attacker.profile.current_card.level < attacker.profile.current_card.rarity.max_level:
        attacker.profile.current_card.experience_bar += 75

    # Увеличение уровня карты победителя при достижении определенного опыта (вынести)
    if attacker.profile.current_card.experience_bar >= calculate_need_exp(attacker.profile.current_card.level):
        attacker.profile.current_card.experience_bar -= calculate_need_exp(attacker.profile.current_card.level)
        attacker.profile.current_card.level += 1

        # Если достигнут максимальный уровень, прогресс опыта обнуляется
        if attacker.profile.current_card.level == attacker.profile.current_card.rarity.max_level:
            attacker.profile.current_card.experience_bar = 0

        # Увеличение характеристик карты победителя (вынести)
        attacker.profile.current_card.increase_stats()

    if is_victory and winner == attacker:
        attacker.profile.win += 1
        protector.profile.lose += 1
    elif is_victory and winner == protector:
        protector.profile.win += 1
        attacker.profile.lose += 1

    if winner == attacker and attacker.profile.guild is not None:
        attacker.profile.get_guild_point('win')

    attacker.profile.save()
    protector.profile.save()

    attacker.profile.current_card.save()

    new_record = FightHistory.objects.create(date_and_time=date_time_now(),
                                             winner=winner,
                                             loser=loser,
                                             card_winner=winner.profile.current_card,
                                             card_loser=loser.profile.current_card
                                             )
    new_record.save()

    # Предметы падают только нападавшему
    items = ExperienceItems.objects.all()
    amulets = AmuletType.objects.exclude(rarity__chance_drop_on_fight=0)
    reward_item_user = []
    reward_amulet_user = []
    for item in items:  # Проверка выпадения предмета
        chance = randint(1, 100)

        # Использование способности эльфа
        if attacker.profile.current_card.class_card.name == 'Эльф':
            chance_drop = item.chance_drop_on_fight + (
                        attacker.profile.current_card.class_card.numeric_value + 4 * attacker.profile.current_card.merger)
        else:
            chance_drop = item.chance_drop_on_fight

        if chance <= chance_drop:
            try:
                items_user = UsersInventory.objects.get(owner=attacker,
                                                        item=item)
                items_user.amount += 1
                items_user.save()
                reward_item_user.append(item)
            except UsersInventory.DoesNotExist:
                new_record_inventory = UsersInventory.objects.create(owner=attacker,
                                                                     item=item,
                                                                     amount=1
                                                                     )
                new_record_inventory.save()
                reward_item_user.append(item)
    if attacker.profile.amulet_slots > AmuletItem.objects.filter(owner=attacker).count():
        for amulet in amulets:  # Проверка выпадения амулета
            # Использование способности эльфа
            if attacker.profile.current_card.class_card.name == 'Эльф':
                chance_drop = amulet.rarity.chance_drop_on_fight + attacker.profile.current_card.class_card.numeric_value
            else:
                chance_drop = amulet.rarity.chance_drop_on_fight

            chance = randint(1, 100)
            if chance <= chance_drop:
                new_amulet = AmuletItem.objects.create(amulet_type=amulet,
                                                       owner=attacker)
                new_amulet.save()
                reward_amulet_user.append(amulet)

    fight_data = FightData(reward_item_user=reward_item_user,
                           reward_amulet_user=reward_amulet_user,
                           history_fight=history_fight,
                           is_victory=is_victory,
                           winner=winner if is_victory else None,
                           loser=loser if is_victory else None,
                           user=attacker if not is_victory else None,
                           enemy=protector)

    return fight_data


@transaction.atomic
def transfer_card_to_user(card_id: int, buyer_id: int) -> dict:
    """ Покупка карты у пользователя на торговой площадке.
        Проверяет возможна ли покупка. Если нет, то возвращает сообщение об ошибке.
        Изменяет значения gold у обоих пользователей.
        Создает 2 записи в Transaction для продажи и покупки.
    """

    buyer_profile = Profile.objects.get(user=buyer_id)
    card = get_object_or_404(Card, pk=card_id)
    seller_profile = Profile.objects.get(user=card.owner.id)
    answer = {}

    if not card.sale_status:
        answer['error_message'] = 'Эта карта не продается!'
        return answer

    if buyer_profile.card_slots <= Card.objects.filter(owner=buyer_id).count():
        answer['error_message'] = 'У вас не хватает места для покупки новой карты!'
        return answer

    if buyer_profile.gold < card.price:
        answer['error_message'] = 'У вас не хватает средств для покупки!'
        return answer

    transaction_buyer = Transactions.objects.create(date_and_time=date_time_now(),
                                                    user=buyer_profile.user,
                                                    before=buyer_profile.gold,
                                                    after=buyer_profile.gold - card.price,
                                                    comment='Покупка карты у пользователя'
                                                    )
    buyer_profile.gold = buyer_profile.gold - card.price
    buyer_profile.save()

    transaction_seller = Transactions.objects.create(date_and_time=date_time_now(),
                                                     user=seller_profile.user,
                                                     before=seller_profile.gold,
                                                     after=seller_profile.gold + card.price,
                                                     comment='Продажа карты пользователю'
                                                     )
    seller_profile.gold = seller_profile.gold + card.price
    seller_profile.save()

    sale_user_card = SaleUserCards.objects.create(date_and_time=date_time_now(),
                                                  buyer=buyer_profile.user,
                                                  salesman=seller_profile.user,
                                                  card=card,
                                                  price=card.price,
                                                  transaction_buyer=transaction_buyer,
                                                  transaction_salesman=transaction_seller
                                                  )
    sale_user_card.save()
    card.owner = buyer_profile.user
    card.price = 0
    card.sale_status = False
    card.save()

    amulet = AmuletItem.objects.filter(card=card).last()
    if amulet:
        amulet.card = None
        amulet.save()

    if card == seller_profile.current_card:
        seller_profile.current_card = None
        seller_profile.save()

    answer['success_message'] = 'Вы успешно совершили покупку!'
    return answer


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


@transaction.atomic
def merge_user_card(current_card_id: int, card_for_merge_id: int, user_id: int) -> dict:
    """ Слияние карты.
        Повышает уровень слияния выбранной карты.
        Уничтожает карту, которую слили, перед этим сняв амулет.
        Избранную карту и карты, участвующие в боевом событии, слить нельзя.
        Возвращает сообщение об успехе или ошибке.
    """

    answer_data = {}
    if current_card_id == card_for_merge_id:
        answer_data['error_message'] = 'Вы не можете слить одну и ту же карту!'
        return answer_data

    current_card = get_object_or_404(Card, pk=current_card_id)
    card_for_merge = get_object_or_404(Card, pk=card_for_merge_id)
    team_card_pks = BattleEventParticipants.objects.filter(user=user_id).values_list('first_card__pk',
                                                                                     'second_card__pk',
                                                                                     'third_card__pk').last()
    if card_for_merge_id in team_card_pks:
        answer_data['error_message'] = 'Вы не можете слить эти карты! Карта в отряде боевого события'
        return answer_data

    if current_card.owner.id != user_id or card_for_merge.owner.id != user_id:
        answer_data['error_message'] = 'Вы не являетесь владельцем необходимой карты!'
        return answer_data

    if current_card.merger >= current_card.max_merger:
        answer_data['error_message'] = 'У этой карты уже максимальный уровень слияния!'
        return answer_data

    if current_card.class_card != card_for_merge.class_card or \
            current_card.type != card_for_merge.type or \
            current_card.rarity != card_for_merge.rarity:
        answer_data['error_message'] = 'Вы не можете делать слияния с разными картами!'
        return answer_data

    current_card.merge()
    card_for_merge.delete()
    answer_data['success_message'] = 'Вы успешно выполнили слияние!'
    return answer_data
