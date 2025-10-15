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
from users.models import Transactions, Profile

from .forms import BuyItemForm
from .models import ExperienceItems, UsersInventory, AmuletItem, AmuletType, UpgradeItemsType, UpgradeItemsUsers


@auth_required()
@owner_required(error_message='Просмотр инвентаря этого пользователя невозможен')
def view_inventory_user(request: HttpRequest, user_id: int,
                        inventory_filter: str = 'all') -> HttpResponseRedirect | HttpResponse:
    """ Просмотр инвентаря пользователя.
        Доступно только если текущий пользователь является владельцем инвентаря.
     """

    context = {'title': 'Инвентарь',
               'header': f'Инвентарь {request.user.username}',
               'user_items': None,
               'user_amulets': None,
               'count_amulets': None,
               'max_count_amulets': None,
               'upgrade_items': None,
               }

    if inventory_filter == 'all':
        context['max_count_amulets'] = Profile.objects.get(pk=user_id).amulet_slots
        context['count_amulets'] = AmuletItem.objects.filter(owner=request.user).count()
        context['user_items'] = UsersInventory.objects.filter(owner=request.user).order_by('id')
        context['user_amulets'] = AmuletItem.objects.filter(owner=request.user).order_by('id')
        context['upgrade_items'] = UpgradeItemsUsers.objects.filter(owner=request.user).order_by('id')

    elif inventory_filter == 'amulets':
        context['max_count_amulets'] = Profile.objects.get(pk=user_id).amulet_slots
        context['count_amulets'] = AmuletItem.objects.filter(owner=request.user).count()
        context['user_amulets'] = AmuletItem.objects.filter(owner=request.user).order_by('id')

    elif inventory_filter == 'upgrade_items':
        context['max_count_amulets'] = Profile.objects.get(pk=user_id).amulet_slots
        context['count_amulets'] = AmuletItem.objects.filter(owner=request.user).count()
        context['upgrade_items'] = UpgradeItemsUsers.objects.filter(owner=request.user).order_by('id')

    elif inventory_filter == 'books_exp':
        context['max_count_amulets'] = Profile.objects.get(pk=user_id).amulet_slots
        context['count_amulets'] = AmuletItem.objects.filter(owner=request.user).count()
        context['user_items'] = UsersInventory.objects.filter(owner=request.user).order_by('id')

    return render(request, 'exchange/view_user_inventory.html', context)


def item_store(request: HttpRequest, store_filter: str = 'all') -> HttpResponse:
    """ Вывод ассортимента магазина предметов """

    items_on_sale = None
    amulets_on_sale = None
    is_box = None
    upgrade_items = None

    if store_filter == 'all':
        items_on_sale = ExperienceItems.objects.filter(sale_now=True).order_by('experience_amount')
        amulets_on_sale = AmuletType.objects.filter(sale_now=True).annotate(new_price=F('price') * (100 - F('discount')) / 100)
        is_box = True
        upgrade_items = UpgradeItemsType.objects.all()

    elif store_filter == 'box':
        is_box = True

    elif store_filter == 'amulets':
        amulets_on_sale = AmuletType.objects.filter(sale_now=True).annotate(new_price=F('price') * (100 - F('discount')) / 100)

    elif store_filter == 'upgrade_items':
        upgrade_items = UpgradeItemsType.objects.all()

    elif store_filter == 'books_exp':
        items_on_sale = ExperienceItems.objects.filter(sale_now=True).order_by('experience_amount')

    context = {'title': 'Магазин предметов',
               'header': 'Магазин предметов',
               'items': items_on_sale,
               'amulets': amulets_on_sale,
               'is_box': is_box,
               'upgrade_items': upgrade_items
               }

    return render(request, 'exchange/items_store.html', context)


