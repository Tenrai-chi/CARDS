from random import randint, choice

from django.contrib import messages
from django.db.models import F
from django.http import HttpResponseRedirect, HttpResponse, HttpRequest
from django.shortcuts import render, get_object_or_404
from django.urls import reverse

from cards.models import Card, HistoryReceivingCards, ClassCard, Type, Rarity
from common.utils import date_time_now, create_new_card
from users.models import Transactions, Profile

from .forms import BuyItemForm
from .models import ExperienceItems, UsersInventory, AmuletItem, AmuletType, UpgradeItemsUsers


def view_inventory_user(request: HttpRequest, user_id: int,
                        inventory_filter: str = 'all') -> HttpResponseRedirect | HttpResponse:
    """ Просмотр инвентаря пользователя.
        Доступно только если текущий пользователь является владельцем инвентаря.
     """

    if request.user.id != user_id:
        messages.error(request, 'Просмотр инвентаря пользователя невозможен')

        return HttpResponseRedirect(reverse('home'))

    if inventory_filter == 'all':
        max_count_amulets = Profile.objects.get(pk=user_id).amulet_slots
        count_amulets = AmuletItem.objects.filter(owner=request.user).count()
        user_items = UsersInventory.objects.filter(owner=request.user).order_by('id')
        user_amulets = AmuletItem.objects.filter(owner=request.user).order_by('id')
        upgrade_items = UpgradeItemsUsers.objects.filter(owner=request.user).order_by('id')

    elif inventory_filter == 'amulets':
        max_count_amulets = Profile.objects.get(pk=user_id).amulet_slots
        count_amulets = AmuletItem.objects.filter(owner=request.user).count()
        user_items = None
        user_amulets = AmuletItem.objects.filter(owner=request.user).order_by('id')
        upgrade_items = None

    elif inventory_filter == 'upgrade_items':
        max_count_amulets = Profile.objects.get(pk=user_id).amulet_slots
        count_amulets = AmuletItem.objects.filter(owner=request.user).count()
        user_items = None
        user_amulets = None
        upgrade_items = UpgradeItemsUsers.objects.filter(owner=request.user).order_by('id')

    elif inventory_filter == 'books_exp':
        max_count_amulets = Profile.objects.get(pk=user_id).amulet_slots
        count_amulets = AmuletItem.objects.filter(owner=request.user).count()
        user_items = UsersInventory.objects.filter(owner=request.user).order_by('id')
        user_amulets = None
        upgrade_items = None

    else:
        pass

    context = {'title': 'Инвентарь',
               'header': f'Инвентарь {request.user.username}',
               'user_items': user_items,
               'user_amulets': user_amulets,
               'count_amulets': count_amulets,
               'max_count_amulets': max_count_amulets,
               'upgrade_items': upgrade_items
               }

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
        upgrade_items = True

    elif store_filter == 'box':
        # items_on_sale = None
        # amulets_on_sale = None
        is_box = True
        # upgrade_items = False

    elif store_filter == 'amulets':
        # items_on_sale = None
        amulets_on_sale = AmuletType.objects.filter(sale_now=True).annotate(new_price=F('price') * (100 - F('discount')) / 100)
        # is_box = False
        # upgrade_items = False

    elif store_filter == 'upgrade_items':
        # items_on_sale = None
        # amulets_on_sale = None
        is_box = False
        # upgrade_items = True

    elif store_filter == 'books_exp':
        items_on_sale = ExperienceItems.objects.filter(sale_now=True).order_by('experience_amount')
        # amulets_on_sale = None
        # is_box = False
        # upgrade_items = False

    else:
        print('Какая-то фигня')

    context = {'title': 'Магазин предметов',
               'header': 'Магазин предметов',
               'items': items_on_sale,
               'amulets': amulets_on_sale,
               'is_box': is_box,
               'upgrade_items': upgrade_items
               }

    return render(request, 'exchange/items_store.html', context)


def buy_amulet(request: HttpRequest, amulet_id: int) -> HttpResponseRedirect:
    """ Покупка амулета.
        Создает амулет на основе амулета из магазина и присваивает его покупателю в таблице AmuletItem.
        Создает запись в Transactions.
        Изменяет gold в Profile текущего пользователя.
    """

    if request.user.is_authenticated:
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

        return HttpResponseRedirect(reverse('items_store', kwargs={'store_filter': 'all'}))

    else:
        messages.error(request, 'Для покупки необходимо авторизоваться!')

        return HttpResponseRedirect(reverse('items_store'))


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

            return HttpResponseRedirect(reverse('items_store', kwargs={'store_filter': 'all'}))
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


