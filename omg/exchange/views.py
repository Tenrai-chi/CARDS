from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.http import HttpResponseRedirect, HttpResponse, HttpRequest
from django.shortcuts import render, get_object_or_404
from django.urls import reverse

from cards.models import Card, Type
from common.decorators import auth_required, owner_required
from common.utils import date_time_now
from users.models import Transactions, Profile

from .forms import BuyItemForm
from .services import (purchase_amulet, set_amulet_on_card, open_box_amulet, open_box_book,
                       open_box_card, purchase_upgrade_item, process_enhance_card)
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
        context['max_count_amulets'] = Profile.objects.get(user=user_id).amulet_slots
        context['user_items'] = UsersInventory.objects.filter(owner=request.user).order_by('id')
        context['upgrade_items'] = UpgradeItemsUsers.objects.filter(owner=request.user).order_by('id')
        amulets = AmuletItem.objects.filter(owner=request.user).order_by('id')
        context['user_amulets'] = amulets
        context['count_amulets'] = len(amulets)

    elif inventory_filter == 'amulets':
        context['max_count_amulets'] = Profile.objects.get(user=user_id).amulet_slots
        amulets = AmuletItem.objects.filter(owner=request.user).order_by('id')
        context['user_amulets'] = amulets
        context['count_amulets'] = len(amulets)

    elif inventory_filter == 'upgrade_items':
        context['max_count_amulets'] = Profile.objects.get(user=user_id).amulet_slots
        context['count_amulets'] = AmuletItem.objects.filter(owner=request.user).count()
        context['upgrade_items'] = UpgradeItemsUsers.objects.filter(owner=request.user).order_by('id')

    elif inventory_filter == 'books_exp':
        context['max_count_amulets'] = Profile.objects.get(user=user_id).amulet_slots
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
    """ Покупка амулета """

    answer: dict = purchase_amulet(request.user.id, amulet_id)
    if answer.get('error_message'):
        messages.error(request, answer['error_message'])
        return HttpResponseRedirect(reverse('items_store'))
    else:
        messages.success(request, answer['success_message'])
        return HttpResponseRedirect(reverse('items_store', kwargs={'store_filter': 'amulets'}))


@auth_required()
@transaction.atomic
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
            profile = Profile.objects.get(user=request.user.id)
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

    answer: dict = set_amulet_on_card(request.user.id, card_id, amulet_id)
    if answer.get('error_message'):
        messages.error(request, answer['error_message'])
        return HttpResponseRedirect(reverse('home'))
    else:
        messages.success(request, answer['success_message'])
        return HttpResponseRedirect(f'/cards/card-{card_id}')


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
@transaction.atomic
def sale_amulet(request: HttpRequest, user_id: int, amulet_id: int) -> HttpResponseRedirect:
    """ Продажа пользователем амулета внутриигровому магазину.
        Амулет удаляется из инвентаря и запись о нем так же удаляется.
        Пользователь получает деньги за продажу.
        Создается запись в Transactions.
    """

    amulet = get_object_or_404(AmuletItem, pk=amulet_id)
    profile = Profile.objects.get(user=request.user.id)
    if amulet.owner == request.user:
        new_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                      user=request.user,
                                                      before=profile.gold,
                                                      after=profile.gold + round(amulet.amulet_type.price),
                                                      comment='Продажа амулета')
        profile.gold += round(amulet.amulet_type.price)
        amulet.delete()
        profile.save()
        new_transaction.save()
        messages.success(request, 'Вы успешно продали амулет!')

        return HttpResponseRedirect(reverse('inventory_user',
                                            kwargs={'inventory_filter': 'amulets', 'user_id': request.user.id}))

    else:
        messages.error(request, 'Произошла ошибка!')

        return HttpResponseRedirect(reverse('home'))


@auth_required()
def buy_and_open_box_amulet(request: HttpRequest) -> HttpResponseRedirect | HttpResponse:
    """ Вывод содержимого купленного сундука с амулетами """

    answer: dict = open_box_amulet(request.user.id)
    if answer.get('error_message'):
        messages.error(request, 'У вас не хватает места для покупки амулета!')
        return HttpResponseRedirect(reverse('items_store'))
    else:
        context = {'amulets': answer.get('new_amulets'), 'title': 'Награда сундука с амулетами'}
        return render(request, 'exchange/open_box_amulets.html', context)


@auth_required()
def buy_and_open_box_book(request: HttpRequest) -> HttpResponseRedirect | HttpResponse:
    """ Вывод содержимого купленного сундука с книгами """

    answer: dict = open_box_book(request.user.id)
    if answer.get('error_message'):
        messages.error(request, answer['error_message'])
        return HttpResponseRedirect(reverse('home'))
    else:
        context = {'books': answer.get('books'),
                   'title': 'Награда сундука с книгами',
                   }
        return render(request, 'exchange/open_box_books.html', context)


@auth_required(error_message='Для покупки необходимо авторизоваться')
def buy_box_card(request: HttpRequest) -> HttpResponseRedirect:
    """ Вывод карты, полученной из сундука """

    answer_data: dict = open_box_card(request.user.id)
    if answer_data.get('error_message'):
        messages.error(request, answer_data['error_message'])
        return HttpResponseRedirect(reverse('items_store'))
    else:
        return HttpResponseRedirect(f'/cards/card-{answer_data["new_card_id"]}')


@auth_required(error_message='Для покупки необходимо авторизоваться', redirect_url_name='items_store')
def buy_upgrade_item(request: HttpRequest, upgrade_item_id: int) -> HttpResponseRedirect:
    """ Покупка предмета усиления """

    answer_data: dict = purchase_upgrade_item(request.user.id, upgrade_item_id)
    if answer_data.get('error_message'):
        messages.error(request, answer_data['error_message'])
    else:
        messages.success(request, answer_data['success_message'])
    return HttpResponseRedirect(reverse('items_store', kwargs={'store_filter': 'upgrade_items'}))


@auth_required(redirect_url_name='items_store')
def menu_enhance_card(request: HttpRequest, card_id: int) -> HttpResponseRedirect | HttpResponse:
    """ Меню усиления карты с помощью предметов усиления """

    card = get_object_or_404(Card, pk=card_id)
    if request.user != card.owner:
        messages.error(request, 'Вы не можете усиливать эту карту!')
        return HttpResponseRedirect(reverse('home'))

    inventory = UpgradeItemsUsers.objects.filter(owner=request.user.id)
    context = {'title': 'Усиление карты',
               'header': f'Усиление карты {card_id}',
               'card': card,
               'inventory': inventory,
               }
    return render(request, 'exchange/card_stats_up.html', context)


@auth_required()
def enhance_card(request: HttpRequest, card_id: int, up_item_id: int) -> HttpResponseRedirect:
    """ Усиление карты с помощью предмета """

    answer_data: dict = process_enhance_card(request.user.id, card_id, up_item_id)
    if answer_data.get('error_message') and answer_data.get('url_name_redirect'):
        messages.error(request, answer_data['error_message'])
        return HttpResponseRedirect(reverse(answer_data['url_name_redirect']))
    elif answer_data.get('error_message'):
        messages.error(request, answer_data['error_message'])
        return HttpResponseRedirect(f'/inventory/card-{card_id}')
    else:
        messages.success(request, answer_data['success_message'])
        return HttpResponseRedirect(f'/inventory/card-{card_id}')
