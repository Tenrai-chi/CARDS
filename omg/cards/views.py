from math import ceil
from random import randint

from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .forms import SaleCardForm, UseItemForm
from .models import Card, ClassCard, Type, Rarity, CardStore, HistoryReceivingCards, FightHistory
from .utils import accrue_experience, calculate_need_exp, fight_now as f_n

from common.utils import date_time_now, time_difference_check, create_new_card
from exchange.models import SaleUserCards, UsersInventory, ExperienceItems, AmuletItem, AmuletType
from users.models import Transactions, Profile, SaleStoreCards


def view_cards(request):
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


def home(request):
    """ Домашняя пустая страница.
    """

    context = {'title': 'Домашняя',
               'header': 'Стартовая страница'
               }

    return render(request, 'cards/home.html', context)


def buy_card(request, card_id):
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

            messages.success(request, 'Вы успешно совершили покупку!')

            return HttpResponseRedirect(f'/cards/card-{new_card.id}')

    else:
        messages.error(request, 'Для покупки необходимо авторизироваться!')

        return HttpResponseRedirect(reverse('card_store'))


def get_card(request):
    """ Получение бесплатной карты.
        Проверка последнего получения бесплатной карты пользователем,
        если прошло более 6 часов с момента получения или регистрации,
        то перенаправляет на страницу создания новой карты.
    """

    if  not request.user.is_authenticated:
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


def create_card(request):
    """ Генерация новой карты при получении ее пользователем бесплатно.
        Обновляет receiving_timer профиля.
        После создания перенаправляет пользователя на страницу просмотра созданной карты.
    """

    if not request.user.is_authenticated:
        messages.error(request, 'Чтобы получить бесплатную карту необходимо авторизироваться')

        return HttpResponseRedirect(reverse('home'))

    user_profile = Profile.objects.get(user=request.user)
    take_card, hours = time_difference_check(user_profile.receiving_timer, 6)

    if take_card:
        new_card = create_new_card(user=request.user)

        new_record = HistoryReceivingCards.objects.create(date_and_time=date_time_now(),
                                                          method_receiving='Бесплатная генерация',
                                                          card=new_card,
                                                          user=request.user
                                                          )

        user_profile.update_receiving_timer()

        return HttpResponseRedirect(f'/cards/card-{new_card.id}')

    else:
        messages.error(request, 'Вы пока не можете получить бесплатную карту')

        return HttpResponseRedirect(reverse('home'))



def card_store(request):
    """ Вывод ассортимента магазина карт """

    available_cards = CardStore.objects.filter(sale_now=True).order_by('-rarity')

    context = {'title': 'Магазин карт',
               'header': 'Магазин карт',
               'cards': available_cards
               }

    return render(request, 'cards/card_store.html', context)


def view_user_cards(request, user_id):
    """ Вывод карт выбранного пользователя """

    user = User.objects.get(pk=user_id)

    cards = Card.objects.filter(owner=user).order_by('rarity', 'class_card', 'id')

    context = {'title': 'Карты пользователя',
               'header': f'Карты пользователя {user.username}',
               'cards': cards,
               'user_info': user
               }

    return render(request, 'cards/view_user_cards.html', context)


def view_card(request, card_id):
    """ Просмотр выбранной карты """

    card = Card.objects.get(pk=card_id)
    amulet = AmuletItem.objects.filter(card=card).last()
    need_exp = calculate_need_exp(card.level)

    context = {'title': 'Выбранная карта',
               'header': 'Выбранная карта',
               'card': card,
               'need_exp': need_exp,
               'amulet': amulet
               }

    return render(request, 'cards/card.html', context)


def select_favorite_card(request, selected_card):
    """ Выбор избранной карты.
        Изменение current_card в Profile пользователя на выбранную карту.
    """

    card = Card.objects.get(pk=selected_card)
    user_profile = Profile.objects.get(user=request.user)
    user_profile.current_card = card
    user_profile.save()

    return HttpResponseRedirect(f'/cards/user_cards-{request.user.id}')


