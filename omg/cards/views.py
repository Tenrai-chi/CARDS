from datetime import date
from math import ceil

from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .forms import SaleCardForm, UseItemForm
from .services import (StartEventData, BattleEventData, FightBattleEventData, FightData,
                       get_cards_with_pagination, get_news_with_pagination, get_info_start_event,
                       create_free_card, get_info_battle_event, set_card_in_template_team, purchase_card,
                       fight_battle_event, fight_users, transfer_card_to_user, get_user_award_start_event,
                       merge_user_card)
from .models import Card, Rarity, CardStore
from .utils import accrue_experience, calculate_need_exp

from common.decorators import auth_required
from common.utils import date_time_now, time_difference_check, create_new_card
from exchange.models import (UsersInventory, AmuletItem, BattleEventParticipants,
                             TeamsForBattleEvent)
from users.models import Transactions, Profile


def view_cards(request: HttpRequest) -> HttpResponse:
    """ Вывод всех существующих карт """

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
        battle_event: Информация о боевом событии в зависимости от текущего дня месяца
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
        start_event_data: StartEventData = get_info_start_event(request.user.id)
        context['user_profile'] = start_event_data.user_profile
        context['event_awards'] = start_event_data.event_awards
        context['show_button'] = start_event_data.show_button
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
    """ Установка карты в команду боевого события """

    answer: dict = set_card_in_template_team(request.user.id, place, current_card_id)
    if answer.get('error_message'):
        messages.error(request, answer['error_message'])
    return HttpResponseRedirect(f'/battle_event')


@auth_required()
def fight_day_battle_event(request: HttpRequest, enemy_id: int) -> HttpResponseRedirect:
    """ Вывод итога боя.
        Начисление очков события.
        Ставится отметка о прошедшем бое.
    """

    fight_result_data: FightBattleEventData = fight_battle_event(request.user.id, enemy_id)
    if fight_result_data.error_message:
        messages.error(request, fight_result_data.error_message)
        return HttpResponseRedirect(reverse('home'))
    else:
        context = {'all_results': fight_result_data.result_fight,
                   'add_points': fight_result_data.add_points}

        return render(request, 'cards/battle_event_fight.html', context)


@auth_required(error_message='Для покупки необходимо авторизоваться!', redirect_url_name='card_store')
def buy_card(request: HttpRequest, card_id: int) -> HttpResponseRedirect:
    """ Покупка карты в магазине """

    answer_purchase_card: dict = purchase_card(request.user.id, card_id)
    if answer_purchase_card.get('error_message'):
        messages.error(request, answer_purchase_card['error_message'])
        return HttpResponseRedirect(reverse('card_store'))
    else:
        new_card_id = answer_purchase_card.get('new_card_id')
        messages.success(request, 'Вы успешно совершили покупку!')
        return HttpResponseRedirect(f'/cards/card-{new_card_id}')


def get_card(request: HttpRequest) -> HttpResponse:
    """ Страница получения бесплатно карты """

    rarity_chance_drop = Rarity.objects.values('name', 'drop_chance')
    if not request.user.is_authenticated:
        context = {'title': 'Получить карту', 'header': 'Получить бесплатную карту',
                   'rarity_chance_drop': rarity_chance_drop}
        return render(request, 'cards/get_card.html', context)

    user_profile = Profile.objects.get(user=request.user)
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
    """ Генерация новой карты при получении ее пользователем бесплатно.
        При ошибке получает сообщение об ошибке и перенаправляет пользователя на нужную страницу.
        При успешном создании перенаправляет пользователя на страницу просмотра созданной карты.
    """

    answer_create_free_card: dict = create_free_card(request.user.id)
    if answer_create_free_card.get('error'):
        messages.error(request, answer_create_free_card['message_error'])
        return HttpResponseRedirect(reverse(answer_create_free_card['return_name']))
    else:
        new_card_id = answer_create_free_card['new_card_id']
        return HttpResponseRedirect(f'/cards/card-{new_card_id}')


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
    max_count_cards = Profile.objects.get(pk=user_id).card_slots

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
    """ Выбор избранной карты.
        Изменение current_card в Profile пользователя на выбранную карту.
    """

    card = Card.objects.get(pk=selected_card_id)
    user_profile = Profile.objects.get(user=request.user)
    user_profile.current_card = card
    user_profile.save()

    return HttpResponseRedirect(f'/cards/user_cards-{request.user.id}')


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
    """ Обработка покупки карты у пользователя """

    purchase_answer: dict = transfer_card_to_user(card_id, request.user.id)
    if purchase_answer.get('error_message'):
        messages.error(request, purchase_answer['error_message'])
        return HttpResponseRedirect(reverse('view_all_sale_card'))
    else:
        messages.success(request, purchase_answer['success_message'])
        return HttpResponseRedirect(f'/cards/card-{card_id}')


