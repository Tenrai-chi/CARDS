from random import choice
from datetime import datetime
from math import ceil
from random import randint

from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .forms import SaleCardForm, UseItemForm
from .models import Card, Rarity, CardStore, HistoryReceivingCards, FightHistory, Type, ClassCard
from .utils import accrue_experience, calculate_need_exp, fight_now as f_n

from common.utils import date_time_now, time_difference_check, create_new_card
from exchange.models import SaleUserCards, UsersInventory, ExperienceItems, AmuletItem, AmuletType, InitialEventAwards
from users.models import Transactions, Profile, SaleStoreCards


def view_cards(request: HttpRequest) -> HttpResponse:
    """ Вывод всех существующих карт """

    cards = Card.objects.all().order_by('-pk')
    paginator = Paginator(cards, 21)
    if 'page' in request.GET:
        page_num = request.GET['page']
    else:
        page_num = 1
    page = paginator.get_page(page_num)
    context = {'cards': page.object_list,
               'title': 'Просмотр карт',
               'header': 'Все карты',
               'page': page
               }

    return render(request, 'cards/view_cards.html', context)


def home(request: HttpRequest) -> HttpResponse:
    """ Домашняя пустая страница.
        Если пользователь не получил награды начального ивента,
        то выводится таблица наград.
        Если отметки в этот день нет, то помимо таблицы выводится кнопка 'отметиться'.
    """

    context = {'title': 'Домашняя',
               'header': 'Стартовая страница',
               'button': False
               }

    if request.user.is_authenticated:
        user_profile = Profile.objects.get(user=request.user)
        event_awards = InitialEventAwards.objects.all().order_by('id')
        if user_profile.date_event_visit is None or user_profile.date_event_visit < datetime.now().date():
            context['button'] = True

        context['user_profile'] = user_profile
        context['event_awards'] = event_awards

    return render(request, 'cards/home.html', context)


def buy_card(request: HttpRequest, card_id: int) -> HttpResponseRedirect:
    """ Покупка карты в магазине.
        Создает карту по шаблону выбранной карты в магазине и присваивает ее текущему пользователю.
        У текущего пользователя в Profile изменяется gold на значение равное цене карты.
    """

    if request.user.is_authenticated:
        user_profile = Profile.objects.get(user=request.user)
        selected_card = CardStore.objects.get(pk=card_id)

        if user_profile.gold < selected_card.price:
            messages.error(request, 'У вас не хватает средств для покупки!')

            return HttpResponseRedirect(reverse('card_store'))

        elif Card.objects.filter(owner=request.user.id).count() == user_profile.card_slots:
            messages.error(request, 'У вас не хватает места для покупки новой карты!')

            return HttpResponseRedirect(reverse('card_store'))

        else:
            transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                      user=request.user,
                                                      before=user_profile.gold,
                                                      after=user_profile.gold-selected_card.price,
                                                      comment='Покупка в магазине карт'
                                                      )

            user_profile.gold -= selected_card.price
            user_profile.save()

            sale_card = SaleStoreCards.objects.create(date_and_time=date_time_now(),
                                                      sold_card=selected_card,
                                                      transaction=transaction
                                                      )
            sale_card.save()

            new_card = Card.objects.create(owner=request.user,
                                           level=1,
                                           class_card=selected_card.class_card,
                                           type=selected_card.type,
                                           rarity=selected_card.rarity,
                                           hp=selected_card.hp,
                                           damage=selected_card.damage
                                           )

            new_record = HistoryReceivingCards.objects.create(date_and_time=date_time_now(),
                                                              method_receiving='Покупка в магазине',
                                                              card=new_card,
                                                              user=request.user
                                                              )
            new_record.save()

            messages.success(request, 'Вы успешно совершили покупку!')

            return HttpResponseRedirect(f'/cards/card-{new_card.id}')

    else:
        messages.error(request, 'Для покупки необходимо авторизироваться!')

        return HttpResponseRedirect(reverse('card_store'))


