from logging import getLogger
from random import choice

from celery import shared_task
from django.db.models import Q
from django.db import transaction

from .models import TeamsForBattleEvent, BattleEventParticipants, BattleEventAwards
from users.models import Profile

logger = getLogger(__name__)


@shared_task
def preparation_battle_event():
    """ Подготовка участников к боевому событию.
        Запуск 1 числа каждого месяца в 0:00
    """

    logger.info('Запуск подготовки к новому сезону боевого события...')
    delete_all_battle_event_participants()
    if fill_battle_event_participants():
        logger.info('Подготовка списка участников...')
        fill_battle_event_enemies()
    logger.info('Подготовка к новому сезону боевого события завершена!')


def fill_battle_event_participants() -> bool:
    """ Заполнение таблицы участников боевого события.
        Заполняет таблицы участниками, у которых заняты все слоты команды.
    """

    users_templates_teams = TeamsForBattleEvent.objects.exclude(Q(first_card__isnull=True) |
                                                                Q(second_card__isnull=True) |
                                                                Q(third_card__isnull=True))

    battle_participants_to_create = []

    for template_team in users_templates_teams:
        initial_battle_progress = {str(day): False for day in range(1, 11)}

        new_participant = BattleEventParticipants(user=template_team.user,
                                                  first_card=template_team.first_card,
                                                  second_card=template_team.second_card,
                                                  third_card=template_team.third_card,
                                                  battle_progress=initial_battle_progress,
                                                  points=0)
        battle_participants_to_create.append(new_participant)

    if len(battle_participants_to_create) >= 2:
        with transaction.atomic():
            BattleEventParticipants.objects.bulk_create(battle_participants_to_create)
            logger.info(f'Зарегистрировано {len(battle_participants_to_create)} '
                        f'участников в battle_event_participants')
            return True
    else:
        logger.info(f'Не хватает участников для боевого события')
        return False


def fill_battle_event_enemies():
    """ Заполняет у каждого участника боевого события список случайных противников на каждый день """

    all_battle_participants = BattleEventParticipants.objects.all()
    all_participant_ids = list(all_battle_participants.values_list('user_id', flat=True))

    participants_to_update = []

    for participant in all_battle_participants:
        available_opponent_ids = [pk for pk in all_participant_ids if pk != participant.user_id]
        enemies_for_participant = {str(day): None for day in range(1, 11)}

        for day in range(1, 11):
            enemies_for_participant[str(day)] = choice(available_opponent_ids)

        participant.enemies = enemies_for_participant
        participants_to_update.append(participant)

    with transaction.atomic():
        BattleEventParticipants.objects.bulk_update(participants_to_update, ['enemies'])
        logger.info(f'Установлено противников на каждый день у '
                    f'{len(participants_to_update)} участников в battle_event_participants')


def delete_all_battle_event_participants():
    """ Удаление всех записей из таблицы участников
        перед формированием нового списка сезона.
    """

    try:
        with transaction.atomic():
            deleted_count, _ = BattleEventParticipants.objects.all().delete()
            logger.info(f'Удалено {deleted_count} записей из таблицы battle_event_participants')
    except Exception as e:
        logger.error(f'Ошибка при удалении записей из battle_event_participants: {e}')


@shared_task
def accrual_of_reward():
    """ Начисление награды участникам боевого события.
        Запуск 11 числа каждого месяца в 0:00
    """

    awards = BattleEventAwards.objects.all().order_by('rank')
    count_awards = awards.count()
    best_users = BattleEventParticipants.objects.filter(points__gt=0).order_by('-points')[:count_awards]
    best_user_ids = best_users.values_list('user_id', flat=True)
    users_in_awards = Profile.objects.filter(user__id__in=best_user_ids)
    users_in_awards_lookup = {profile.user_id: profile for profile in users_in_awards}
    update_user = []
    for rank, user in enumerate(best_users):
        current_award = awards[rank]
        user_profile = users_in_awards_lookup.get(user.user_id)
        user_profile.diamond += current_award.amount
        update_user.append(user_profile)

    with transaction.atomic():
        Profile.objects.bulk_update(update_user, ['diamond'])
        logger.info(f'Отправлена награда для {len(update_user)} лидеров в боевом событии')




