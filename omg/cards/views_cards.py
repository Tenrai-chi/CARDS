from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .forms import SaleCardForm, UseItemForm
from .models import Card, Rarity, CardStore
from .services_cards import (get_cards_with_pagination, create_free_card, buy_card_service,
                             transfer_card_to_user, merge_user_card, card_sale_service,
                             level_up_with_item_service, remove_from_sale_card_service)

from .utils import calculate_need_exp

from common.decorators import auth_required
from common.utils import time_difference_check
from exchange.models import UsersInventory, AmuletItem, BattleEventParticipants
from users.models import Profile


def view_cards(request: HttpRequest) -> HttpResponse:
    """ Вывод всех существующих карт.
        Вызывает сервис для получения карт с пагинацией.
        Выводит полученные данные пользователю.
    """

    try:
        page_num = int(request.GET.get('page', 1))
    except ValueError:
        page_num = 1
    cards_data: dict = get_cards_with_pagination(page_num)
    context = {'title': 'Просмотр карт',
               'header': 'Все карты',
               'cards': cards_data.get('cards'),
               'page': cards_data.get('page'),
               }

    return render(request, 'cards/view_cards.html', context)


@auth_required(error_message='Для покупки необходимо авторизоваться!', redirect_url_name='card_store')
def buy_card(request: HttpRequest, card_id: int) -> HttpResponseRedirect:
    """ Покупка карты в магазине.
        Обрабатывает только POST запросы.
        Вызывает сервис покупки карты.
        При ошибке направляет на страницу магазина карт.
        При успехе направляет на страницу просмотра купленной карты.
        Выводит сообщение об успехе или ошибке.
    """

    if request.method == 'POST':
        answer_buy_card_service: dict = buy_card_service(request.user.id, card_id)
        if answer_buy_card_service.get('error_message'):
            messages.error(request, answer_buy_card_service['error_message'])
            return HttpResponseRedirect(reverse('card_store'))
        else:
            new_card_id = answer_buy_card_service.get('new_card_id')
            messages.success(request, 'Вы успешно совершили покупку!')
            return HttpResponseRedirect(reverse('card', kwargs={'card_id': new_card_id}))
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


def get_card(request: HttpRequest) -> HttpResponse:
    """ Страница получения бесплатно карты """

    rarity_chance_drop: dict = Rarity.objects.values('name', 'drop_chance')
    if not request.user.is_authenticated:
        context = {'title': 'Получить карту', 'header': 'Получить бесплатную карту',
                   'rarity_chance_drop': rarity_chance_drop}
        return render(request, 'cards/get_card.html', context)

    user_profile = Profile.objects.get(user=request.user.id)
    take_card, hours = time_difference_check(user_profile.receiving_timer, 6)

    context = {'title': 'Получить карту',
               'header': 'Получить бесплатную карту',
               'rarity_chance_drop': rarity_chance_drop,
               'user_profile': user_profile,
               'take_card': take_card,
               'hours': 6 - hours
               }

    return render(request, 'cards/get_card.html', context)


@auth_required(error_message='Чтобы получить бесплатную карту необходимо авторизоваться')
def create_card(request: HttpRequest) -> HttpResponseRedirect:
    """ Получение бесплатной карты.
        Обрабатывает только POST запросы.
        Вызывает сервис получения бесплатной карты.
        При ошибке направляет на страницу, полученную из сервиса.
        При успехе направляет на страницу полученной карты.
    """

    if request.method == 'POST':
        answer_create_free_card: dict = create_free_card(request.user.id)
        if answer_create_free_card.get('error_message'):
            messages.error(request, answer_create_free_card['error_message'])
            return HttpResponseRedirect(reverse(answer_create_free_card['return_name']))
        else:
            new_card_id = answer_create_free_card['new_card_id']
            return HttpResponseRedirect(reverse('card', kwargs={'card_id': new_card_id}))
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


def card_store(request: HttpRequest) -> HttpResponse:
    """ Вывод ассортимента магазина карт """

    available_cards = CardStore.objects.filter(sale_now=True).order_by('-rarity')

    context = {'title': 'Магазин карт',
               'header': 'Магазин карт',
               'cards': available_cards
               }

    return render(request, 'cards/card_store.html', context)


def view_user_cards(request: HttpRequest, user_id: int) -> HttpResponse:
    """ Вывод карт выбранного пользователя """

    user = get_object_or_404(User, pk=user_id)
    cards = Card.objects.filter(owner=user_id).order_by('rarity', 'class_card', 'id')
    max_count_cards = Profile.objects.get(user=user_id).card_slots

    context = {'title': 'Карты пользователя',
               'header': f'Карты пользователя {user.username}',
               'cards': cards,
               'user_info': user,
               'count_cards': len(cards),
               'max_count_cards': max_count_cards
               }

    return render(request, 'cards/view_user_cards.html', context)