def get_card(request: HttpRequest) -> HttpResponse:
    """ Получение бесплатной карты.
        Проверка последнего получения бесплатной карты пользователем,
        если прошло более 6 часов с момента получения или регистрации,
        то перенаправляет на страницу создания новой карты.
    """

    if not request.user.is_authenticated:
        context = {'title': 'Получить карту', 'header': 'Получить бесплатную карту'}

        return render(request, 'cards/get_card.html', context)

    user_profile = Profile.objects.get(user=request.user)
    take_card, hours = time_difference_check(user_profile.receiving_timer, 6)
    rarity_chance_drop = Rarity.objects.values('name', 'drop_chance')

    context = {'title': 'Получить карту',
               'header': 'Получить бесплатную карту',
               'rarity_chance_drop': rarity_chance_drop,
               'user_profile': user_profile,
               'take_card': take_card,
               'hours': 6 - hours
               }

    return render(request, 'cards/get_card.html', context)


def create_card(request: HttpRequest) -> HttpResponseRedirect:
    """ Генерация новой карты при получении ее пользователем бесплатно.
        Обновляет receiving_timer профиля.
        После создания перенаправляет пользователя на страницу просмотра созданной карты.
    """

    if not request.user.is_authenticated:
        messages.error(request, 'Чтобы получить бесплатную карту необходимо авторизироваться')

        return HttpResponseRedirect(reverse('home'))

    if Card.objects.filter(owner=request.user.id).count() == request.user.profile.card_slots:
        messages.error(request, 'У вас не хватает места для получения новой карты!')

        return HttpResponseRedirect(reverse('card_store'))

    user_profile = Profile.objects.get(user=request.user)
    take_card, hours = time_difference_check(user_profile.receiving_timer, 6)

    if take_card:
        new_card = create_new_card(user=request.user)

        new_record = HistoryReceivingCards.objects.create(date_and_time=date_time_now(),
                                                          method_receiving='Бесплатная генерация',
                                                          card=new_card,
                                                          user=request.user
                                                          )
        new_record.save()

        user_profile.update_receiving_timer()

        return HttpResponseRedirect(f'/cards/card-{new_card.id}')

    else:
        messages.error(request, 'Вы пока не можете получить бесплатную карту')

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

    user = User.objects.get(pk=user_id)

    cards = Card.objects.filter(owner=user).order_by('rarity', 'class_card', 'id')
    count_cards = Card.objects.filter(owner=user).count()
    max_count_cards = Profile.objects.get(pk=user_id).card_slots

    context = {'title': 'Карты пользователя',
               'header': f'Карты пользователя {user.username}',
               'cards': cards,
               'user_info': user,
               'count_cards': count_cards,
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


def select_favorite_card(request: HttpRequest, selected_card_id: int) -> HttpResponseRedirect:
    """ Выбор избранной карты.
        Изменение current_card в Profile пользователя на выбранную карту.
    """

    card = Card.objects.get(pk=selected_card_id)
    user_profile = Profile.objects.get(user=request.user)
    user_profile.current_card = card
    user_profile.save()

    return HttpResponseRedirect(f'/cards/user_cards-{request.user.id}')


def fight(request: HttpRequest, protector_id: int) -> HttpResponseRedirect | HttpResponse:
    """ Бой.
        Проверяет есть ли у обоих пользователей выбранная карта.
        Проверяет время последнего боя между двумя пользователями. Если прошло больше 6 часов, происходит битва.
        После битвы начисляются опыт в experience_bar карт.
        Если опыта достаточно, то увеличивается уровень карты и ее характеристики.
        В Profile пользователей увеличиваются gold, win, lose в зависимости от победителя.
        В Transactions появляются записи о начислении денег за победу и проигрыш.
        Создается новая запись в FightHistory.
        Обрабатывается возможность получения книг опыта нападавшему,
        если прокнул шанс, то книги появляются в инвентаре.
    """

    if request.user.is_authenticated:
        protector = User.objects.get(pk=protector_id)
        attacker = User.objects.get(pk=request.user.id)

        # Проверка не один и тот же это человек
        if protector == attacker:
            messages.error(request, 'Для боя необходимо выбрать противника!')

            return HttpResponseRedirect(reverse('home'))

        last_fight = FightHistory.objects.filter(Q(winner=protector, loser=attacker) | Q(winner=attacker, loser=protector)).order_by('-id').first()

        # Проверка есть ли в истории боев бой между этими пользователями
        if last_fight is not None:
            can_fight, hours = time_difference_check(last_fight.date_and_time, 6)

            # Если бой есть и прошло менее 6 часов, то нельзя
            if not can_fight:
                messages.error(request, f'Вы пока не можете бросить вызов этому пользователю! Осталось времени: {6-hours} часов')

                return HttpResponseRedirect(reverse('home'))

        if protector.profile.current_card is None or protector.profile.current_card is None:
            messages.error(request, 'Для боя необходимо чтобы у обоих соперников были выбраны карты')

            return HttpResponseRedirect(reverse('home'))

        #  Если все проверки пройдены, идет битва, где определяются победитель и проигравший, записывается история боя
        winner, loser, history_fight = f_n(attacker, protector)

        old_winner_gold = winner.profile.gold
        old_loser_gold = loser.profile.gold

        # Начисление золота (вынести)
        if winner.profile.guild and winner.profile.guild.buff.name == 'Бандитский улов':
            winner.profile.get_gold(200)

        else:
            winner.profile.get_gold(100)

        loser.profile.get_gold(25)

        transaction_winner = Transactions.objects.create(date_and_time=date_time_now(),
                                                         user=winner,
                                                         before=old_winner_gold,
                                                         after=winner.profile.gold,
                                                         comment='Награда за победу в битве'
                                                         )
        transaction_winner.save()
        transaction_loser = Transactions.objects.create(date_and_time=date_time_now(),
                                                        user=loser,
                                                        before=old_loser_gold,
                                                        after=loser.profile.gold,
                                                        comment='Награда за проигрыш в битве'
                                                        )
        transaction_loser.save()

        # Начисление опыта, если не достигнут максимальный уровень карты (вынести)
        if winner.profile.current_card.level < winner.profile.current_card.rarity.max_level:
            winner.profile.current_card.experience_bar += 75
        if loser.profile.current_card.level < loser.profile.current_card.rarity.max_level:
            loser.profile.current_card.experience_bar += 25

        # Увеличение уровня карты победителя при достижении определенного опыта (вынести)
        if winner.profile.current_card.experience_bar >= calculate_need_exp(winner.profile.current_card.level):
            winner.profile.current_card.experience_bar -= calculate_need_exp(winner.profile.current_card.level)
            winner.profile.current_card.level += 1

            # Если достигнут максимальный уровень, прогресс опыта обнуляется
            if winner.profile.current_card.level == winner.profile.current_card.rarity.max_level:
                winner.profile.current_card.experience_bar = 0

            # Увеличение характеристик карты победителя (вынести)
            winner.profile.current_card.increase_stats()

        # Увеличение уровня карты проигравшего при достижении определенного опыта (вынести)
        if loser.profile.current_card.experience_bar >= calculate_need_exp(loser.profile.current_card.level):
            loser.profile.current_card.experience_bar -= calculate_need_exp(loser.profile.current_card.level)
            loser.profile.current_card.level += 1

            # Если достигнут максимальный уровень, прогресс опыта обнуляется
            if loser.profile.current_card.level == loser.profile.current_card.rarity.max_level:
                loser.profile.current_card.experience_bar = 0

            # Увеличение характеристик карты проигравшего (вынести)
            loser.profile.current_card.increase_stats()

        winner.profile.win += 1
        loser.profile.lose += 1

        if winner.profile.guild is not None:
            winner.profile.get_guild_point('win')

        if loser.profile.guild is not None:
            loser.profile.get_guild_point('lose')

        winner.profile.save()
        loser.profile.save()

        winner.profile.current_card.save()
        loser.profile.current_card.save()

        new_record = FightHistory.objects.create(date_and_time=date_time_now(),
                                                 winner=winner,
                                                 loser=loser,
                                                 card_winner=winner.profile.current_card,
                                                 card_loser=loser.profile.current_card
                                                 )
        new_record.save()

        # Предметы падают только нападавшему
        items = ExperienceItems.objects.all()
        amulets = AmuletType.objects.exclude(rarity__chance_drop_on_fight=0)
        reward_item_user = []
        reward_amulet_user = []
        for item in items:  # Проверка выпадения предмета
            chance = randint(1, 100)

            # Использование способности эльфа
            if attacker.profile.current_card.class_card.name == 'Эльф':
                chance_drop = item.chance_drop_on_fight + (attacker.profile.current_card.class_card.numeric_value + 4 * attacker.profile.current_card.merger)
            else:
                chance_drop = item.chance_drop_on_fight

            if chance <= chance_drop:
                try:
                    items_user = UsersInventory.objects.get(owner=request.user,
                                                            item=item)
                    items_user.amount += 1
                    items_user.save()
                    reward_item_user.append(item)
                except UsersInventory.DoesNotExist:
                    new_record_inventory = UsersInventory.objects.create(owner=request.user,
                                                                         item=item,
                                                                         amount=1
                                                                         )
                    new_record_inventory.save()
                    reward_item_user.append(item)
        if request.user.profile.amulet_slots > AmuletItem.objects.filter(owner=request.user.id).count():
            for amulet in amulets:  # Проверка выпадения амулета

                # Использование способности эльфа
                if attacker.profile.current_card.class_card.name == 'Эльф':
                    chance_drop = amulet.rarity.chance_drop_on_fight + attacker.profile.current_card.class_card.numeric_value
                else:
                    chance_drop = amulet.rarity.chance_drop_on_fight

                chance = randint(1, 100)
                if chance <= chance_drop:
                    new_amulet = AmuletItem.objects.create(amulet_type=amulet,
                                                           owner=attacker)
                    new_amulet.save()
                    reward_amulet_user.append(amulet)

        context = {'title': 'Битва',
                   'header': f'Итог битвы между {attacker.username} и {protector.username}!',
                   'winner': winner,
                   'loser': loser,
                   'reward_item_user': reward_item_user,
                   'reward_amulet_user': reward_amulet_user,
                   'history_fight': history_fight
                   }

        return render(request, 'cards/fight.html', context)

    else:
        messages.error(request, 'Для боя необходимо авторизироваться!')

        return HttpResponseRedirect(reverse('home'))


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


def buy_card_user(request: HttpRequest, card_id: int) -> HttpResponseRedirect:
    """ Покупка карты у пользователя.
        Изменение владельца карты на текущего пользователя.
        Увеличение/уменьшение gold у покупателя/продавца.
        Создание 2 записей в Transaction.
    """

    if request.user.is_authenticated:
        buyer_profile = Profile.objects.get(user=request.user.pk)
        card = Card.objects.get(pk=card_id)

        if request.user.profile.card_slots <= Card.objects.filter(owner=request.user.id).count():
            messages.error(request, 'У вас не хватает места для покупки новой карты!')

            return HttpResponseRedirect(reverse('view_all_sale_card'))

        if buyer_profile.gold < card.price:
            messages.error(request, 'У вас не хватает средств для покупки!')

            return HttpResponseRedirect(f'/cards/user_cards-{card.owner.id}/sale')
        else:
            transaction1 = Transactions.objects.create(date_and_time=date_time_now(),
                                                       user=request.user,
                                                       before=buyer_profile.gold,
                                                       after=buyer_profile.gold-card.price,
                                                       comment='Покупка карты у пользователя'
                                                       )
            buyer_profile.gold = buyer_profile.gold - card.price
            buyer_profile.save()

            salesman_profile = Profile.objects.get(user=card.owner)
            transaction2 = Transactions.objects.create(date_and_time=date_time_now(),
                                                       user=card.owner,
                                                       before=salesman_profile.gold,
                                                       after=salesman_profile.gold + card.price,
                                                       comment='Продажа карты пользователю'
                                                       )
            salesman_profile.gold = salesman_profile.gold + card.price
            salesman_profile.save()

            sale_user_card = SaleUserCards.objects.create(date_and_time=date_time_now(),
                                                          buyer=buyer_profile.user,
                                                          salesman=salesman_profile.user,
                                                          card=card,
                                                          price=card.price,
                                                          transaction_buyer=transaction1,
                                                          transaction_salesman=transaction2
                                                          )
            sale_user_card.save()

            card.owner = request.user
            card.price = 0
            card.sale_status = False
            card.save()

            amulet = AmuletItem.objects.filter(card=card).last()
            if amulet:
                amulet.card = None
                amulet.save()

            if card == salesman_profile.current_card:
                salesman_profile.current_card = None
                salesman_profile.save()

            messages.success(request, 'Вы успешно совершили покупку!')

            return HttpResponseRedirect(f'/cards/card-{card.id}')

    else:
        messages.error(request, 'Для покупки необходимо авторизироваться!')

        return HttpResponseRedirect(reverse('card_store'))


def card_sale(request: HttpRequest, card_id: int) -> HttpResponseRedirect | HttpResponse:
    """ Выставление на продажу карты.
        С помощью формы задается цена карты, sale_status устанавливается на True автоматически.
    """

    card = Card.objects.get(pk=card_id)
    if request.user == card.owner:
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
        else:
            sale_card_form = SaleCardForm(instance=card, initial={'price': 1})
            context = {'form': sale_card_form,
                       'title': 'Выставление на продажу',
                       'header': 'Выставление на продажу',
                       'card': card,
                       }

            return render(request, 'cards/sale_card.html', context)
    else:
        messages.error(request, 'Вы не можете продать эту карту!')

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

    else:
        form = UseItemForm(initial={'amount': 1})
        context = {'title': 'Улучшение карты',
                   'header': f'Улучшение карты {card_id} с помощью предмета {item_id}',
                   'form': form,
                   'card': card,
                   'need_exp': need_exp,
                   'item': item
                   }

        return render(request, 'cards/card_level_up_with_item.html', context)


def view_all_sale_card(request: HttpRequest) -> HttpResponse:
    """ Вывод всех продаваемых карт """

    if request.user.is_authenticated:
        sale_cards = Card.objects.exclude(Q(sale_status=False) | Q(owner=request.user))
    else:
        sale_cards = Card.objects.filter(sale_status=True)

    context = {'title': 'Торговая площадка',
               'header': 'Торговая площадка',
               'cards': sale_cards,
               }

    return render(request, 'cards/all_sale_card.html', context)


def get_award_start_event(request: HttpRequest):
    """ Получение награды из начального ивента.
        Пользователь получает награду за отметку дня, если она еще не получена.
        Количество совершенных входов пользователя увеличивается.
        Если награда 30 дня (UR карта), то создает ее и присваивает пользователю.
    """

    if request.user.is_authenticated:
        user_profile = Profile.objects.get(user=request.user)
        if user_profile.event_visit >= 30:
            messages.error(request, 'Вы получили все награды из этого ивента)')
            return HttpResponseRedirect(reverse('home'))

        if user_profile.date_event_visit is None or user_profile.date_event_visit < datetime.now().date():

            award = InitialEventAwards.objects.get(day_event_visit=user_profile.event_visit + 1)
            if award.type_award in ['Маленькая книга опыта', 'Средняя книга опыта', 'Большая книга опыта']:
                try:
                    books_user = UsersInventory.objects.get(owner=request.user, item__name=award.type_award)
                    books_user.amount += int(award.amount_or_rarity_award)
                    books_user.save()
                except UsersInventory.DoesNotExist:
                    book = ExperienceItems.objects.get(name=award.type_award)
                    books_user = UsersInventory.objects.create(owner=request.user,
                                                               item=book,
                                                               amount=int(award.amount_or_rarity_award))
                    books_user.save()

                messages.success(request, f'Вы получили награду! {award.type_award} {award.amount_or_rarity_award}')

            elif award.type_award == 'Золото':
                user_profile.get_gold(int(award.amount_or_rarity_award))
                new_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                              user=request.user,
                                                              before=user_profile.gold,
                                                              after=user_profile.gold + int(award.amount_or_rarity_award),
                                                              comment='Награда стартового ивента'
                                                              )
                new_transaction.save()
                messages.success(request, f'Вы получили награду! {award.type_award} {award.amount_or_rarity_award}')

            elif award.type_award == 'Амулет':
                amulet = AmuletType.objects.get(name=award.amount_or_rarity_award)
                user_amulet = AmuletItem.objects.create(owner=request.user, amulet_type=amulet)
                user_amulet.save()
                messages.success(request, f'Вы получили награду! {award.amount_or_rarity_award}')

            elif award.type_award == 'Карта':
                type_card = choice(Type.objects.all())
                class_card = choice(ClassCard.objects.all())
                rarity = Rarity.objects.get(name=award.amount_or_rarity_award)

                user_card = Card.objects.create(owner=request.user,
                                                level=1,
                                                class_card=class_card,
                                                type=type_card,
                                                rarity=rarity,
                                                hp=rarity.max_hp,
                                                damage=rarity.max_damage)
                user_card.save()
                user_profile.add_event_visit()
                messages.success(request, f'Вы получили карту {award.amount_or_rarity_award} с максимальными характеристиками!')
                return HttpResponseRedirect(f'/cards/card-{user_card.id}')

            else:
                messages.error(request, 'Что-то пошло не так... Упс')
                return HttpResponseRedirect(reverse('home'))

            user_profile.add_event_visit()
            return HttpResponseRedirect(reverse('home'))
        else:
            messages.error(request, 'Вы уже получили награду за сегодня')
            return HttpResponseRedirect(reverse('home'))

    else:
        messages.error(request, 'Вы не авторизованы!')
        return HttpResponseRedirect(reverse('home'))


