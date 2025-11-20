from datetime import date

from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .forms import SaleCardForm, UseItemForm
from .services import (BattleEventData, FightBattleEventData, FightData,
                       get_cards_with_pagination, get_news_with_pagination, get_info_start_event,
                       create_free_card, get_info_battle_event, set_card_in_template_team, buy_card_service,
                       fight_battle_event, fight_users, transfer_card_to_user, get_user_award_start_event,
                       merge_user_card, card_sale_service, level_up_with_item_service, select_favorite_card_service,
                       remove_from_sale_card_service,)
from .models import Card, Rarity, CardStore
from .utils import calculate_need_exp

from common.decorators import auth_required
from common.utils import time_difference_check
from exchange.models import UsersInventory, AmuletItem, BattleEventParticipants, TeamsForBattleEvent
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


def home(request: HttpRequest, theme: str = 'news') -> HttpResponse:
    """ Домашняя страница.
        Theme: news, battle_event, start_event
        news: все новости с пагинацией
        start_event: награды боевого события и возможность их получения пользователем
        battle_event: Информация о боевом событии в зависимости от текущего дня месяца.
        Вызывает сервисы в зависимости от темы.
    """

    context = {'title': 'Домашняя',
               'header': 'Стартовая страница',
               'theme': None,
               }
    if theme == 'news':
        try:
            page_num = int(request.GET.get('page', 1))
        except ValueError:
            page_num = 1
        news_data: dict = get_news_with_pagination(page_num)

        context['theme'] = 'news'
        context['all_news'] = news_data.get('news')
        context['page'] = news_data.get('page')

        return render(request, 'cards/home_news.html', context)

    if not request.user.is_authenticated:
        messages.info(request, 'Для участия в событиях вы должны быть авторизованы')
        return HttpResponseRedirect(reverse('home'))

    if theme == 'start_event':
        start_event_data: dict = get_info_start_event(request.user.id)
        context['user_profile'] = start_event_data.get('user_profile')
        context['event_awards'] = start_event_data.get('event_awards')
        context['show_button'] = start_event_data.get('show_button')
        context['theme'] = 'start_event'

        return render(request, 'cards/home_start_event.html', context)

    elif theme == 'battle_event':
        today = date.today().day
        context['theme'] = 'battle_event'
        context['day'] = today

        get_info_battle_event_answer: BattleEventData = get_info_battle_event(today, request.user.id)
        # Если идет событие
        if today <= 10:
            if get_info_battle_event_answer.message_info:
                messages.info(request, get_info_battle_event_answer.message_info)
                return HttpResponseRedirect(reverse('home'))

            context['team_user'] = get_info_battle_event_answer.team_user
            context['team_enemy'] = get_info_battle_event_answer.team_enemy
            context['points'] = get_info_battle_event_answer.points
            context['rating'] = get_info_battle_event_answer.rating
            context['enemy_user'] = get_info_battle_event_answer.enemy_user
            context['can_fight'] = get_info_battle_event_answer.can_fight

        # Если событие завершилось
        else:
            context['user_team_template'] = get_info_battle_event_answer.user_team_template
        return render(request, 'cards/home_battle_event.html', context)

    else:
        return HttpResponseRedirect(reverse('home'))


@auth_required()
def menu_team_template_battle_event(request: HttpRequest, place: int) -> HttpResponseRedirect | HttpResponse:
    """ Меню установки карты.
        Выводит все доступные для установки на выбранное место карты,
        исключая уже размещенную
    """

    user_cards = Card.objects.filter(owner=request.user).order_by('rarity')
    team, _ = TeamsForBattleEvent.objects.get_or_create(user=request.user)
    used_card = [team.first_card, team.second_card, team.third_card]
    context = {'title': 'Отряд боевого события',
               'header': 'Настройка отряда боевого события',
               'cards': user_cards,
               'place': place,
               'used': used_card}

    return render(request, 'cards/menu_team_battle_event.html', context)