def view_card(request: HttpRequest, card_id: int) -> HttpResponse:
    """ Просмотр выбранной карты """

    card = get_object_or_404(Card, pk=card_id)
    amulet = AmuletItem.objects.filter(card=card).last()
    need_exp = calculate_need_exp(card.level)

    context = {'title': 'Выбранная карта',
               'header': 'Выбранная карта',
               'card': card,
               'need_exp': need_exp,
               'amulet': amulet
               }

    return render(request, 'cards/card.html', context)


def view_user_cards_for_sale(request: HttpRequest, user_id: int) -> HttpResponse:
    """ Просмотр продаваемых карт пользователя """

    owner = get_object_or_404(User, pk=user_id)
    cards = Card.objects.filter(owner=user_id, sale_status=True)
    context = {'title': 'Продаются',
               'header': 'Продаются',
               'cards': cards,
               'owner': owner,
               }

    return render(request, 'cards/view_sale_card_user.html', context)


@auth_required(error_message='Для покупки необходимо авторизоваться!', redirect_url_name='view_all_sale_card')
def buy_card_user(request: HttpRequest, card_id: int) -> HttpResponseRedirect:
    """ Покупка карты на торговой площадке.
        Обрабатывает только POST запросы.
        Вызывает сервис для покупки.
        При успехе направляет на страницу просмотра карты с сообщением об успехе.
        При ошибке направляет на домашнюю страницу с сообщением об ошибке.
    """

    if request.method == 'POST':
        purchase_answer: dict = transfer_card_to_user(card_id, request.user.id)
        if purchase_answer.get('error_message'):
            messages.error(request, purchase_answer['error_message'])
            return HttpResponseRedirect(reverse('view_all_sale_card'))
        else:
            messages.success(request, purchase_answer['success_message'])
            return HttpResponseRedirect(reverse('card', kwargs={'card_id': card_id}))
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


@auth_required(redirect_url_name='card_store')
def card_sale(request: HttpRequest, card_id: int) -> HttpResponseRedirect | HttpResponse:
    """ Выставление на продажу карты.
        При GET запросе выводит форму для установки цены.
        При POST запросе вызывает сервис для выставления на продажу карты.
        При ошибке направляет на домашнюю страницу с сообщением об ошибке.
        При успехе направляет на страницу карт пользователя.
        При других запросах направляет на стартовую страницу.
    """

    card = get_object_or_404(Card, pk=card_id)
    if request.method == 'POST':
        sale_card_form = SaleCardForm(request.POST)
        if sale_card_form.is_valid():
            price = sale_card_form.cleaned_data['price']
            answer: dict = card_sale_service(request.user.id, card_id, price)
            if answer.get('error_message'):
                messages.error(request, answer['error_message'])
                return HttpResponseRedirect(reverse('home'))
            else:
                messages.success(request, answer['success_message'])
                return HttpResponseRedirect(reverse('user_cards', kwargs={'user_id': request.user.id}))
        else:
            context = {'form': sale_card_form,
                       'title': 'Выставление на продажу',
                       'header': 'Выставление на продажу',
                       'card': card,
                       }
            return render(request, 'cards/sale_card.html', context)

    elif request.method == 'GET':
        sale_card_form = SaleCardForm(instance=card, initial={'price': 1})
        context = {'form': sale_card_form,
                   'title': 'Выставление на продажу',
                   'header': 'Выставление на продажу',
                   'card': card,
                   }

        return render(request, 'cards/sale_card.html', context)
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


def remove_from_sale_card(request: HttpRequest, card_id: int) -> HttpResponseRedirect:
    """ Удаление карты из торговой площадки.
        Обрабатывает только POST запросы.
        Вызывает сервис по удаления карты из торговой площадки.
        При ошибке направляет на домашнюю страницу.
        При успехе направляет на страницу карт пользователя.
    """

    if request.method == 'POST':
        answer: dict = remove_from_sale_card_service(request.user.id, card_id)
        if answer.get('error_message'):
            messages.error(request, answer['error_message'])
            return HttpResponseRedirect(reverse('home'))
        else:
            messages.success(request, answer['success_message'])
            return HttpResponseRedirect(reverse('user_cards', kwargs={'user_id': request.user.id}))
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


@auth_required()
def card_level_up(request: HttpRequest, card_id: int) -> HttpResponse:
    """ Меню увеличение уровня """

    card = get_object_or_404(Card, pk=card_id)
    if request.user != card.owner:
        messages.error(request, 'Вы не можете усиливать эту карту!')
        return HttpResponseRedirect(reverse('home'))

    need_exp = calculate_need_exp(card.level)

    inventory = UsersInventory.objects.filter(owner=request.user)
    context = {'title': 'Улучшение карты',
               'header': f'Улучшение карты {card_id}',
               'card': card,
               'inventory': inventory,
               'need_exp': need_exp
               }

    return render(request, 'cards/card_level_up.html', context)


