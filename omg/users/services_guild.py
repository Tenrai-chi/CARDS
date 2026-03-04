from logging import getLogger

from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404


from cards.models import Card
from common.utils import date_time_now, time_difference_check

from .models import Profile, Transactions, Guild, GuildBuff

logger = getLogger(__name__)


def update_user_after_guild_removal(guild: Guild, profile_user: Profile) -> None:
    """ Обновляет данные профиля и информацию в гильдии после удаления пользователя из нее """

    guild.rating -= profile_user.guild_point
    guild.number_of_participants -= 1

    profile_user.guild = None
    profile_user.date_guild_accession = None
    profile_user.guild_point = 0

    profile_user.save()
    guild.save()
    logger.info(f'Пользователь ID {profile_user.user.id} покинул гильдию ID {guild.id}')


def view_all_guilds_service(page_num: int = 1, item_per_page: int = 15) -> dict:
    """ Возвращает список всех гильдий с учетом пагинации """

    guilds = Guild.objects.all().order_by('-rating')
    paginator = Paginator(guilds, item_per_page)
    page = paginator.get_page(page_num)
    answer_data = {'guilds': page.object_list,
                   'page': page
                   }

    return answer_data


@transaction.atomic
def delete_member_guild_service(user_id: int, member_id: int, guild_id: int) -> dict:
    """ Удаление пользователя из гильдии.
        Лидер может удалить любого пользователя.
        Лидер может удалить себя только если он 1 в гильдии + удаляется гильдия,
        иначе ошибка с просьбой передать права другому участнику.
        Другие пользователи могут удалять только себя.
        Если пользователь (и гильдия) удалены, возвращает сообщение об успехе.
        Если не произошло удаление, то сообщение об ошибке.
        Возвращает redirect_name_url, если view не должна перенаправлять на страницу гильдии.
    """

    answer_data = {}
    profile_user = get_object_or_404(Profile, user=member_id)
    guild = get_object_or_404(Guild, pk=guild_id)

    is_leader: bool = guild.leader.id == user_id
    is_self_remove: bool = user_id == member_id
    is_last_member: bool = guild.number_of_participants == 1

    if profile_user.guild != guild:
        answer_data['error_message'] = 'Вы не участник этой гильдии'
        answer_data['redirect_name_url'] = 'view_all_guilds'
        return answer_data

    if is_leader and is_self_remove:
        if is_last_member:
            update_user_after_guild_removal(guild, profile_user)

            message_delete_guild = delete_guild_service(user_id, guild_id, True)

            answer_data['success_message'] = message_delete_guild.get('success_message')
            answer_data['redirect_name_url'] = 'view_all_guilds'
            return answer_data

        else:
            message = 'Вы не можете покинуть гильдию. Сначала передайте лидерство другому участнику'
            answer_data['error_message'] = message
            return answer_data

    elif is_leader and not is_self_remove:
        update_user_after_guild_removal(guild, profile_user)
        answer_data['success_message'] = 'Вы успешно выгнали участника из гильдии'
        return answer_data

    elif not is_leader and is_self_remove:
        update_user_after_guild_removal(guild, profile_user)
        answer_data['redirect_name_url'] = 'view_all_guilds'
        answer_data['success_message'] = 'Вы успешно покинули гильдию!'
        return answer_data

    else:
        answer_data['error_message'] = 'У вас нет прав выгонять участников из гильдии'
        return answer_data


def delete_guild_service(user_id: int, guild_id: int, is_internal_call: bool = False) -> dict:
    """ Удаление гильдии.
        Если было вызвано из другого сервиса (удаление пользователя), то просто удаляет гильдию.
        Удалить гильдию может только лидер.
        У всех текущих участников гильдии изменяются guild, date_guild_accession на None, а guild_point на 0.
        Удаляется запись о гильдии в Guild.
        Возвращает сообщение об успехе или ошибке.
    """

    answer_data = {}
    if is_internal_call:
        guild = Guild.objects.get(pk=guild_id)
        guild.delete()
        answer_data['success_message'] = 'Вы успешно расформировали гильдию'
        logger.info(f'Гильдия ID {guild.id} была удалена')
        return answer_data

    members_for_update = []
    guild_info = get_object_or_404(Guild, pk=guild_id)
    members_guild = Profile.objects.filter(guild=guild_info)
    if user_id != guild_info.leader.id:
        answer_data['error_message'] = 'Вы не являетесь лидером гильдии'
        return answer_data

    for member in members_guild:
        member.guild = None
        member.date_guild_accession = None
        member.guild_point = 0
        members_for_update.append(member)

    with transaction.atomic():
        Profile.objects.bulk_update(members_for_update, ['guild', 'date_guild_accession', 'guild_point'])
        guild_info.delete()
        logger.info(f'Участники гильдии ID {guild_info.id} были исключены')
        logger.info(f'Гильдия ID {guild_info.id} была удалена')

    answer_data['success_message'] = 'Вы расформировали гильдию!'
    return answer_data