def change_amulet_menu(request: HttpRequest, card_id: int) -> HttpResponse:
    """ Меню смены амулеты у выбранной карты.
        Выводит список доступных амулетов.
    """

    # Проверка того что пользователь хозяин карты и он авторизован
    card = Card.objects.get(pk=card_id)
    available_amulets = AmuletItem.objects.filter(owner=request.user)
    context = {'title': 'Выбор амулета',
               'header': 'Выбрать амулет',
               'card': card,
               'amulets': available_amulets}

    return render(request, 'cards/change_amulet_menu.html', context)


def change_amulet(request: HttpRequest, card_id: int, amulet_id: int) -> HttpResponseRedirect:
    """ Устанавливает выбранный амулет на выбранную карту.
        Если у карты был установлен амулет, то отвязывает его.
    """

    if request.user.is_authenticated:
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

    else:
        messages.error(request, 'Вы не можете поменять у карты амулет!')

        return HttpResponseRedirect(reverse('home'))


def remove_amulet(request: HttpRequest, card_id: int, amulet_id: int) -> HttpResponseRedirect:
    """ Удаляет у выбранного амулета карту """

    if request.user.is_authenticated:
        current_amulet = get_object_or_404(AmuletItem, pk=amulet_id)
        if current_amulet.owner == request.user:
            current_amulet.card = None
            current_amulet.save()
            messages.success(request, 'Вы успешно сняли амулет!')

            return HttpResponseRedirect(f'/cards/card-{card_id}')
        else:
            messages.error(request, 'Вы не можете пользоваться этим амулетом!')

            return HttpResponseRedirect(reverse('home'))
    else:
        messages.error(request, 'Для данных действий нужно авторизоваться!')

        return HttpResponseRedirect(reverse('home'))


def sale_amulet(request: HttpRequest, user_id: int, amulet_id: int) -> HttpResponseRedirect:
    """ Продажа пользователем амулета внутриигровому магазину.
        Амулет удаляется из инвентаря и запись о нем так же удаляется.
        Пользователь получает деньги за продажу.
        Создается запись в Transactions.
    """

    if request.user.is_authenticated and request.user.id == user_id:
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

    else:
        messages.error(request, 'Произошла ошибка!')

        return HttpResponseRedirect(reverse('home'))


def buy__and_open_box_amulet(request: HttpRequest) -> HttpResponseRedirect | HttpResponse:
    """ Покупка и открытие пользователем сундука с амулетами стоимостью 15 000.
        Случайно выбирает 5 амулетов и помещает в инвентарь пользователя.
        У пользователя снимаются деньги.
        Создается запись в Transaction.
        Амулеты, полученные из сундука выводятся пользователю
    """

    if request.user.is_authenticated:
        profile_user = Profile.objects.get(user=request.user)

        if request.user.profile.amulet_slots - 5 <= AmuletItem.objects.filter(owner=request.user.id).count():
            messages.error(request, 'У вас не хватает места для покупки амулета!')

            return HttpResponseRedirect(reverse('items_store'))

        if profile_user.gold >= 15000:

            amulets_ur = AmuletType.objects.filter(rarity__name='UR')
            amulets_ur_count = AmuletType.objects.filter(rarity__name='UR').count()

            amulets_sr = AmuletType.objects.filter(rarity__name='SR')
            amulets_sr_count = AmuletType.objects.filter(rarity__name='SR').count()

            amulets_r = AmuletType.objects.filter(rarity__name='R')
            amulets_r_count = AmuletType.objects.filter(rarity__name='R').count()

            amulet_reward = []
            for _ in range(5):
                chance = randint(1, 100)
                if chance <= amulets_r[1].rarity.chance_drop_on_box:  # Если выпал R
                    random_amulet = randint(0, amulets_r_count-1)
                    new_amulet = AmuletItem.objects.create(amulet_type=amulets_r[random_amulet],
                                                           owner=request.user)
                    amulet_reward.append(amulets_r[random_amulet])
                    new_amulet.save()

                elif chance <= (amulets_sr[1].rarity.chance_drop_on_box + amulets_r[1].rarity.chance_drop_on_box):  # Если выпал SR

                    random_amulet = randint(0, amulets_sr_count-1)
                    new_amulet = AmuletItem.objects.create(amulet_type=amulets_sr[random_amulet],
                                                           owner=request.user)
                    amulet_reward.append(amulets_sr[random_amulet])
                    new_amulet.save()

                else:  # Если выпал UR

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
        else:
            messages.error(request, 'Вам не хватает денег!')
            return HttpResponseRedirect(reverse('home'))

    else:
        messages.error(request, 'Произошла ошибка!')

        return HttpResponseRedirect(reverse('home'))