@auth_required(error_message='Для покупки необходимо авторизоваться!', redirect_url_name='items_store')
def buy_amulet(request: HttpRequest, amulet_id: int) -> HttpResponseRedirect:
    """ Покупка амулета.
        Создает амулет на основе амулета из магазина и присваивает его покупателю в таблице AmuletItem.
        Создает запись в Transactions.
        Изменяет gold в Profile текущего пользователя.
    """

    profile_user = Profile.objects.get(user=request.user)
    current_amulet = get_object_or_404(AmuletType, pk=amulet_id)

    if request.user.profile.amulet_slots <= AmuletItem.objects.filter(owner=request.user.id).count():
        messages.error(request, 'У вас не хватает места для покупки амулета!')

        return HttpResponseRedirect(reverse('items_store'))

    if current_amulet.discount_now:
        if profile_user.gold < current_amulet.price * (100 - current_amulet.discount) / 100:
            messages.error(request, 'Для покупки вам не хватает денег!')

            return HttpResponseRedirect(reverse('items_store'))
    else:
        if profile_user.gold < current_amulet.price:
            messages.error(request, 'Для покупки вам не хватает денег!')

            return HttpResponseRedirect(reverse('items_store'))

    bought_amulet = AmuletItem.objects.create(amulet_type=current_amulet,
                                              owner=request.user)

    bought_amulet.save()
    if current_amulet.discount_now:
        new_record_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                             user=request.user,
                                                             before=profile_user.gold,
                                                             after=profile_user.gold - current_amulet.price * (100 - current_amulet.discount) / 100,
                                                             comment='Покупка в магазине предметов')
    else:
        new_record_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                             user=request.user,
                                                             before=profile_user.gold,
                                                             after=profile_user.gold - current_amulet.price,
                                                             comment='Покупка в магазине предметов')

    profile_user.gold = new_record_transaction.after
    new_record_transaction.save()
    profile_user.save()
    messages.success(request, 'Вы успешно совершили покупку!')

    return HttpResponseRedirect(reverse('items_store', kwargs={'store_filter': 'amulets'}))


@auth_required()
def buy_item(request: HttpRequest, item_id: int) -> HttpResponseRedirect | HttpResponse:
    """ Покупка книги опыта.
        Создает запись в Transactions.
        Создает запись в истории покупок предметов HistoryPurchaseItems.
        Выбранный товар начисляется в инвентарь (или обновляется его количество).
        Изменяет gold в Profile текущего пользователя.
    """

    if request.method == 'POST':
        form = BuyItemForm(request.POST)
        item = get_object_or_404(ExperienceItems,
                                 pk=item_id)
        if form.is_valid():
            profile = Profile.objects.get(user=request.user)
            new_record_history = form.save(commit=False)
            if profile.gold < item.price * new_record_history.amount:
                messages.error(request, 'Вам не хватает денег!')
                context = {'form': form,
                           'title': 'Покупка предмета',
                           'header': f'Покупка предмета "{item.name}"',
                           'item': item
                           }

                return render(request, 'exchange/buy_item.html', context)

            new_record_history.date_and_time = date_time_now()
            new_record_history.user = request.user
            new_record_history.item = item

            profile_gold_after = profile.gold-item.price*new_record_history.amount
            new_record_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                                 user=request.user,
                                                                 before=profile.gold,
                                                                 after=profile_gold_after,
                                                                 comment='Покупка в магазине предметов'
                                                                 )
            new_record_history.transaction = new_record_transaction
            profile.gold = profile_gold_after
            profile.save()
            # Увеличить количество предмета у данного пользователя, если записи нет, то создать
            try:
                items_user = UsersInventory.objects.get(owner=request.user,
                                                        item=item
                                                        )
                items_user.amount += new_record_history.amount
                items_user.save()
            except UsersInventory.DoesNotExist:
                new_record_inventory = UsersInventory.objects.create(owner=request.user,
                                                                     item=item,
                                                                     amount=new_record_history.amount
                                                                     )
                new_record_inventory.save()
            new_record_history.save()
            messages.success(request, 'Вы успешно совершили покупку!')

            return HttpResponseRedirect(reverse('items_store', kwargs={'store_filter': 'books_exp'}))
        else:
            context = {'form': form,
                       'title': 'Покупка предмета',
                       'header': f'Покупка предмета "{item.name}"',
                       'item': item
                       }

            messages.error(request, 'Какая-то ошибка!')

            return render(request, 'exchange/buy_item.html', context)

    else:
        form = BuyItemForm(initial={'amount': 1})
        item = get_object_or_404(ExperienceItems, pk=item_id)
        context = {'title': 'Покупка предмета',
                   'header': f'Покупка предмета "{item.name}"',
                   'form': form,
                   'item': item
                   }

        return render(request, 'exchange/buy_item.html', context)


@auth_required()
def change_amulet_menu(request: HttpRequest, card_id: int) -> HttpResponse:
    """ Меню смены амулеты у выбранной карты.
        Выводит список доступных амулетов.
    """

    card = get_object_or_404(Card, pk=card_id)
    available_amulets = AmuletItem.objects.filter(owner=request.user)
    context = {'title': 'Выбор амулета',
               'header': 'Выбрать амулет',
               'card': card,
               'amulets': available_amulets}

    return render(request, 'cards/change_amulet_menu.html', context)