@auth_required(redirect_url_name='card_store')
def card_sale(request: HttpRequest, card_id: int) -> HttpResponseRedirect | HttpResponse:
    """ Выставление на продажу карты.
        С помощью формы задается цена карты, sale_status устанавливается на True автоматически.
    """

    card = get_object_or_404(Card, pk=card_id)
    if request.user != card.owner:
        messages.error(request, 'Вы не можете выставить на продажу чужую карту!')
        return HttpResponseRedirect(reverse('home'))

    team_card_pks = BattleEventParticipants.objects.filter(user=request.user).values_list('first_card__pk',
                                                                                          'second_card__pk',
                                                                                          'third_card__pk').last()

    if card.id in team_card_pks:
        messages.error(request, 'Вы не можете выставить на продажу эту карту! Карта в отряде боевого события')
        return HttpResponseRedirect(reverse('home'))

    if request.method == 'POST':
        sale_card_form = SaleCardForm(request.POST, instance=card)
        if sale_card_form.is_valid():
            edit_card_status = sale_card_form.save(commit=False)
            edit_card_status.sale_status = True
            edit_card_status.save()

            return HttpResponseRedirect(f'/cards/user_cards-{card.owner.id}')
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
    """ Убрать карту из продажи.
        Устанавливает sale_status карты на False.
        Цену карты устанавливает на None.
    """

    card = Card.objects.get(pk=card_id)
    if request.user == card.owner:
        card.sale_status = False
        card.price = None
        card.save()

        messages.success(request, 'Вы успешно убрали карту с продажи')
        return HttpResponseRedirect(f'/cards/user_cards-{card.owner.id}/')
    else:
        messages.error(request, 'Вы не можете убрать с продажи эту карту!')
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
    """ Увеличение уровня с помощью книг опыта.
        Если у пользователя хватает денег для использования предметов,
        то увеличивает опыт карты, и изменяет ее уровень, если необходимо.
        Использует только необходимое количество книг опыта.
        В Profile пользователя уменьшается gold.
        Создается транзакция.
    """

    card = get_object_or_404(Card, pk=card_id)
    if request.user != card.owner:
        messages.error(request, 'Вы не можете усиливать эту карту!')
        return HttpResponseRedirect(reverse('home'))

    if card.level >= card.rarity.max_level:
        messages.error(request, 'Эту карту больше нельзя улучшить!')
        return HttpResponseRedirect(reverse('home'))

    item = get_object_or_404(UsersInventory, pk=item_id)
    need_exp = calculate_need_exp(card.level)
    if request.method == 'POST':
        form = UseItemForm(request.POST)
        if form.is_valid():
            profile = Profile.objects.get(user=request.user)
            inventory_change = form.save(commit=False)
            if profile.gold < inventory_change.amount * item.item.gold_for_use:
                messages.error(request, 'Вам не хватает денег!')
                context = {'form': form,
                           'title': 'Улучшение карты',
                           'header': f'Улучшение карты {card_id} с помощью предмета {item_id}',
                           'card': card,
                           'need_exp': need_exp,
                           'item': item
                           }

                return render(request, 'cards/card_level_up_with_item.html', context)

            if item.amount < inventory_change.amount:
                messages.error(request, 'У вас нет столько предметов!')
                context = {'form': form,
                           'title': 'Улучшение карты',
                           'header': f'Улучшение карты {card_id} с помощью предмета {item_id}',
                           'card': card,
                           'need_exp': need_exp,
                           'item': item
                           }

                return render(request, 'cards/card_level_up_with_item.html', context)

            accrued_experience = inventory_change.amount * item.item.experience_amount
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

            # Проверка на бафф гильдиии
            if profile.guild.buff.name == 'Пытливый ум':
                expended_items = ceil((expended_experience / item.item.experience_amount) * 0.8)
            else:
                expended_items = ceil(expended_experience / item.item.experience_amount)
            transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                      user=request.user,
                                                      before=profile.gold,
                                                      after=profile.gold-expended_items*item.item.gold_for_use,
                                                      comment='Улучшение карты'
                                                      )
            transaction.save()
            profile.gold -= expended_items * item.item.gold_for_use
            item.amount -= expended_items

            profile.save()
            item.save()
            card.save()

            return HttpResponseRedirect(f'/cards/card-{card.id}/level_up/')
        else:
            context = {'title': 'Улучшение карты',
                       'header': f'Улучшение карты {card_id} с помощью предмета {item_id}',
                       'form': form,
                       'card': card,
                       'need_exp': need_exp,
                       'item': item
                       }
            messages.error(request, 'Какая-то ошибка!')

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
    """ Процесс получения награды за стартовое событие и перенаправление на стартовую страницу """

    answer: dict = get_user_award_start_event(request.user.id)
    if answer.get('error_message'):
        messages.error(request, answer['error_message'])
        return HttpResponseRedirect(reverse('home'))
    elif answer.get('card_id'):
        messages.success(request, answer['success_message'])
        return HttpResponseRedirect(f'/cards/card-{answer["card_id"]}')
    else:
        messages.success(request, answer['success_message'])
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

    team_card_pks = BattleEventParticipants.objects.filter(user=request.user).values_list('first_card__pk',
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
    """ Слияние карты """

    answer_card_merge: dict = merge_user_card(current_card_id, card_for_merge_id, request.user.id)
    if answer_card_merge.get('error_message'):
        messages.error(request, answer_card_merge['error_message'])
        return HttpResponseRedirect(reverse('home'))
    else:
        messages.success(request, answer_card_merge['success_message'])
        return HttpResponseRedirect(f'/cards/card-{current_card_id}/merge_menu')