@auth_required()
def level_up_with_item(request: HttpRequest, card_id: int, item_id: int) -> HttpResponseRedirect | HttpResponse:
    """ Увеличение уровня карты с помощью книг опыта.
        При GET запросе показывает форму с количеством книг.
        При POST запросе и валидных данных вызывает сервис увеличения уровня.
        При ошибке направляет на домашнюю страницу с сообщением об ошибке.
        При успехе направляет на страницу меню увеличения уровня этой карты.
        При других запросах направляет на домашнюю страницу с сообщением об ошибке.
    """

    card = get_object_or_404(Card, pk=card_id)
    need_exp = calculate_need_exp(card.level)
    item = get_object_or_404(UsersInventory, pk=item_id)

    if request.method == 'POST':
        user_item_form = UseItemForm(request.POST)
        if user_item_form.is_valid():
            amount_item = user_item_form.cleaned_data['amount']
            answer: dict = level_up_with_item_service(request.user.id, card_id, item_id, amount_item)

            # Если доступ есть, но не хватает ресурсов
            if answer.get('error_message') and answer.get('show_form'):
                messages.error(request, answer['error_message'])
                context = {'form': user_item_form,
                           'title': 'Улучшение карты',
                           'header': f'Улучшение карты {card_id} с помощью предмета {item_id}',
                           'card': card,
                           'need_exp': need_exp,
                           'item': item
                           }
                return render(request, 'cards/card_level_up_with_item.html', context)

            # Если нет доступа или карта максимального уровня
            elif answer.get('error_message'):
                messages.error(request, answer['error_message'])
                return HttpResponseRedirect(reverse('home'))

            else:
                # Все прошло успешно
                return HttpResponseRedirect(reverse('level_up', kwargs={'card_id': card.id}))
        else:
            context = {'title': 'Улучшение карты',
                       'header': f'Улучшение карты {card_id} с помощью предмета {item_id}',
                       'form': user_item_form,
                       'card': card,
                       'need_exp': need_exp,
                       'item': item
                       }
            messages.error(request, 'Введены неверные данные!')

            return render(request, 'cards/card_level_up_with_item.html', context)

    elif request.method == "GET":
        form = UseItemForm(initial={'amount': 1})
        context = {'title': 'Улучшение карты',
                   'header': f'Улучшение карты {card_id} с помощью предмета {item_id}',
                   'form': form,
                   'card': card,
                   'need_exp': need_exp,
                   'item': item
                   }

        return render(request, 'cards/card_level_up_with_item.html', context)
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


def view_all_sale_card(request: HttpRequest) -> HttpResponse:
    """ Вывод всех продаваемых карт на торговой площадке"""

    if request.user.is_authenticated:
        sale_cards = Card.objects.exclude(Q(sale_status=False) | Q(owner=request.user))
    else:
        sale_cards = Card.objects.filter(sale_status=True)

    context = {'title': 'Торговая площадка',
               'header': 'Торговая площадка',
               'cards': sale_cards,
               }

    return render(request, 'cards/all_sale_card.html', context)


@auth_required()
def merge_card_menu(request: HttpRequest, current_card_id: int) -> HttpResponseRedirect:
    """ Меню слияния карты.
        Выводит карты, которые можно слить в выбранную карту.
        В выборку не входят карты, которые участвуют в боевом событии.
    """

    current_card = get_object_or_404(Card, pk=current_card_id)

    if current_card.owner != request.user:
        messages.error(request, 'Вы не являетесь владельцем карты')
        return HttpResponseRedirect(reverse('home'))

    team_card_pks = BattleEventParticipants.objects.filter(user=request.user.id).values_list('first_card__pk',
                                                                                             'second_card__pk',
                                                                                             'third_card__pk').last()

    cards_for_merge = Card.objects.filter(owner=request.user,
                                          class_card=current_card.class_card,
                                          type=current_card.type,
                                          rarity=current_card.rarity).exclude(pk=current_card_id)
    # исключая карты, которые в отряде боевого события
    cards_for_merge = cards_for_merge.exclude(pk__in=team_card_pks)

    context = {'title': 'Слияние карты',
               'header': 'Слияние карты',
               'current_card': current_card,
               'cards_for_merge': cards_for_merge
               }

    return render(request, 'cards/merge_menu_card.html', context)


@auth_required()
def merge_card(request: HttpRequest, current_card_id: int, card_for_merge_id: int) -> HttpResponseRedirect:
    """ Слияние карты.
        Обрабатывает только POST запросы.
        Вызывает сервис слияния карты.
        При успехе направляет на страницу меню слияния с сообщением об успехе.
        При ошибке направляет на домашнюю страницу с сообщением об ошибке.
    """

    if request.method == 'POST':
        answer_card_merge: dict = merge_user_card(current_card_id, card_for_merge_id, request.user.id)
        if answer_card_merge.get('error_message'):
            messages.error(request, answer_card_merge['error_message'])
            return HttpResponseRedirect(reverse('home'))
        else:
            messages.success(request, answer_card_merge['success_message'])
            return HttpResponseRedirect(reverse('merge_card_menu', kwargs={'current_card_id': current_card_id}))
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))
