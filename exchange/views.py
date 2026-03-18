from django.contrib import messages
from django.db.models import F
from django.http import HttpResponseRedirect, HttpResponse, HttpRequest
from django.shortcuts import render, get_object_or_404
from django.urls import reverse

from cards.models import Card, Type
from common.decorators import auth_required, owner_required
from users.models import Profile

from .forms import BuyItemForm
from .services import (change_amulet_service, open_box_amulet, open_box_book, open_box_card,
                       buy_upgrade_item_service, enhance_card_service, buy_item_service,
                       remove_service, sale_amulet_service, buy_amulet_service)
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
    """ Покупка амулета.
        Обрабатывает только POST запросы.
        Вызывает сервис покупки амулета.
        При ошибке направляет на страницу магазина с темой all.
        При успехе направляет на страницу магазина с темой amulets.
        Выводит пользователю сообщение об успехе или ошибке.
    """

    if request.method == 'POST':
        answer: dict = buy_amulet_service(request.user.id, amulet_id)
        if answer.get('error_message'):
            messages.error(request, answer['error_message'])
            return HttpResponseRedirect(reverse('items_store', kwargs={'store_filter': 'all'}))
        else:
            messages.success(request, answer['success_message'])
            return HttpResponseRedirect(reverse('items_store', kwargs={'store_filter': 'amulets'}))
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


@auth_required()
def buy_item(request: HttpRequest, item_id: int) -> HttpResponseRedirect | HttpResponse:
    """ Покупка книг опыта.
        При GET запросе выводит форму для покупки.
        При POST запросе и валидных данных вызывает сервис покупки книг опыта.
        В зависимости от ответа сервиса направляет на нужную страницу с сообщением.
        При других запросах направляет на стартовую страницу.
    """

    if request.method == 'POST':
        form = BuyItemForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            buy_item_service_data: dict = buy_item_service(request.user.id, item_id, amount)

            if buy_item_service_data.get('error_message'):
                item = get_object_or_404(ExperienceItems, pk=item_id)
                messages.error(request, buy_item_service_data['error_message'])
                context = {'form': form,
                           'title': 'Покупка предмета',
                           'header': f'Покупка предмета "{item.name}"',
                           'item': item
                           }
                return render(request, 'exchange/buy_item.html', context)
            else:
                messages.success(request, buy_item_service_data['success_message'])
                return HttpResponseRedirect(reverse('items_store', kwargs={'store_filter': 'books_exp'}))

        else:
            item = get_object_or_404(ExperienceItems, pk=item_id)
            context = {'form': form,
                       'title': 'Покупка предмета',
                       'header': f'Покупка предмета "{item.name}"',
                       'item': item
                       }

            messages.error(request, 'Неверные данные!')
            return render(request, 'exchange/buy_item.html', context)

    elif request.method == 'GET':
        form = BuyItemForm(initial={'amount': 1})
        item = get_object_or_404(ExperienceItems, pk=item_id)
        context = {'title': 'Покупка предмета',
                   'header': f'Покупка предмета "{item.name}"',
                   'form': form,
                   'item': item
                   }
        return render(request, 'exchange/buy_item.html', context)

    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


@auth_required()
def change_amulet_menu(request: HttpRequest, card_id: int) -> HttpResponse:
    """ Меню смены амулеты у выбранной карты.
        Выводит список доступных амулетов.
    """

    card = get_object_or_404(Card, pk=card_id)
    available_amulets = AmuletItem.objects.filter(owner=request.user.id)
    context = {'title': 'Выбор амулета',
               'header': 'Выбрать амулет',
               'card': card,
               'amulets': available_amulets}

    return render(request, 'cards/change_amulet_menu.html', context)


@auth_required()
def change_amulet(request: HttpRequest, card_id: int, amulet_id: int) -> HttpResponseRedirect:
    """ Установка амулета на карту.
        Обрабатывает только POST запросы.
        Вызывает сервис для смены амулета.
        При ошибке направляет на главную страницу.
        При успехе направляет на страницу просмотра карты.
        Выводит сообщение об успехе или ошибке.
    """

    if request.method == 'POST':
        answer: dict = change_amulet_service(request.user.id, card_id, amulet_id)
        if answer.get('error_message'):
            messages.error(request, answer['error_message'])
            return HttpResponseRedirect(reverse('home'))
        else:
            messages.success(request, answer['success_message'])
            return HttpResponseRedirect(reverse('card', kwargs={'card_id': card_id}))
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


@auth_required()
def remove_amulet(request: HttpRequest, card_id: int, amulet_id: int) -> HttpResponseRedirect:
    """ Удаление амулета у карты.
        Обрабатывает только POST запросы.
        Вызывает сервис для снятия амулета.
        При ошибке направляет на стартовую страницу.
        При успехе направляет на страницу просмотра карты.
        Выводит пользователю сообщение об успехе или ошибке.
    """

    if request.method == 'POST':
        remove_service_data: dict = remove_service(request.user.id, amulet_id, card_id)
        if remove_service_data.get('error_message'):
            messages.error(request, remove_service_data['error_message'])
            return HttpResponseRedirect(reverse('home'))
        else:
            messages.success(request, remove_service_data['success_message'])
            return HttpResponseRedirect(reverse('card', kwargs={'card_id': card_id}))
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


