from cards.models import Card, CardStore, HistoryReceivingCards
from django.contrib.auth.models import User
from datetime import datetime
import pytz


def fight_now(attacker_hp, attacker_damage, protector_hp, protector_damage: int) -> str:
    """ Битва """

    fight = True
    winner = None
    while fight:
        protector_hp -= attacker_damage
        if protector_hp <= 0:
            winner = 'attacker'
            fight = False
        else:
            attacker_hp -= protector_damage
            if attacker_hp <= 0:
                winner = 'protector'
                fight = False
    return winner


def filling_missing_data():
    """ Заполнение данных о создании карты у карт, созданных изначально """

    date_and_time = datetime(year=2023, month=11, day=5, hour=13, minute=30, tzinfo=pytz.timezone('Europe/Moscow'))
    cards = Card.objects.all()
    card_store = CardStore.objects.all()
    admin = User.objects.get(pk=1)
    temp_info = []

    for card in cards:
        for card_in_store in card_store:
            if (card.class_card == card_in_store.class_card and card.type == card_in_store.type and
                    card.rarity == card_in_store.rarity and card.hp == card_in_store.hp and card.damage == card_in_store.damage):
                temp_info.append(card.id)

    for card in cards:
        if card.id in temp_info:
            method_receiving = 'Покупка в магазине'
            new_record = HistoryReceivingCards.objects.create(card=card,
                                                              date_and_time=date_and_time,
                                                              user=admin,
                                                              method_receiving=method_receiving)
            new_record.save()
        else:
            method_receiving = 'Бесплатная генерация'
            new_record = HistoryReceivingCards.objects.create(card=card,
                                                              date_and_time=date_and_time,
                                                              user=admin,
                                                              method_receiving=method_receiving)
            new_record.save()


def delete_all_record():
    """ Удаление всех записей в таблице с историей получения карт """

    table = HistoryReceivingCards.objects.all()
    for a in table:
        a.delete()


def date_time_now():
    date_time = datetime.now(pytz.timezone('Europe/Moscow'))

    return date_time
