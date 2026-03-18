from logging import getLogger
from random import choice, randint

from django.db import transaction
from django.shortcuts import get_object_or_404

from cards.models import Card, HistoryReceivingCards, Type, Rarity
from common.utils import date_time_now, create_new_card
from users.models import Transactions, Profile

from .models import (ExperienceItems, UsersInventory, AmuletItem, AmuletType,
                     UpgradeItemsType, UpgradeItemsUsers, HistoryPurchaseItems)

logger = getLogger(__name__)


@transaction.atomic
def buy_amulet_service(user_id: int, amulet_id: int) -> dict:
    """ Покупка амулета из магазина.
        Создает амулет на основе амулета из магазина и присваивает его покупателю в таблице AmuletItem.
        Создает запись в Transactions.
        Изменяет gold в Profile текущего пользователя.
        Возвращает сообщение об успехе или ошибке.
    """

    answer_data = {}
    current_amulet = get_object_or_404(AmuletType, pk=amulet_id)
    profile_user = Profile.objects.get(user=user_id)

    if profile_user.amulet_slots <= AmuletItem.objects.filter(owner=user_id).count():
        answer_data['error_message'] = 'У вас не хватает места для покупки амулета!'
        return answer_data

    if current_amulet.discount_now:
        if profile_user.gold < current_amulet.price * (100 - current_amulet.discount) / 100:
            answer_data['error_message'] = 'Для покупки вам не хватает денег!'
            return answer_data
    else:
        if profile_user.gold < current_amulet.price:
            answer_data['error_message'] = 'Для покупки вам не хватает денег!'
            return answer_data

    bought_amulet = AmuletItem.objects.create(amulet_type=current_amulet,
                                              owner=profile_user.user)
    logger.info(f'Создан амулет ID {bought_amulet.id}')

    if current_amulet.discount_now:
        new_record_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                             user=profile_user.user,
                                                             before=profile_user.gold,
                                                             after=profile_user.gold - current_amulet.price * (
                                                                         100 - current_amulet.discount) / 100,
                                                             comment='Покупка в магазине предметов')
    else:
        new_record_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                             user=profile_user.user,
                                                             before=profile_user.gold,
                                                             after=profile_user.gold - current_amulet.price,
                                                             comment='Покупка в магазине предметов')
    logger.info(f'Создана транзакция пользователя ID {profile_user.user.id}: ID {new_record_transaction.id}')

    profile_user.gold = new_record_transaction.after
    profile_user.save()
    logger.info(f'Пользователь ID {profile_user.user.id} потратил деньги на покупку амулета в магазине')
    answer_data['success_message'] = 'Вы успешно совершили покупку!'
    return answer_data


@transaction.atomic
def change_amulet_service(user_id: int, card_id: int, amulet_id: int) -> dict:
    """ Устанавливает выбранный амулет на выбранную карту.
        Если у карты был установлен амулет, то отвязывает текущий.
        Возвращает сообщение об успехе или ошибке.
    """

    answer_data = {}
    current_amulet = get_object_or_404(AmuletItem, pk=amulet_id)
    card = get_object_or_404(Card, pk=card_id)

    if current_amulet.owner.id != user_id:
        answer_data['error_message'] = 'Вы не можете использовать чужой амулет!'
        return answer_data

    if card.owner.id != user_id:
        answer_data['error_message'] = 'Вы не можете поменять амулет у чужой карты!'
        return answer_data

    another_amulet_in_card = AmuletItem.objects.filter(card=card).last()
    if another_amulet_in_card:
        another_amulet_in_card.card = None
        another_amulet_in_card.save()

    current_amulet.card = card
    current_amulet.save()

    answer_data['success_message'] = 'Вы успешно надели амулет!'
    return answer_data


