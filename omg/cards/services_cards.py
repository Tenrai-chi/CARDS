from math import ceil

from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import Card, CardStore, HistoryReceivingCards
from .utils import accrue_experience

from common.utils import time_difference_check, create_new_card, date_time_now
from exchange.models import (SaleUserCards, UsersInventory, AmuletItem, BattleEventParticipants)
from users.models import Transactions, Profile, SaleStoreCards


def get_cards_with_pagination(page_num: int = 1, item_per_page: int = 21) -> dict:
    """ Возвращает список всех карт с учетом пагинации """

    cards = Card.objects.all().order_by('-pk')
    paginator = Paginator(cards, item_per_page)
    page = paginator.get_page(page_num)
    answer_data = {'cards': page.object_list,
                   'page': page
                   }

    return answer_data


@transaction.atomic
def create_free_card(user_id: int) -> dict:
    """ Генерация новой карты пользователя при бесплатном получении.
        Если возникла ошибка, то возвращает сообщение об ошибке и имя для перенаправления
    """

    answer_data = {}
    user = User.objects.get(pk=user_id)
    user_profile = Profile.objects.get(user=user)
    if Card.objects.filter(owner=user_id).count() == user_profile.card_slots:
        answer_data['error'] = True
        answer_data['error_message'] = 'У вас не хватает места для получения новой карты!'
        answer_data['return_name'] = 'card_store'
        return answer_data

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
        answer_data['new_card_id'] = new_card.id

    else:
        answer_data['error'] = True
        answer_data['error_message'] = 'Вы пока не можете получить бесплатную карту'
        answer_data['return_name'] = 'home'
    return answer_data


@transaction.atomic
def buy_card_service(user_id: int, card_id: int) -> dict:
    """ Процесс покупки карты.
        Создает карту по шаблону выбранной карты в магазине и присваивает ее текущему пользователю.
        У пользователя в Profile изменяется gold на значение равное цене карты.
        При ошибке возвращает сообщение об ошибке.
    """

    answer_data = {}
    user = User.objects.get(pk=user_id)
    user_profile = Profile.objects.get(user=user)
    selected_card = CardStore.objects.get(pk=card_id)

    if user_profile.gold < selected_card.price:
        answer_data['error_message'] = 'У вас не хватает средств для покупки!'
        return answer_data

    if Card.objects.filter(owner=user).count() >= user_profile.card_slots:
        answer_data['error_message'] = 'У вас не хватает места для покупки новой карты!'
        return answer_data

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
    answer_data['new_card_id'] = new_card.id

    return answer_data


@transaction.atomic
def transfer_card_to_user(card_id: int, buyer_id: int) -> dict:
    """ Покупка карты у пользователя на торговой площадке.
        Проверяет возможна ли покупка. Если нет, то возвращает сообщение об ошибке.
        Изменяет значения gold у обоих пользователей.
        Создает 2 записи в Transaction для продажи и покупки.
        Возвращает сообщение об успехе или ошибке.
    """

    buyer_profile = Profile.objects.get(user=buyer_id)
    card = get_object_or_404(Card, pk=card_id)
    seller_profile = Profile.objects.get(user=card.owner.id)
    answer_data = {}

    if not card.sale_status:
        answer_data['error_message'] = 'Эта карта не продается!'
        return answer_data

    if buyer_profile.card_slots <= Card.objects.filter(owner=buyer_id).count():
        answer_data['error_message'] = 'У вас не хватает места для покупки новой карты!'
        return answer_data

    if buyer_profile.gold < card.price:
        answer_data['error_message'] = 'У вас не хватает средств для покупки!'
        return answer_data

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

    answer_data['success_message'] = 'Вы успешно совершили покупку!'
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