def buy_and_open_box_book(request: HttpRequest) -> HttpResponseRedirect | HttpResponse:
    """ Покупка и открытие пользователем сундука с книгами опыта стоимостью 1 600.
        Случайно генерирует 9 книг и создает 1 книгу UR редкости.
        У пользователя снимаются деньги.
        Создается запись в Transaction.
        Книги, полученные из сундука выводятся пользователю.
    """

    if request.user.is_authenticated:
        profile_user = Profile.objects.get(user=request.user)
        if profile_user.gold >= 1600:
            all_items = ExperienceItems.objects.all().order_by('rarity')
            item_reward = []
            for _ in range(9):  # Переделать. Сначала рандом, потом запись количества 1 вызовом
                chance = randint(1, 100)
                if chance <= all_items[0].chance_drop_on_box:
                    item_reward.append(all_items[0])
                    try:
                        items_user = UsersInventory.objects.get(owner=request.user,
                                                                item=all_items[0])
                        items_user.amount += 1
                        items_user.save()

                    except UsersInventory.DoesNotExist:
                        new_item_user = UsersInventory.objects.create(owner=request.user,
                                                                      item=all_items[0],
                                                                      amount=1)
                        new_item_user.save()

                elif all_items[0].chance_drop_on_box <= (all_items[0].chance_drop_on_box + all_items[1].chance_drop_on_box):
                    item_reward.append(all_items[1])
                    try:
                        items_user = UsersInventory.objects.get(owner=request.user,
                                                                item=all_items[1])
                        items_user.amount += 1
                        items_user.save()

                    except UsersInventory.DoesNotExist:
                        new_item_user = UsersInventory.objects.create(owner=request.user,
                                                                      item=all_items[1],
                                                                      amount=1)
                        new_item_user.save()

                else:
                    item_reward.append(all_items[2])
                    try:
                        items_user = UsersInventory.objects.get(owner=request.user,
                                                                item=all_items[2])
                        items_user.amount += 1
                        items_user.save()

                    except UsersInventory.DoesNotExist:
                        new_item_user = UsersInventory.objects.create(owner=request.user,
                                                                      item=all_items[0],
                                                                      amount=2)
                        new_item_user.save()

            item_reward.append(all_items[2])
            try:
                items_user = UsersInventory.objects.get(owner=request.user,
                                                        item=all_items[2])
                items_user.amount += 1
                items_user.save()

            except UsersInventory.DoesNotExist:
                new_item_user = UsersInventory.objects.create(owner=request.user,
                                                              item=all_items[2],
                                                              amount=1)
                new_item_user.save()

            new_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                          user=request.user,
                                                          before=profile_user.gold,
                                                          after=profile_user.gold - 1600,
                                                          comment='Покупка в магазине предметов'
                                                          )
            new_transaction.save()
            profile_user.gold -= 1600
            profile_user.save()

            context = {'books': sorted(item_reward, key=lambda item: item.rarity, reverse=True)}
            return render(request, 'exchange/open_box_books.html', context)
        else:
            messages.error(request, 'Вам не хватает денег!')

            return HttpResponseRedirect(reverse('home'))
    else:
        messages.error(request, 'Произошла ошибка!')

        return HttpResponseRedirect(reverse('home'))


def buy_box_card(request: HttpRequest) -> HttpResponseRedirect:
    """ Покупка и открытие пользователем сундука с UR картой стоимостью 20 000.
        Создает карту UR редкости с максимальным значение начального здоровья или урона.
        У пользователя снимаются деньги.
        Создается запись в Transaction.
        Создается новая запись в HistoryReceivingCards.
    """

    if request.user.is_authenticated:
        profile_user = Profile.objects.get(user=request.user)

        if profile_user.card_slots <= Card.objects.filter(owner=request.user.id).count():
            messages.error(request, 'У вас не хватает места для получения новой карты!')

            return HttpResponseRedirect(reverse('items_store'))

        if profile_user.gold >= 20000:
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

        else:
            messages.error(request, 'Вам не хватает денег!')

            return HttpResponseRedirect(reverse('home'))

    else:
        messages.error(request, 'Для покупки необходимо авторизоваться!')

        return HttpResponseRedirect(reverse('home'))


# def open_box_items(request: HttpRequest, user_id: int, open_box: str) -> HttpResponseRedirect | HttpResponse:
#     """ Вывод книг опыта или амулетов, полученных из сундука """
#
#     if request.user.is_authenticated:
#         if open_box == 'books':
#             items = UsersInventory.objects.filter(owner=user_id).order_by('-id')[:10]
#             print(items)
#             context = {'books': items}
#         elif open_box == 'amulets':
#             items = AmuletItem.objects.filter(owner=user_id).order_by('-id')[:5]
#             context = {'amulets': items}
#         else:
#             pass
#         return render(request, 'exchange/open_box_books.html', context)
#     else:
#         return HttpResponseRedirect(reverse('home'))