@transaction.atomic()
def open_box_amulet(user_id: int) -> dict:
    """ Покупка и открытие пользователем сундука с амулетами стоимостью 15 000.
        Проверяет возможность покупки.
        Случайно выбирает 5 амулетов и помещает в инвентарь пользователя.
        У пользователя снимаются деньги.
        Создается запись в Transaction.
        Возвращает список полученных амулетов или сообщение об ошибке """

    answer_data = {}
    profile_user = Profile.objects.get(user=user_id)

    if profile_user.amulet_slots - 5 <= AmuletItem.objects.filter(owner=user_id).count():
        answer_data['error_message'] = 'У вас не хватает места для покупки амулета!'
        return answer_data

    if profile_user.gold < 15000:
        answer_data['error_message'] = 'Вам не хватает денег!'
        return answer_data

    amulets_ur = AmuletType.objects.filter(rarity__name='UR')
    amulets_ur_count = len(amulets_ur)

    amulets_sr = AmuletType.objects.filter(rarity__name='SR')
    amulets_sr_count = len(amulets_sr)

    amulets_r = AmuletType.objects.filter(rarity__name='R')
    amulets_r_count = len(amulets_r)

    amulet_reward = []
    for _ in range(5):
        chance = randint(1, 100)
        # Если выпал R
        if chance <= amulets_r[1].rarity.chance_drop_on_box:
            random_amulet = randint(0, amulets_r_count-1)
            new_amulet = AmuletItem.objects.create(amulet_type=amulets_r[random_amulet],
                                                   owner=profile_user.user)
            amulet_reward.append(amulets_r[random_amulet])
            new_amulet.save()

        # Если выпал SR
        elif chance <= (amulets_sr[1].rarity.chance_drop_on_box + amulets_r[1].rarity.chance_drop_on_box):
            random_amulet = randint(0, amulets_sr_count-1)
            new_amulet = AmuletItem.objects.create(amulet_type=amulets_sr[random_amulet],
                                                   owner=profile_user.user)
            amulet_reward.append(amulets_sr[random_amulet])
            new_amulet.save()

        # Если выпал UR
        else:
            random_amulet = randint(0, amulets_ur_count-1)
            new_amulet = AmuletItem.objects.create(amulet_type=amulets_ur[random_amulet],
                                                   owner=profile_user.user)
            amulet_reward.append(amulets_ur[random_amulet])
            new_amulet.save()

    new_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                  user=profile_user.user,
                                                  before=profile_user.gold,
                                                  after=profile_user.gold - 15000,
                                                  comment='Покупка в магазине предметов'
                                                  )
    new_transaction.save()
    profile_user.gold -= 15000
    profile_user.save()
    answer_data['new_amulets'] = sorted(amulet_reward, key=lambda item: item.rarity.id, reverse=True)

    return answer_data


@transaction.atomic()
def open_box_book(user_id: int) -> dict:
    """ Покупка и открытие пользователем сундука с книгами опыта стоимостью 1 600.
        Случайно генерирует 9 книг и создает 1 книгу UR редкости.
        У пользователя снимаются деньги.
        Создается запись в Transaction.
        Возвращает книги, полученные из сундука выводятся пользователю
        или сообщение об ошибке.
    """

    answer_data = {}
    profile_user = Profile.objects.get(user=user_id)
    if profile_user.gold < 1600:
        answer_data['error_message'] = 'Вам не хватает денег!'
        return answer_data

    all_items = ExperienceItems.objects.all().order_by('rarity')

    # Всегда как минимум 1 книга будет UR
    items_reward_for_view = [all_items[2]]
    count_ur_books = 1
    count_sr_books = 0
    count_r_books = 0

    for _ in range(9):
        chance = randint(1, 100)
        if chance <= all_items[0].chance_drop_on_box:
            items_reward_for_view.append(all_items[0])
            count_r_books += 1
        elif all_items[0].chance_drop_on_box <= (all_items[0].chance_drop_on_box + all_items[1].chance_drop_on_box):
            items_reward_for_view.append(all_items[1])
            count_sr_books += 1
        else:
            items_reward_for_view.append(all_items[2])
            count_ur_books += 1

    r_items_user, _ = UsersInventory.objects.get_or_create(owner=profile_user.user, item=all_items[0])
    sr_items_user, _ = UsersInventory.objects.get_or_create(owner=profile_user.user, item=all_items[1])
    ur_items_user, _ = UsersInventory.objects.get_or_create(owner=profile_user.user, item=all_items[2])

    r_items_user.amount += count_r_books
    sr_items_user.amount += count_sr_books
    ur_items_user.amount += count_ur_books

    r_items_user.save()
    sr_items_user.save()
    ur_items_user.save()

    new_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                  user=profile_user.user,
                                                  before=profile_user.gold,
                                                  after=profile_user.gold - 1600,
                                                  comment='Покупка в магазине предметов'
                                                  )
    new_transaction.save()
    profile_user.gold -= 1600
    profile_user.save()

    answer_data['books'] = sorted(items_reward_for_view, key=lambda item: item.rarity, reverse=True)
    return answer_data