def fight(request, protector_id):
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
        if winner.profile.guild.buff.name == 'Бандитский улов':
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
        transaction_loser = Transactions.objects.create(date_and_time=date_time_now(),
                                                        user=loser,
                                                        before=old_loser_gold,
                                                        after=loser.profile.gold,
                                                        comment='Награда за проигрыш в битве'
                                                        )

        # Начисление опыта, если не достигнут максимальный уровень карты (вынести)
        if winner.profile.current_card.level < winner.profile.current_card.rarity.max_level:
            winner.profile.current_card.experience_bar += 75
        if loser.profile.current_card.level < loser.profile.current_card.rarity.max_level:
            loser.profile.current_card.experience_bar += 25

        # Увеличение уровня карты победителя при достижении определенного опыта (вынести)
        if winner.profile.current_card.experience_bar >= 1000 + 100 * 1.15 ** winner.profile.current_card.level:
            winner.profile.current_card.experience_bar -= 1000 + 100 * 1.15 ** winner.profile.current_card.level
            winner.profile.current_card.level += 1

            # Если достигнут максимальный уровень, прогресс опыта обнуляется
            if winner.profile.current_card.level == winner.profile.current_card.rarity.max_level:
                winner.profile.current_card.experience_bar = 0

            # Увеличение характеристик карты победителя (вынести)
            winner.profile.current_card.hp += winner.profile.current_card.rarity.coefficient_hp_for_level
            winner.profile.current_card.damage += winner.profile.current_card.rarity.coefficient_damage_for_level

        # Увеличение уровня карты проигравшего при достижении определенного опыта (вынести)
        if loser.profile.current_card.experience_bar >= 1000 + 100 * 1.15 ** loser.profile.current_card.level:
            loser.profile.current_card.experience_bar -= 1000 + 100 * 1.15 ** loser.profile.current_card.level
            loser.profile.current_card.level += 1

            # Если достигнут максимальный уровень, прогресс опыта обнуляется
            if loser.profile.current_card.level == loser.profile.current_card.rarity.max_level:
                loser.profile.current_card.experience_bar = 0

            # Увеличение характеристик карты проигравшего (вынести)
            loser.profile.current_card.hp += loser.profile.current_card.rarity.coefficient_hp_for_level
            loser.profile.current_card.damage += loser.profile.current_card.rarity.coefficient_damage_for_level

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

        # Предметы падают только нападавшему
        items = ExperienceItems.objects.all()
        amulets = AmuletType.objects.exclude(chance_drop_on_fight=0)
        reward_item_user = []
        reward_amulet_user = []
        for item in items:  # Проверка выпадения предмета
            chance = randint(1, 100)

            # Использование способности эльфа
            if attacker.profile.current_card.class_card.name == 'Эльф':
                chance_drop = item.chance_drop_on_fight + attacker.profile.current_card.class_card.numeric_value
            else:
                chance_drop = item.chance_drop_on_fight

            if chance <= chance_drop:
                try:
                    items_user = UsersInventory.objects.get(owner=request.user,
                                                            item=item
                                                            )
                    items_user.amount += 1
                    items_user.save()
                    reward_item_user.append(item)
                except UsersInventory.DoesNotExist:
                    new_record_inventory = UsersInventory.objects.create(owner=request.user,
                                                                         item=item,
                                                                         amount=1
                                                                         )
                    reward_item_user.append(item)

        for amulet in amulets:  # Проверка выпадения амулета

            # Использование способности эльфа
            if attacker.profile.current_card.class_card.name == 'Эльф':
                chance_drop = amulet.chance_drop_on_fight + attacker.profile.current_card.class_card.numeric_value
            else:
                chance_drop = amulet.chance_drop_on_fight

            chance = randint(1, 100)
            if chance <= chance_drop:
                new_amulet = AmuletItem.objects.create(amulet_type=amulet,
                                                       owner=attacker)
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


def view_user_cards_for_sale(request, user_id):
    """ Просмотр продаваемых карт пользователя """

    cards = Card.objects.filter(owner=user_id, sale_status=True)
    owner = User.objects.get(pk=user_id)
    context = {'title': 'Продаются',
               'header': 'Продаются',
               'cards': cards,
               'owner': owner,
               }

    return render(request, 'cards/view_sale_card_user.html', context)


def buy_card_user(request, card_id):
    """ Покупка карты у пользователя.
        Изменение владельца карты на текущего пользователя.
        Увеличение/уменьшение gold у покупателя/продавца.
        Создание 2 записей в Transaction.
    """

    if request.user.is_authenticated:
        buyer_profile = Profile.objects.get(user=request.user.pk)
        card = Card.objects.get(pk=card_id)

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


def card_sale(request, card_id):
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


def remove_from_sale_card(request, card_id):
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


def card_level_up(request, card_id):
    """ Меню увеличение уровня """

    card = get_object_or_404(Card, pk=card_id)
    need_exp = calculate_need_exp(card.level)

    inventory = UsersInventory.objects.filter(owner=request.user)
    context = {'title': 'Улучшение карты',
               'header': f'Улучшение карты {card_id}',
               'card': card,
               'inventory': inventory,
               'need_exp': need_exp
               }

    return render(request, 'cards/card_level_up.html', context)


def level_up_with_item(request, card_id, item_id):
    """ Увеличение уровня с помощью предмета.
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
            card.hp += card.rarity.coefficient_hp_for_level * new_levels
            card.damage += card.rarity.coefficient_damage_for_level * new_levels
            card.level = answer[1]

            expended_items = ceil(expended_experience / item.item.experience_amount)

            transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                      user=request.user,
                                                      before=profile.gold,
                                                      after=profile.gold-expended_items*item.item.gold_for_use,
                                                      comment='Улучшение карты'
                                                      )
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


def view_all_sale_card(request):
    """ Вывод всех продаваемых карт.
    """

    if request.user.is_authenticated:
        sale_cards = Card.objects.exclude(Q(sale_status=False) | Q(owner=request.user))
    else:
        sale_cards = Card.objects.filter(sale_status=True)

    context = {'title': 'Улучшение карты',
               'header': 'Торговая площадка',
               'cards': sale_cards,
               }

    return render(request, 'cards/all_sale_card.html', context)