@transaction.atomic
def add_member_guild_service(user_id: int, guild_id: int) -> dict:
    """ Вступление пользователя в гильдию.
        У пользователя устанавливается гильдия, текущие очки гильдии и дата присоединения.
        В гильдии увеличивается количество участников.
        Возвращает сообщение об успехе или ошибке.
    """

    answer_data = {}
    user_profile = Profile.objects.get(user=user_id)
    guild_info = get_object_or_404(Guild, pk=guild_id)

    if guild_info.number_of_participants >= guild_info.max_number_of_participants:
        answer_data['error_message'] = 'В этой гильдии заняты все места!'
        return answer_data

    if user_profile.guild is not None:
        answer_data['error_message'] = 'Чтобы вступить в новую гильдию, покиньте текущую!'
        return answer_data

    user_profile.guild = guild_info
    user_profile.date_guild_accession = date_time_now()
    user_profile.guild_point = 0

    guild_info.add_user_in_guild()
    user_profile.save()
    logger.info(f'Пользователь ID {user_profile.user.id} вступил в гильдию')

    answer_data['success_message'] = 'Вы успешно вступили в гильдию!'
    return answer_data


@transaction.atomic
def edit_guild_info_service(user_id: int, guild_id: int, name: str,
                            guild_pic: UploadedFile, buff: GuildBuff) -> dict:
    """ Изменение информации о гильдии.
        Изменяет данные гильдии на переданные.
        Если была попытка изменить усиление гильдии, то проверяется прошло ли 2 недели
        с момента прошлой смены усиления.
        Если не прошло - выводится ошибка, если прошло, то создается транзакция у главы.
        Стоимость смены усиления 30.000 золота.
        Возвращает только сообщение об ошибке при наличии.
    """

    answer_data = {}
    guild_info = get_object_or_404(Guild, pk=guild_id)

    if guild_info.leader.id != user_id:
        answer_data['error_message'] = 'Вы не являетесь лидером гильдии!'
        return answer_data

    if guild_info.name != name:
        profile_leader = Profile.objects.get(user=user_id)
        profile_gold_before = profile_leader.gold
        profile_gold_after = profile_gold_before - 30000
        profile_leader.gold = profile_gold_after
        profile_leader.save()

        new_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                      user=profile_leader.user,
                                                      before=profile_gold_before,
                                                      after=profile_gold_after,
                                                      comment='Смена названия гильдии'
                                                      )
        logger.info(f'Создана транзакция пользователя ID {profile_leader.user.id}: ID {new_transaction.id}')
        guild_info.name = name

    if guild_info.guild_pic != guild_pic:
        guild_info.guild_pic = guild_pic

    if guild_info.buff != buff:
        can_edit_buff, hours = time_difference_check(guild_info.date_last_change_buff, 336)
        days = hours // 24

        if can_edit_buff:
            guild_info.date_last_change_buff = date_time_now()
        else:
            message = f'Вы пока что не можете поменять усиление гильдии! До следующего изменения {14-days} дней'
            answer_data['error_message'] = message
    guild_info.save()
    logger.info(f'Гильдия ID {guild_info.id} изменила свои публичные данные')
    return answer_data


@transaction.atomic
def create_guild_service(user_id: int, name: str, guild_pic: UploadedFile, buff: GuildBuff) -> dict:
    """ Создание гильдии.
        Если пользователь уже состоит в гильдии или ему не хватает денег, возвращается ошибка.
        Устанавливает переданные параметры (имя, усиление, картинка).
        Лидером становится создатель.
        Создает запись в Transaction.
        При успешном создании возвращается сообщение об успехе и айди созданной гильдии.
        При ошибке возвращается сообщение об ошибке.
    """

    answer_data = {}
    user_profile = Profile.objects.get(user=user_id)
    if user_profile.guild:
        answer_data['error_message'] = 'Для создания гильдии покиньте текущую!'
        return answer_data

    if user_profile.gold < 50000:
        answer_data['error_message'] = 'Вам не хватает денег!'
        return answer_data

    new_guild = Guild.objects.create(name=name,
                                     leader=user_profile.user,
                                     guild_pic=guild_pic,
                                     date_create=date_time_now(),
                                     date_last_change_buff=date_time_now(),
                                     rating=1,
                                     buff=buff)
    logger.info(f'Создана гильдия ID {new_guild.id}')

    user_gold_before = user_profile.gold
    user_gold_after = user_gold_before - 50000
    new_transaction = Transactions.objects.create(date_and_time=date_time_now(),
                                                  user=user_profile.user,
                                                  before=user_gold_before,
                                                  after=user_gold_after,
                                                  comment='Создание гильдии'
                                                  )
    logger.info(f'Создана транзакция пользователя ID {user_profile.user.id}: ID {new_transaction.id}')
    user_profile.spend_gold(50000)
    user_profile.guild = new_guild
    user_profile.guild_point = 0
    user_profile.date_guild_accession = date_time_now()
    user_profile.save()
    logger.info(f'Пользователь ID {user_profile.user.id} вступил в гильдию ID {new_guild.id}')

    answer_data['success_message'] = 'Вы успешно создали гильдию'
    answer_data['guild_id'] = new_guild.id
    return answer_data


def change_leader_guild_service(user_id: int, guild_id: int, new_lead_id: int) -> dict:
    """ Смена лидера гильдии.
        Возвращает сообщение об ошибке или успехе.
    """

    answer_data = {}
    guild_info = get_object_or_404(Guild, pk=guild_id)
    new_leader = get_object_or_404(User, pk=new_lead_id)
    if user_id != guild_info.leader.id:
        answer_data['error_message'] = 'Вы не являетесь лидером гильдии!'
        return answer_data

    if user_id == new_lead_id:
        answer_data['error_message'] = 'Вы уже являетесь лидером!'
        return answer_data

    guild_info.leader = new_leader
    guild_info.save()
    logger.info(f'Гильдия ID {guild_info.id} сменила лидера')
    answer_data['success_message'] = 'Вы успешно сменили лидера!'

    return answer_data