@auth_required()
@owner_required()
def sale_amulet(request: HttpRequest, user_id: int, amulet_id: int) -> HttpResponseRedirect:
    """ Продажа амулета.
        Обрабатывает только POST запросы.
        Вызывает сервис для продажи амулета.
        При ошибке направляет на стартовую страницу.
        При успехе направляет на страницу просмотра инвентаря пользователя.
        Выводит сообщение об успехе или ошибке.
    """

    if request.method == 'POST':
        answer: dict = sale_amulet_service(request.user.id, amulet_id)
        if answer.get('error_message'):
            messages.error(request, answer['error_message'])
            return HttpResponseRedirect(reverse('home'))
        else:
            messages.success(request, answer['success_message'])
            return HttpResponseRedirect(reverse('inventory_user',
                                                kwargs={'inventory_filter': 'amulets', 'user_id': request.user.id}))

    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


@auth_required()
def buy_and_open_box_amulet(request: HttpRequest) -> HttpResponseRedirect | HttpResponse:
    """ Покупка сундука с амулетами.
        Обрабатывает только POST запросы.
        Вызывает сервис для открытия сундука.
        При ошибке направляет на страницу магазина.
        При успехе показывает полученные амулеты.
    """

    if request.method == 'POST':
        answer: dict = open_box_amulet(request.user.id)
        if answer.get('error_message'):
            messages.error(request, 'У вас не хватает места для покупки амулета!')
            return HttpResponseRedirect(reverse('items_store'))
        else:
            context = {'amulets': answer.get('new_amulets'), 'title': 'Награда сундука с амулетами'}
            return render(request, 'exchange/open_box_amulets.html', context)
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


@auth_required()
def buy_and_open_box_book(request: HttpRequest) -> HttpResponseRedirect | HttpResponse:
    """ Покупка сундука с книгами.
        Обрабатывает только POST запросы.
        Вызывает сервис для открытия сундука.
        При ошибке направляет на страницу магазина сундуков.
        При успехе показывает полученные книги.
    """

    if request.method == 'POST':
        answer: dict = open_box_book(request.user.id)
        if answer.get('error_message'):
            messages.error(request, answer['error_message'])
            return HttpResponseRedirect(reverse('items_store', kwargs={'store_filter': 'box'}))
        else:
            context = {'books': answer.get('books'),
                       'title': 'Награда сундука с книгами',
                       }
            return render(request, 'exchange/open_box_books.html', context)
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


@auth_required(error_message='Для покупки необходимо авторизоваться')
def buy_box_card(request: HttpRequest) -> HttpResponseRedirect:
    """ Покупка сундука с UR картой.
        Обрабатывает только POST запросы.
        Вызывает сервис для открытия сундука.
        При ошибке направляет на страницу магазина сундуков.
        При успехе показывает полученную карту.
    """

    if request.method == 'POST':
        answer_data: dict = open_box_card(request.user.id)
        if answer_data.get('error_message'):
            messages.error(request, answer_data['error_message'])
            return HttpResponseRedirect(reverse('items_store', kwargs={'store_filter': answer_data['box']}))
        else:
            return HttpResponseRedirect(reverse('card', kwargs={'card_id': answer_data['new_card_id']}))
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


@auth_required(error_message='Для покупки необходимо авторизоваться', redirect_url_name='items_store')
def buy_upgrade_item(request: HttpRequest, upgrade_item_id: int) -> HttpResponseRedirect:
    """ Покупка предмета усиления.
        Обрабатывает только POST запросы.
        Вызывает сервис для покупки предмета.
        Направляет на страницу магазина с фильтром и выводит сообщение в зависимости от успеха.
    """

    if request.method == 'POST':
        answer_data: dict = buy_upgrade_item_service(request.user.id, upgrade_item_id)
        if answer_data.get('error_message'):
            messages.error(request, answer_data['error_message'])
        else:
            messages.success(request, answer_data['success_message'])
        return HttpResponseRedirect(reverse('items_store', kwargs={'store_filter': 'upgrade_items'}))
    messages.error(request, 'Неожиданный запрос')
    return HttpResponseRedirect(reverse('home'))


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
    """ Усиление карты с помощью предмета.
        Обрабатывает только POST запросы.
        Вызывает сервис для усиления карты.
        При успехе направляет на страницу выбранной карты с сообщением об успехе.
        При ошибке направляет на страницу, полученную из сервиса с сообщением об ошибке.
    """

    if request.method == 'POST':
        answer_data: dict = enhance_card_service(request.user.id, card_id, up_item_id)
        if answer_data.get('error_message') and answer_data.get('url_name_redirect'):
            messages.error(request, answer_data['error_message'])
            return HttpResponseRedirect(reverse(answer_data['url_name_redirect']))
        elif answer_data.get('error_message'):
            messages.error(request, answer_data['error_message'])
            return HttpResponseRedirect(reverse('menu_enhance_card', kwargs={'card_id':card_id}))
        else:
            messages.success(request, answer_data['success_message'])
            return HttpResponseRedirect(reverse('menu_enhance_card', kwargs={'card_id': card_id}))
    messages.error(request, 'Неожиданный запрос')
    return HttpResponseRedirect(reverse('home'))
