from random import randint, choice

from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.http import HttpResponseRedirect, HttpResponse, HttpRequest
from django.shortcuts import render, get_object_or_404
from django.urls import reverse

from cards.models import Card, HistoryReceivingCards, ClassCard, Type, Rarity
from common.decorators import auth_required, owner_required
from common.utils import date_time_now, create_new_card
from prompt_toolkit.formatted_text.ansi import ansi_escape
from users.models import Transactions, Profile

from .forms import BuyItemForm
from .models import ExperienceItems, UsersInventory, AmuletItem, AmuletType, UpgradeItemsType, UpgradeItemsUsers


@transaction.atomic
def purchase_amulet(user_id: int, amulet_id: int) -> dict:
    """ Процесс покупки амулета из магазина.
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

    bought_amulet.save()
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

    profile_user.gold = new_record_transaction.after
    new_record_transaction.save()
    profile_user.save()
    answer_data['success_message'] = 'Вы успешно совершили покупку!'
    return answer_data


@transaction.atomic
def set_amulet_on_card(user_id: int, card_id: int, amulet_id: int) -> dict:
    """ Устанавливает выбранный амулет на выбранную карту.
        Если у карты был установлен амулет, то отвязывает текущий """

    answer_data = {}
    current_amulet = get_object_or_404(AmuletItem, pk=amulet_id)
    card = get_object_or_404(Card, pk=card_id)
    if current_amulet.owner.id != user_id or card.owner.id != user_id:
        answer_data['error_message'] = 'Вы не можете поменять у карты амулет!'
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
        Книги, полученные из сундука выводятся пользователю
    """

    # answer_data = {}
    # profile_user = Profile.objects.get(user=user_id)
    # if profile_user.gold < 1600:
    #     answer_data['error_message'] = 'Вам не хватает денег!'
    #     return answer_data
    #
    # all_items = ExperienceItems.objects.all().order_by('rarity')
    #
    # # Всегда как минимум 1 книга будет UR
    # items_reward_for_view = [all_items[2]]
    # count_ur_books = 1
    # count_sr_books = 0
    # count_r_books = 0
    #
    # for _ in range(9):
    #     chance = randint(1, 100)
    #     if chance <= all_items[0].chance_drop_on_box:
    #         items_reward_for_view.append(all_items[0])
    #         count_r_books += 1
    #     elif all_items[0].chance_drop_on_box <= (all_items[0].chance_drop_on_box + all_items[1].chance_drop_on_box):
    #         items_reward_for_view.append(all_items[1])
    #         count_sr_books += 1
    #     else:
    #         items_reward_for_view.append(all_items[2])
    #         count_ur_books += 1
    #
    # r_items_user, _ = UsersInventory.objects.get_or_create(owner=request.user, item=all_items[0])
    # sr_items_user, _ = UsersInventory.objects.get_or_create(owner=request.user, item=all_items[1])
    # ur_items_user, _ = UsersInventory.objects.get_or_create(owner=request.user, item=all_items[2])
    #
    # r_items_user.amount += count_r_books
    # sr_items_user.amount += count_sr_books
    # ur_items_user.amount += count_ur_books
    # for_transaction = [r_items_user, sr_items_user, ur_items_user]
    #
    # with transaction.atomic():
    #     UsersInventory.objects.bulk_update(for_transaction, ['amount'])
    #
    # new_transaction = Transactions.objects.create(date_and_time=date_time_now(),
    #                                               user=request.user,
    #                                               before=profile_user.gold,
    #                                               after=profile_user.gold - 1600,
    #                                               comment='Покупка в магазине предметов'
    #                                               )
    # new_transaction.save()
    # profile_user.gold -= 1600
    # profile_user.save()
    #
    # context = {'books': sorted(items_reward_for_view, key=lambda item: item.rarity, reverse=True)}
    pass