@auth_required()
def change_amulet(request: HttpRequest, card_id: int, amulet_id: int) -> HttpResponseRedirect:
    """ Устанавливает выбранный амулет на выбранную карту.
        Если у карты был установлен амулет, то отвязывает его.
    """

    current_amulet = get_object_or_404(AmuletItem, pk=amulet_id)
    card = get_object_or_404(Card, pk=card_id)
    if current_amulet.owner == request.user:
        card_with_current_amulet = AmuletItem.objects.filter(card=card)
        for elem in card_with_current_amulet:
            elem.card = None
            elem.save()
        current_amulet.card = card
        current_amulet.save()

        messages.success(request, 'Вы успешно надели амулет!')
        return HttpResponseRedirect(f'/cards/card-{card_id}')

    else:
        messages.error(request, 'Вы не можете поменять у карты амулет!')
        return HttpResponseRedirect(reverse('home'))


@auth_required()
def remove_amulet(request: HttpRequest, card_id: int, amulet_id: int) -> HttpResponseRedirect:
    """ Удаляет у выбранного амулета карту """

    current_amulet = get_object_or_404(AmuletItem, pk=amulet_id)
    if current_amulet.owner == request.user:
        current_amulet.card = None
        current_amulet.save()

        messages.success(request, 'Вы успешно сняли амулет!')
        return HttpResponseRedirect(f'/cards/card-{card_id}')

    else:
        messages.error(request, 'Вы не можете пользоваться этим амулетом!')
        return HttpResponseRedirect(reverse('home'))


@auth_required()
@owner_required()
def sale_amulet(request: HttpRequest, user_id: int, amulet_id: int) -> HttpResponseRedirect:
    """ Продажа пользователем амулета внутриигровому магазину.
        Амулет удаляется из инвентаря и запись о нем так же удаляется.
        Пользователь получает деньги за продажу.
        Создается запись в Transactions.
    """

    amulet = get_object_or_404(AmuletItem, pk=amulet_id)
    profile = Profile.objects.get(pk=request.user.id)
    if amulet.owner == request.user:
        transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                  user=request.user,
                                                  before=profile.gold,
                                                  after=profile.gold+round(amulet.amulet_type.price),
                                                  comment='Продажа амулета')
        profile.gold += round(amulet.amulet_type.price)
        amulet.delete()
        profile.save()
        transaction.save()
        messages.success(request, 'Вы успешно продали амулет!')

        return HttpResponseRedirect(f'/inventory/{user_id}')
    else:
        messages.error(request, 'Произошла ошибка!')

        return HttpResponseRedirect(reverse('home'))


@auth_required()
def buy_and_open_box_amulet(request: HttpRequest) -> HttpResponseRedirect | HttpResponse:
    """ Покупка и открытие пользователем сундука с амулетами стоимостью 15 000.
        Случайно выбирает 5 амулетов и помещает в инвентарь пользователя.
        У пользователя снимаются деньги.
        Создается запись в Transaction.
        Амулеты, полученные из сундука выводятся пользователю
    """

    profile_user = Profile.objects.get(user=request.user)

    if request.user.profile.amulet_slots - 5 <= AmuletItem.objects.filter(owner=request.user.id).count():
        messages.error(request, 'У вас не хватает места для покупки амулета!')
        return HttpResponseRedirect(reverse('items_store'))

    if profile_user.gold < 15000:
        messages.error(request, 'Вам не хватает денег!')
        return HttpResponseRedirect(reverse('home'))

    amulets_ur = AmuletType.objects.filter(rarity__name='UR')
    amulets_ur_count = AmuletType.objects.filter(rarity__name='UR').count()

    amulets_sr = AmuletType.objects.filter(rarity__name='SR')
    amulets_sr_count = AmuletType.objects.filter(rarity__name='SR').count()

    amulets_r = AmuletType.objects.filter(rarity__name='R')
    amulets_r_count = AmuletType.objects.filter(rarity__name='R').count()

    amulet_reward = []
    for _ in range(5):
        chance = randint(1, 100)
        # Если выпал R
        if chance <= amulets_r[1].rarity.chance_drop_on_box:
            random_amulet = randint(0, amulets_r_count-1)
            new_amulet = AmuletItem.objects.create(amulet_type=amulets_r[random_amulet],
                                                   owner=request.user)
            amulet_reward.append(amulets_r[random_amulet])
            new_amulet.save()

        # Если выпал SR
        elif chance <= (amulets_sr[1].rarity.chance_drop_on_box + amulets_r[1].rarity.chance_drop_on_box):
            random_amulet = randint(0, amulets_sr_count-1)
            new_amulet = AmuletItem.objects.create(amulet_type=amulets_sr[random_amulet],
                                                   owner=request.user)
            amulet_reward.append(amulets_sr[random_amulet])
            new_amulet.save()

        # Если выпал UR
        else:
            random_amulet = randint(0, amulets_ur_count-1)
            new_amulet = AmuletItem.objects.create(amulet_type=amulets_ur[random_amulet],
                                                   owner=request.user)
            amulet_reward.append(amulets_ur[random_amulet])
            new_amulet.save()

    new_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                  user=request.user,
                                                  before=profile_user.gold,
                                                  after=profile_user.gold - 15000,
                                                  comment='Покупка в магазине предметов'
                                                  )
    new_transaction.save()
    profile_user.gold -= 15000
    profile_user.save()

    context = {'amulets': sorted(amulet_reward, key=lambda item: item.rarity.id, reverse=True)}
    return render(request, 'exchange/open_box_amulets.html', context)


