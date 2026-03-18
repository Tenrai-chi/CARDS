from logging import getLogger

from django.contrib.auth.models import User
from django.db.models import F
from django.core.files.uploadedfile import UploadedFile
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404

from .models import Profile, FavoriteUsers

logger = getLogger(__name__)


def add_favorite_user_service(user_id: int, favorite_user_id: int) -> dict:
    """ Добавляет пользователя в список избранных.
        Возвращает сообщение об успехе или ошибке.
    """

    answer_data = {}
    if user_id == favorite_user_id:
        answer_data['error_message'] = 'Вы не можете добавить себя в избранное'
        return answer_data

    try:
        _ = FavoriteUsers.objects.get(user=user_id, favorite_user=favorite_user_id)
        answer_data['error_message'] = 'Этот пользователь уже в избранном!'
        return answer_data

    except FavoriteUsers.DoesNotExist:
        new_favorite_user = get_object_or_404(User, pk=favorite_user_id)

    favorite_users_count = FavoriteUsers.objects.filter(user=user_id).count()
    user = User.objects.get(pk=user_id)
    if favorite_users_count >= 50:
        answer_data['error_message'] = 'Достигнут предел избранных пользователей! Для добавления новых освободите место'
        return answer_data

    FavoriteUsers.objects.create(user=user, favorite_user=new_favorite_user)
    logger.info(f'Пользователь ID {user_id} добавил пользователя ID {favorite_user_id} в избранное')

    answer_data['success_message'] = 'Вы успешно добавили пользователя в избранное'
    return answer_data


def delete_favorite_user_service(user_id: int, favorite_user_id: int) -> dict:
    """ Удаляет пользователя из списка избранных.
        Возвращает сообщение об успехе или ошибке.
    """

    answer_data = {}
    if user_id == favorite_user_id:
        answer_data['error_message'] = 'Вы не можете убрать себя из избранных!'
        return answer_data

    try:
        record = FavoriteUsers.objects.get(user=user_id, favorite_user=favorite_user_id)
        record.delete()
        logger.info(f'Пользователь ID {user_id} удалил пользователя ID {favorite_user_id} в избранное')
        answer_data['success_message'] = 'Вы успешно удалили пользователя из списка избранных!'

    except FavoriteUsers.DoesNotExist:
        answer_data['error_message'] = 'Этот участник не находится в вашем списке избранных!'

    return answer_data


def edit_profile_service(user_id: int, about_user: str | None, profile_pic: UploadedFile | None) -> None:
    """ Изменение профиля.
        Устанавливает переданные поля у профиля пользователя.
    """

    profile = Profile.objects.get(user=user_id)
    profile.about_user = about_user
    profile.profile_pic = profile_pic
    profile.save()
    logger.info(f'Профиль пользователя ID {user_id} был изменен')


def view_rating_service(page_num: int = 1, item_per_page: int = 25) -> dict:
    """ Возвращает список всех пользователей и их рейтинга с учетом пагинации """

    users = (User.objects.all()
             .annotate(rating=500 + F('profile__win') * 25 - F('profile__lose') * 20).order_by('-rating'))
    paginator = Paginator(users, item_per_page)
    page = paginator.get_page(page_num)
    answer_data = {'users': page.object_list,
                   'page': page
                   }

    return answer_data