@transaction.atomic
def open_box_card(user_id: int) -> dict:
    """ Покупка и открытие пользователем сундука с UR картой стоимостью 20 000.
        Создает карту UR редкости с максимальным значение начального здоровья или урона.
        У пользователя снимаются деньги.
        Создается запись в Transaction.
        Создается новая запись в HistoryReceivingCards.
        Возвращает сообщение об успехе или ошибке.
    """

    profile_user = Profile.objects.get(user=user_id)
    answer_data = {}

    if profile_user.card_slots <= Card.objects.filter(owner=profile_user.user.id).count():
        answer_data['error_message'] = 'У вас не хватает места для получения новой карты!'
        return answer_data

    if profile_user.gold < 20000:
        answer_data['error_message'] = 'Вам не хватает денег!'
        return answer_data

    attributes = ('damage', 'hp')
    max_attribute = choice(attributes)
    new_card = create_new_card(user_id=profile_user.user.id,
                               ur_box=True,
                               max_attribute=max_attribute)

    new_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                  user=profile_user.user,
                                                  before=profile_user.gold,
                                                  after=profile_user.gold - 20000,
                                                  comment='Покупка в магазине предметов'
                                                  )
    new_transaction.save()
    profile_user.gold -= 20000
    profile_user.save()

    new_history_receiving_cards = HistoryReceivingCards.objects.create(card=new_card,
                                                                       date_and_time=date_time_now(),
                                                                       user=profile_user.user,
                                                                       method_receiving='Покупка сундука'
                                                                       )
    new_history_receiving_cards.save()
    answer_data['new_card_id'] = new_card.id

    return answer_data


@transaction.atomic
def buy_upgrade_item_service(user_id: int, upgrade_item_id: int) -> dict:
    """ Покупка предмета усиления в магазине.
        Добавляет или создает предмет усиления в инвентаре пользователя в таблице UpgradeItemsUsers.
        Создает запись в Transactions.
        У пользователя снимаются деньги.
        Возвращает сообщение об успехе или ошибке.
    """

    profile_user = Profile.objects.get(user=user_id)
    current_upgrade_item = get_object_or_404(UpgradeItemsType, pk=upgrade_item_id)
    answer_data = {}

    if profile_user.gold < current_upgrade_item.price:
        answer_data['error_message'] = 'Для покупки вам не хватает денег!'
        return answer_data

    upgrade_item = UpgradeItemsType.objects.get(id=upgrade_item_id)

    new_upgrade_item_user, _ = UpgradeItemsUsers.objects.get_or_create(owner=profile_user.user,
                                                                       upgrade_item_type=upgrade_item)
    new_upgrade_item_user.amount += 1
    new_upgrade_item_user.save()

    new_record_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                         user=profile_user.user,
                                                         before=profile_user.gold,
                                                         after=profile_user.gold - upgrade_item.price,
                                                         comment='Покупка в магазине предметов')

    profile_user.gold = new_record_transaction.after
    new_record_transaction.save()
    profile_user.save()

    answer_data['success_message'] = 'Вы успешно совершили покупку!'
    return answer_data


@transaction.atomic
def enhance_card_service(user_id: int, card_id: int, up_item_id: int) -> dict:
    """ Улучшение характеристик карты в зависимости от выбранного предмета.
        Удаляет выбранный предмет из инвентаря пользователя UpgradeItemsUsers.
        Создает запись в Transactions.
        У пользователя снимаются деньги.
        Возвращает сообщение об успехе или ошибке и url_name для перенаправления при необходимости.
    """

    current_card = get_object_or_404(Card, pk=card_id)
    profile_user = Profile.objects.get(user=user_id)
    answer_data = {}

    if current_card.owner.id != user_id:
        answer_data['error_message'] = 'Вы не являетесь владельцем этой карты!'
        answer_data['url_name_redirect'] = 'home'
        return answer_data

    current_up_item = UpgradeItemsUsers.objects.filter(owner=user_id,
                                                       upgrade_item_type=up_item_id).last()

    # Ленивое условие
    if current_up_item is None or current_up_item.amount <= 0:
        answer_data['error_message'] = 'У вас недостаточно предметов усиления!'
        return answer_data

    if profile_user.gold < current_up_item.upgrade_item_type.price_of_use:
        answer_data['error_message'] = 'У вас недостаточно денег!'
        return answer_data

    if current_card.enhancement >= current_card.max_enhancement:
        answer_data['error_message'] = 'Эта карта имеет максимальный уровень усиления!'
        answer_data['url_name_redirect'] = 'home'
        return answer_data

    if current_up_item.upgrade_item_type.type == 'hp':
        current_card.enhance_hp()
    elif current_up_item.upgrade_item_type.type == 'attack':
        current_card.enhance_attack()
    elif current_up_item.upgrade_item_type.type == 'random':
        current_card.enhance_random()

    current_up_item.amount -= 1
    new_record_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                         user=profile_user.user,
                                                         before=profile_user.gold,
                                                         after=profile_user.gold - current_up_item.upgrade_item_type.price_of_use,
                                                         comment='Усиление карты')

    profile_user.gold = new_record_transaction.after
    new_record_transaction.save()
    profile_user.save()
    current_up_item.save()

    answer_data['success_message'] = 'Вы улучшили карту!'
    return answer_data