@auth_required()
def buy_and_open_box_book(request: HttpRequest) -> HttpResponseRedirect | HttpResponse:
    """ Покупка и открытие пользователем сундука с книгами опыта стоимостью 1 600.
        Случайно генерирует 9 книг и создает 1 книгу UR редкости.
        У пользователя снимаются деньги.
        Создается запись в Transaction.
        Книги, полученные из сундука выводятся пользователю.
    """

    profile_user = Profile.objects.get(user=request.user)
    if profile_user.gold < 1600:
        messages.error(request, 'Вам не хватает денег!')
        return HttpResponseRedirect(reverse('home'))

    all_items = ExperienceItems.objects.all().order_by('rarity')  # мал, сре, больш

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

    r_items_user, _ = UsersInventory.objects.get_or_create(owner=request.user, item=all_items[0])
    sr_items_user, _ = UsersInventory.objects.get_or_create(owner=request.user, item=all_items[1])
    ur_items_user, _ = UsersInventory.objects.get_or_create(owner=request.user, item=all_items[2])

    r_items_user.amount += count_r_books
    sr_items_user.amount += count_sr_books
    ur_items_user.amount += count_ur_books
    for_transaction = [r_items_user, sr_items_user, ur_items_user]

    with transaction.atomic():
        UsersInventory.objects.bulk_update(for_transaction, ['amount'])

    new_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                  user=request.user,
                                                  before=profile_user.gold,
                                                  after=profile_user.gold - 1600,
                                                  comment='Покупка в магазине предметов'
                                                  )
    new_transaction.save()
    profile_user.gold -= 1600
    profile_user.save()

    context = {'books': sorted(items_reward_for_view, key=lambda item: item.rarity, reverse=True)}
    return render(request, 'exchange/open_box_books.html', context)


@auth_required(error_message='Для покупки необходимо авторизоваться')
def buy_box_card(request: HttpRequest) -> HttpResponseRedirect:
    """ Покупка и открытие пользователем сундука с UR картой стоимостью 20 000.
        Создает карту UR редкости с максимальным значение начального здоровья или урона.
        У пользователя снимаются деньги.
        Создается запись в Transaction.
        Создается новая запись в HistoryReceivingCards.
    """

    profile_user = Profile.objects.get(user=request.user)

    if profile_user.card_slots <= Card.objects.filter(owner=request.user.id).count():
        messages.error(request, 'У вас не хватает места для получения новой карты!')
        return HttpResponseRedirect(reverse('items_store'))

    if profile_user.gold < 20000:
        messages.error(request, 'Вам не хватает денег!')
        return HttpResponseRedirect(reverse('home'))

    attributes = ('damage', 'hp')
    max_attribute = choice(attributes)

    new_card = create_new_card(user=request.user,
                               ur_box=True,
                               max_attribute=max_attribute)

    new_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                  user=request.user,
                                                  before=profile_user.gold,
                                                  after=profile_user.gold-20000,
                                                  comment='Покупка в магазине предметов'
                                                  )
    new_transaction.save()
    profile_user.gold -= 20000
    profile_user.save()

    new_history_receiving_cards = HistoryReceivingCards.objects.create(card=new_card,
                                                                       date_and_time=date_time_now(),
                                                                       user=request.user,
                                                                       method_receiving='Покупка сундука'
                                                                       )
    new_history_receiving_cards.save()

    return HttpResponseRedirect(f'/cards/card-{new_card.id}')


