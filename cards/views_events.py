from datetime import date

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from .services_events import (BattleEventData, FightBattleEventData, FightData, get_news_with_pagination,
                              get_info_start_event, get_info_battle_event, set_card_in_template_team,
                              fight_battle_event, fight_users, get_user_award_start_event,
                              select_favorite_card_service)
from .models import Card

from common.decorators import auth_required
from exchange.models import TeamsForBattleEvent


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
    """ Меню установки карты для участия в боевом событии.
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
                   'user': request.user,
                   'enemy': answer_fight.enemy
                   }
        return render(request, 'cards/fight.html', context)


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