@auth_required()
def set_team_template_battle_event(request: HttpRequest, place: int, current_card_id: int) -> HttpResponseRedirect:
    """ Установка карты в команду боевого события.
        Обрабатывает только POST запросы.
        Вызывает сервис установки шаблона команды.
        Если при установке возникла ошибка, направляет на домашнюю страницу
        и выводит сообщение пользователю.
    """

    if request.method == 'POST':
        answer: dict = set_card_in_template_team(request.user.id, place, current_card_id)
        if answer.get('error_message'):
            messages.error(request, answer['error_message'])
        return HttpResponseRedirect(reverse('home', kwargs={'theme': 'battle_event'}))
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


@auth_required()
def fight_day_battle_event(request: HttpRequest, enemy_id: int) -> HttpResponseRedirect:
    """ Вывод итога боя.
        Обрабатывает только POST запросы.
        Вызывает сервис битвы боевого события.
        Если битва состоялась, выводит итоги боя.
        Если произошла ошибка направляет на домашнюю страницу с сообщением об ошибке.
    """

    if request.method == 'POST':
        fight_result_data: FightBattleEventData = fight_battle_event(request.user.id, enemy_id)
        if fight_result_data.error_message:
            messages.error(request, fight_result_data.error_message)
            return HttpResponseRedirect(reverse('home'))
        else:
            context = {'all_results': fight_result_data.result_fight,
                       'add_points': fight_result_data.add_points}

            return render(request, 'cards/battle_event_fight.html', context)
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


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

    rarity_chance_drop = Rarity.objects.values('name', 'drop_chance')
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
        if answer_create_free_card.get('error'):
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
    cards = Card.objects.filter(owner=user).order_by('rarity', 'class_card', 'id')
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


@auth_required()
def select_favorite_card(request: HttpRequest, selected_card_id: int) -> HttpResponseRedirect:
    """ Установка избранной карты.
        Обрабатывает только POST запросы.
        Вызывает сервис для установки избранной карты.
        При ошибке направляет на домашнюю страницу.
        При успехе направляет на страницу карт пользователя.
    """

    if request.method == 'POST':
        answer: dict = select_favorite_card_service(request.user.id, selected_card_id)
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
def fight(request: HttpRequest, protector_id: int) -> HttpResponseRedirect | HttpResponse:
    """ Вывод итога рейтингового боя между пользователями """

    answer_fight: FightData = fight_users(request.user.id, protector_id)
    if answer_fight.error_message:
        messages.error(request, answer_fight.error_message)
        return HttpResponseRedirect(reverse('home'))
    else:
        context = {'title': 'Битва',
                   'header': f'Итог битвы между {request.user.username} и {answer_fight.enemy.username}!',
                   'reward_item_user': answer_fight.reward_item_user,
                   'reward_amulet_user': answer_fight.reward_amulet_user,
                   'history_fight': answer_fight.history_fight,
                   'is_victory': answer_fight.is_victory,
                   'winner': answer_fight.winner,
                   'loser': answer_fight.loser,
                   'user': answer_fight.user,
                   'enemy': answer_fight.enemy
                   }
        return render(request, 'cards/fight.html', context)


def view_user_cards_for_sale(request: HttpRequest, user_id: int) -> HttpResponse:
    """ Просмотр продаваемых карт пользователя """

    cards = Card.objects.filter(owner=user_id, sale_status=True)
    owner = User.objects.get(pk=user_id)
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
def get_award_start_event(request: HttpRequest) -> HttpResponseRedirect:
    """ Получение награды стартового события.
        Обрабатывает только POST запросы.
        Вызывает сервис для отметки и получения награды.
        Если наградой была карта, направляет на страницу просмотра полученной карты.
        В остальных ситуациях направляет на стартовую страницу
        с сообщением об успехе или ошибке.
    """

    if request.method == 'POST':
        answer: dict = get_user_award_start_event(request.user.id)
        if answer.get('error_message'):
            messages.error(request, answer['error_message'])
            return HttpResponseRedirect(reverse('home'))
        elif answer.get('card_id'):
            messages.success(request, answer['success_message'])
            return HttpResponseRedirect(reverse('card', kwargs={'card_id': answer['card_id']}))
        else:
            messages.success(request, answer['success_message'])
            return HttpResponseRedirect(reverse('home'))
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


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