def card_sale_service(user_id: int, card_id: int, price: int) -> dict:
    """ Выставление на продажу карты.
        Устанавливает sale_status на True.
        Устанавливает указанную цену.
        Возвращает сообщение об успехе или ошибке.
    """

    answer_data = {}
    card = get_object_or_404(Card, pk=card_id)
    if card.owner.id != user_id:
        answer_data['error_message'] = 'Вы не можете выставить на продажу чужую карту!'
        return answer_data

    team_card_pks = BattleEventParticipants.objects.filter(user=user_id).values_list('first_card__pk',
                                                                                     'second_card__pk',
                                                                                     'third_card__pk').last()

    if card_id in team_card_pks:
        answer_data['error_message'] = 'Вы не можете выставить на продажу эту карту! Карта в отряде боевого события'
        return answer_data

    card.sale_status = True
    card.price = price
    card.save()
    answer_data['success_message'] = 'Карта успешно выставлена на торговую площадку!'
    return answer_data


@transaction.atomic
def level_up_with_item_service(user_id: int, card_id: int, item_id: int, amount_item: int) -> dict:
    """ Увеличение уровня с помощью книг опыта.
        Если у пользователя хватает денег для использования предметов,
        то увеличивает опыт карты, и изменяет ее уровень, если необходимо.
        Использует только необходимое количество книг опыта.
        В Profile пользователя уменьшается gold.
        Создается транзакция.
        Возвращает сообщение об успехе или ошибке.
    """

    answer_data = {}
    card = get_object_or_404(Card, pk=card_id)
    item = get_object_or_404(UsersInventory, pk=item_id)

    if user_id != card.owner.id:
        answer_data['error_message'] = 'Вы не можете улучшать чужую карту!'
        answer_data['show_form'] = False
        return answer_data

    if card.level >= card.rarity.max_level:
        answer_data['error_message'] = 'Эта карта имеет максимальный уровень!'
        answer_data['show_form'] = False
        return answer_data

    profile = Profile.objects.get(user=user_id)

    if item.amount < amount_item:
        answer_data['error_message'] = 'У вас нет столько предметов!'
        answer_data['show_form'] = True
        return answer_data

    if profile.gold < amount_item * item.item.gold_for_use:
        answer_data['error_message'] = 'Вам не хватает денег!'
        answer_data['show_form'] = True
        return answer_data

    accrued_experience = amount_item * item.item.experience_amount
    if profile.guild.buff.name == 'Пытливый ум':
        accrued_experience = round(accrued_experience * profile.guild.buff.numeric_value / 100)

    answer = accrue_experience(accrued_experience=accrued_experience,
                               current_level=card.level,
                               max_level=card.rarity.max_level,
                               current_exp=card.experience_bar)

    card.experience_bar = answer[0]
    expended_experience = answer[2]

    new_levels = answer[1] - card.level
    card.increase_stats(new_levels)
    card.level = answer[1]

    # Проверка на бафф гильдии
    if profile.guild.buff.name == 'Пытливый ум':
        expended_items = ceil((expended_experience / item.item.experience_amount) * 0.8)
    else:
        expended_items = ceil(expended_experience / item.item.experience_amount)

    new_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                  user=profile.user,
                                                  before=profile.gold,
                                                  after=profile.gold - expended_items * item.item.gold_for_use,
                                                  comment='Улучшение карты'
                                                  )
    new_transaction.save()
    profile.gold -= expended_items * item.item.gold_for_use
    item.amount -= expended_items

    profile.save()
    item.save()
    card.save()

    answer_data['success_message'] = 'Ваша карта успешно получила опыт'
    return answer_data


def remove_from_sale_card_service(user_id: int, card_id: int) -> dict:
    """ Удаление карты из торговой площадки.
        Устанавливает sale_status на False, а price на None.
        Возвращает сообщение об успехе или ошибке.
    """

    answer_data = {}
    card = get_object_or_404(Card, pk=card_id)
    if card.owner.id != user_id:
        answer_data['error_message'] = 'Вы не являетесь владельцем этой карты!'
        return answer_data

    if card.sale_status is False:
        answer_data['error_message'] = 'В данный момент вы не продаете эту карту и не можете убрать ее из продажи'
        return answer_data

    card.sale_status = False
    card.price = None
    card.save()

    answer_data['success_message'] = 'Вы успешно убрали карту с продажи'
    return answer_data