def merge_card_menu(request: HttpRequest, current_card_id: int):
    """ Меню слияния карты.
        Выводит карты, которые можно слить в выбранную карту
    """

    if request.user.is_authenticated:
        current_card = get_object_or_404(Card, pk=current_card_id)

        if current_card.owner != request.user:
            messages.error(request, 'Вы не являетесь владельцем карты')
            return HttpResponseRedirect(reverse('home'))

        cards_for_merge = Card.objects.filter(owner=request.user,
                                              class_card=current_card.class_card,
                                              type=current_card.type,
                                              rarity=current_card.rarity).exclude(pk=current_card_id)

        context = {'title': 'Слияние карты',
                   'header': 'Слияние карты',
                   'current_card': current_card,
                   'cards_for_merge': cards_for_merge
                   }

        return render(request, 'cards/merge_menu_card.html', context)

    else:
        messages.error(request, 'Вы не авторизованы!')
        return HttpResponseRedirect(reverse('home'))


def merge_card(request: HttpRequest, current_card_id: int, card_for_merge_id: int):
    """ Слияние карты.
        Повышает уровень слияния выбранной карты.
        Уничтожает карту, которую слили, перед этим сняв амулет.
        Избранную карту нельзя слить.
    """

    if request.user.is_authenticated:
        if current_card_id == card_for_merge_id:
            messages.error(request, 'Вы не можете слить одну и ту же карту!')
            return HttpResponseRedirect(reverse('home'))

        current_card = get_object_or_404(Card, pk=current_card_id)
        card_for_merge = get_object_or_404(Card, pk=card_for_merge_id)

        if current_card.owner != request.user or card_for_merge.owner != request.user:
            messages.error(request, 'Вы не можете слить эти карты!')
            return HttpResponseRedirect(reverse('home'))

        if current_card.merger >= current_card.max_merger:
            messages.error(request, 'Вы больше не можете использовать слияние для этой карты!')
            return HttpResponseRedirect(reverse('home'))

        if current_card.class_card != card_for_merge.class_card or \
                current_card.type != card_for_merge.type or \
                current_card.rarity != card_for_merge.rarity:
            messages.error(request, 'Вы не можете слить эти карты!')
            return HttpResponseRedirect(reverse('home'))

        current_card.merge()
        card_for_merge.delete()
        messages.success(request, 'Вы успешно выполнили слияние!')
        return HttpResponseRedirect(f'/cards/card-{current_card.id}/merge_menu')

    else:
        messages.error(request, 'Вы не авторизованы!')
        return HttpResponseRedirect(reverse('home'))