@auth_required(error_message='Для покупки необходимо авторизоваться', redirect_url_name='items_store')
def buy_upgrade_item(request: HttpRequest, upgrade_item_id: int) -> HttpResponseRedirect:
    """ Покупка предмета усиления.
        Добавляет или создает предмет усиления в инвентаре пользователя в таблице UpgradeItemsUsers.
        Создает запись в Transactions.
        Изменяет gold в Profile текущего пользователя.
    """

    profile_user = Profile.objects.get(user=request.user)
    current_upgrade_item = get_object_or_404(UpgradeItemsType, pk=upgrade_item_id)

    if profile_user.gold < current_upgrade_item.price:
        messages.error(request, 'Для покупки вам не хватает денег!')
        return HttpResponseRedirect(reverse('items_store'))

    # Сделать ОБНОВИТЬ ИЛИ СОЗДАТЬ
    upgrade_item = UpgradeItemsType.objects.get(id=upgrade_item_id)
    try:
        upgrade_item_user = UpgradeItemsUsers.objects.get(owner=request.user,
                                                          upgrade_item_type=upgrade_item)

        upgrade_item_user.amount += 1
        upgrade_item_user.save()

    except UpgradeItemsUsers.DoesNotExist:
        new_upgrade_item_user = UpgradeItemsUsers.objects.create(owner=request.user,
                                                                 upgrade_item_type=upgrade_item,
                                                                 amount=1)
        new_upgrade_item_user.save()

    new_record_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                         user=request.user,
                                                         before=profile_user.gold,
                                                         after=profile_user.gold - upgrade_item.price,
                                                         comment='Покупка в магазине предметов')

    profile_user.gold = new_record_transaction.after
    new_record_transaction.save()
    profile_user.save()
    messages.success(request, 'Вы успешно совершили покупку!')

    return HttpResponseRedirect(reverse('items_store', kwargs={'store_filter': 'all'}))


@auth_required(redirect_url_name='items_store')
def menu_enhance_card(request: HttpRequest, card_id: int) -> HttpResponseRedirect | HttpResponse:
    """ Меню усиления карты с помощью предметов усиления """

    card = get_object_or_404(Card, pk=card_id)
    if request.user != card.owner:
        messages.error(request, 'Вы не можете усиливать эту карту!')
        return HttpResponseRedirect(reverse('home'))

    inventory = UpgradeItemsUsers.objects.filter(owner=request.user)
    context = {'title': 'Усиление карты',
               'header': f'Усиление карты {card_id}',
               'card': card,
               'inventory': inventory,
               }
    return render(request, 'exchange/card_stats_up.html', context)


@auth_required()
def enhance_card(request: HttpRequest, card_id: int, up_item_id: int) -> HttpResponseRedirect:
    """ Усиление карты с помощью предмета.
        Карта улучшает свои характеристики в зависимости от выбранного предмета.
        Удаляет выбранный предмет из инвентаря пользователя UpgradeItemsUsers.
        Создает запись в Transactions.
        Изменяет gold в Profile текущего пользователя.
    """

    current_card = get_object_or_404(Card, pk=card_id)

    if current_card.owner != request.user:
        messages.error(request, 'Вы не можете улучшать эту карту!')
        return HttpResponseRedirect(reverse('home'))

    current_up_item = UpgradeItemsUsers.objects.filter(owner=request.user,
                                                       upgrade_item_type=up_item_id).last()
    if current_up_item is None:
        messages.error(request, 'У вас недостаточно предметов усиления!')
        return HttpResponseRedirect(f'/inventory/card-{card_id}')
    elif current_up_item.amount <= 0:
        messages.error(request, 'У вас недостаточно предметов усиления!')
        return HttpResponseRedirect(f'/inventory/card-{card_id}')

    profile_user = Profile.objects.get(user=request.user)
    if profile_user.gold < current_up_item.upgrade_item_type.price_of_use:
        messages.error(request, 'У вас недостаточно денег!')
        return HttpResponseRedirect(f'/inventory/card-{card_id}')

    if current_card.enhancement >= current_card.max_enhancement:
        messages.error(request, 'Эта карта имеет максимальный уровень усиления!')
        return HttpResponseRedirect(reverse('home'))

    if current_up_item.upgrade_item_type.type == 'hp':
        current_card.enhance_hp()
    elif current_up_item.upgrade_item_type.type == 'attack':
        current_card.enhance_attack()
    elif current_up_item.upgrade_item_type.type == 'random':
        current_card.enhance_random()

    current_up_item.amount -= 1
    new_record_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                         user=request.user,
                                                         before=profile_user.gold,
                                                         after=profile_user.gold - current_up_item.upgrade_item_type.price_of_use,
                                                         comment='Усиление карты')

    profile_user.gold = new_record_transaction.after
    new_record_transaction.save()
    profile_user.save()
    current_up_item.save()

    messages.success(request, 'Вы улучшили карту!')
    return HttpResponseRedirect(f'/inventory/card-{card_id}')