@transaction.atomic()
def buy_item_service(user_id: int, item_id: int, amount: int) -> dict:
    """ Покупка книги опыта.
        Создает запись в Transactions.
        Создает запись в истории покупок предметов HistoryPurchaseItems.
        Выбранный товар начисляется в инвентарь (или обновляется его количество).
        Изменяет gold в Profile текущего пользователя.
        Возвращает сообщение об успехе или ошибке.
    """

    item = get_object_or_404(ExperienceItems, pk=item_id)
    profile = Profile.objects.get(user=user_id)
    answer_data = {}
    if profile.gold < item.price * amount:
        answer_data['error_message'] = 'Для покупки вам не хватает денег!'
        return answer_data

    profile_gold_after = profile.gold - item.price * amount
    new_record_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                         user=profile.user,
                                                         before=profile.gold,
                                                         after=profile_gold_after,
                                                         comment='Покупка в магазине предметов'
                                                         )
    new_record_history = HistoryPurchaseItems.objects.create(date_and_time=date_time_now(),
                                                             user=profile.user,
                                                             item=item,
                                                             amount=amount,
                                                             transaction=new_record_transaction)

    profile.gold = profile_gold_after
    profile.save()

    items_user, _ = UsersInventory.objects.get_or_create(owner=profile.user, item=item)
    items_user.amount += amount
    items_user.save()

    new_record_history.save()
    answer_data['success_message'] = 'Вы успешно совершили покупку!'
    return answer_data


def remove_service(user_id: int, amulet_id: int, card_id: int) -> dict:
    """ Снятие амулета с карты.
        Если амулета не существует, возвращает 404.
        Если пользователь не владелец амулета или амулет не на выбранной карте, ошибка.
        Если проверки прошли, снимает амулет.
        Возвращает сообщение об успехе или ошибке
    """

    answer_data = {}
    current_amulet = get_object_or_404(AmuletItem, pk=amulet_id)

    if current_amulet.owner.id != user_id:
        answer_data['error_message'] = 'Вы не можете пользоваться чужим амулетом'

    elif current_amulet.card.id != card_id:
        answer_data['error_message'] = 'Этот амулет не надет на выбранную карту!'

    else:
        current_amulet.card = None
        current_amulet.save()

        answer_data['success_message'] = 'Вы успешно сняли амулет!'

    return answer_data


@transaction.atomic()
def sale_amulet_service(user_id: int, amulet_id: int) -> dict:
    """ Продажа пользователем амулета внутриигровому магазину.
        Амулет удаляется из инвентаря и запись о нем так же удаляется.
        Пользователь получает деньги за продажу.
        Создается запись в Transactions.
        Возвращает сообщение об успехе или ошибке.
    """

    answer_data = {}
    amulet = get_object_or_404(AmuletItem, pk=amulet_id)
    profile = Profile.objects.get(user=user_id)
    if amulet.owner.id != user_id:
        answer_data['error_message'] = 'Вы не можете пользоваться чужим амулетом!'
        return answer_data

    new_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                  user=profile.user,
                                                  before=profile.gold,
                                                  after=profile.gold + round(amulet.amulet_type.price, 2),
                                                  comment='Продажа амулета')
    profile.gold += round(amulet.amulet_type.price, 2)
    amulet.delete()
    profile.save()
    new_transaction.save()
    answer_data['success_message'] = f'Вы успешно продали амулет за {round(amulet.amulet_type.price, 2)}!'
    return answer_data

