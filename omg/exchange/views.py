from datetime import datetime
import pytz

from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponseRedirect

from .models import ExperienceItems, UsersInventory, AmuletStore, AmuletItem
from .forms import BuyItemForm

from users.models import Transactions, Profile
from cards.models import Card


def view_inventory_user(request, user_id):
    """ Просмотр инвентаря пользователя.
        Доступно только если текущий пользователь является владельцем инвентаря.
     """

    if request.user.id == user_id:
        user_items = UsersInventory.objects.filter(owner=request.user)
        user_amulets = AmuletItem.objects.filter(owner=request.user)

        context = {'title': 'Инвентарь',
                   'header': f'Инвентарь {request.user.username}',
                   'user_items': user_items,
                   'user_amulets': user_amulets
                   }

        return render(request, 'exchange/view_user_inventory.html', context)
    else:
        messages.error(request, 'Просмотр инвентаря пользователя невозможен')

        return HttpResponseRedirect(reverse('home'))


def item_store(request):
    """ Вывод ассортимента магазина предметов """

    items_on_sale = ExperienceItems.objects.filter(sale_now=True).order_by('experience_amount')
    amulets_on_sale = AmuletStore.objects.filter(sale_now=True)

    context = {'title': 'Магазин предметов',
               'header': 'Магазин предметов',
               'items': items_on_sale,
               'amulets': amulets_on_sale
               }

    return render(request, 'exchange/items_store.html', context)


def buy_amulet(request, amulet_id):
    """ Покупка амулета.
        Создает амулет на основе амулета из магазина и присваивает его покупателю в таблице AmuletItem.
        Создает запись в Transactions.
        Изменяет gold в Profile текущего пользователя.
    """

    if request.user.is_authenticated:
        profile_user = Profile.objects.get(user=request.user)
        current_amulet = get_object_or_404(AmuletStore, pk=amulet_id)
        if profile_user.gold < current_amulet.price:
            messages.error(request, 'Для покупки вам не хватает денег!')

            return HttpResponseRedirect(reverse('items_store'))

        else:
            bought_amulet = AmuletItem.objects.create(amulet_type=current_amulet.amulet_type,
                                                      owner=request.user,
                                                      bonus_hp=current_amulet.bonus_hp,
                                                      bonus_damage=current_amulet.bonus_damage,
                                                      price=round(0.7*current_amulet.price))
            bought_amulet.save()
            new_record_transaction = Transactions.objects.create(date_and_time=datetime.now(pytz.timezone('Europe/Moscow')),
                                                                 user=request.user,
                                                                 before=profile_user.gold,
                                                                 after=profile_user.gold - current_amulet.price,
                                                                 comment='Покупка в магазине предметов')
            profile_user.gold = new_record_transaction.after
            new_record_transaction.save()
            profile_user.save()
            messages.success(request, 'Вы успешно совершили покупку!')

            return HttpResponseRedirect(reverse('items_store'))

    else:
        messages.error(request, 'Для покупки необходимо авторизироваться!')

        return HttpResponseRedirect(reverse('items_store'))


def buy_item(request, item_id):
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

            new_record_history.date_and_time = datetime.now(pytz.timezone('Europe/Moscow'))
            new_record_history.user = request.user
            new_record_history.item = item

            new_record_transaction = Transactions.objects.create(date_and_time=datetime.now(pytz.timezone('Europe/Moscow')),
                                                                 user=request.user,
                                                                 before=profile.gold,
                                                                 after=profile.gold-item.price*new_record_history.amount,
                                                                 comment='Покупка в магазине предметов'
                                                                 )
            new_record_transaction.save()
            new_record_history.transaction = new_record_transaction
            profile.gold = profile.gold - item.price*new_record_history.amount
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

            return HttpResponseRedirect(reverse('items_store'))
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


def change_amulet_menu(request, card_id):
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


def change_amulet(request, card_id, amulet_id):
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


def remove_amulet(request, card_id, amulet_id):
    """ Удаляет у выбранного амулета карту
    """
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
        messages.error(request, 'Для данных действий нужно авторизироваться!')

        return HttpResponseRedirect(reverse('home'))


def sale_amulet(request, user_id, amulet_id):
    """ Продажа пользователем амулета внутриигровому магазину.
        Амулет удаляется из инвенторя и запись о нем так же удаляется.
        Пользователь получает деньги за продажу.
        Создается запись в Transactions.
    """
    if request.user.is_authenticated and request.user.id == user_id:
        amulet = get_object_or_404(AmuletItem, pk=amulet_id)
        profile = Profile.objects.get(pk=request.user.id)
        if amulet.owner == request.user:
            transaction = Transactions.objects.create(date_and_time=datetime.now(pytz.timezone('Europe/Moscow')),
                                                      user=request.user,
                                                      before=profile.gold,
                                                      after=profile.gold+amulet.price,
                                                      comment='Продажа амулета')
            profile.gold += amulet.price
            amulet.delete()
            profile.save()
            transaction.save()

            return HttpResponseRedirect(f'/inventory/{user_id}')
        else:
            messages.error(request, 'Произошла ошибка!')

            return HttpResponseRedirect(reverse('home'))

    else:
        messages.error(request, 'Произошла ошибка!')

        return HttpResponseRedirect(reverse('home'))
