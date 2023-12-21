from datetime import datetime
import pytz

from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponseRedirect

from .models import ExperienceItems, UsersInventory
from .forms import BuyItemForm

from users.models import Transactions, Profile


def view_inventory_user(request, user_id):
    """ Просмотр инвентаря пользователя.
        Доступно только если текущий пользователь является владельцем инвентаря.
     """

    if request.user.id == user_id:
        user_items = UsersInventory.objects.filter(owner=request.user)

        context = {'title': 'Инвентарь',
                   'header': f'Инвентарь {request.user.username}',
                   'user_items': user_items
                   }

        return render(request, 'exchange/view_user_inventory.html', context)
    else:
        messages.error(request, 'Просмотр инвентаря пользователя невозможен')

        return HttpResponseRedirect(reverse('home'))


def item_store(request):
    """ Вывод ассортимента магазина предметов """

    items_on_sale = ExperienceItems.objects.filter(sale_now=True).order_by('experience_amount')

    context = {'title': 'Магазин предметов',
               'header': 'Магазин предметов',
               'items': items_on_sale
               }

    return render(request, 'exchange/items_store.html', context)


def buy_item(request, item_id):
    """ Покупка предмета.
        Создает запись в Transactions.
        Создает запись в истории покупок предметов HistoryPurchaseItems.
        Выбранный товар начисляется в инвентарь (или обновляется его количество).
        Изменяется gold в Profile.
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
