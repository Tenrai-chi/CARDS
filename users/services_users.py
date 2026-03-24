from logging import getLogger

from django.contrib.auth.models import User
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.core.files.uploadedfile import UploadedFile
from django.core.paginator import Paginator
from django.contrib.auth.tokens import default_token_generator
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.encoding import force_str
from django.utils.encoding import force_bytes
from django.shortcuts import get_object_or_404
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from common.utils import date_time_now
from .models import FavoriteUsers, Profile

from .tasks import send_verification_email, send_email_change_confirmation, send_password_reset_email

signer = TimestampSigner()

logger = getLogger(__name__)


@receiver(post_save, sender=User)
def create_profile_user(sender, instance, created, **kwargs):
    """ Создание профиля пользователя при создании экземпляра User  """

    if created and not Profile.objects.filter(user=instance).exists():
        Profile.objects.create(user=instance,
                               receiving_timer=date_time_now()
                               )
        if instance.email:
            from .tasks import send_verification_email
            send_verification_email.delay(instance.id)


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


def confirm_email(signed_value: str) -> dict:
    """ Подтверждение email.
        Возвращает словарь с success, user_id и massage
    """

    answer_data = {}
    try:
        user_id = signer.unsign(signed_value, max_age=172800)
        user = User.objects.get(id=user_id)
        profile = user.profile
        if profile.is_activated:
            answer_data['success'] = False
            answer_data['user_id'] = user.id
            answer_data['message'] = 'Email уже подтверждён'
            return answer_data
        profile.is_activated = True
        profile.save()

        answer_data['success'] = True
        answer_data['user_id'] = user.id
        answer_data['message'] = 'Email успешно подтверждён!'
        logger.info(f'Пользователь ID {user_id} подтвердил свой email')
        return answer_data

    except SignatureExpired:
        try:
            user_id = signed_value.split(':')[0]
            user = User.objects.get(id=user_id)
            answer_data['success'] = False
            answer_data['user_id'] = user.id
            answer_data['message'] = 'Срок действия ссылки истёк'
            logger.warning(f'Пользователь ID {user_id} перешел по истекшей ссылке для подтверждения email')
            return answer_data

        except (ValueError, User.DoesNotExist):
            answer_data['success'] = False
            answer_data['user_id'] = None
            answer_data['message'] = 'Некорректная ссылка'
            return answer_data

    except BadSignature:
        answer_data['success'] = False
        answer_data['user_id'] = None
        answer_data['message'] = 'Недействительная ссылка подтверждения'
        return answer_data

    except User.DoesNotExist:
        answer_data['success'] = False
        answer_data['user_id'] = None
        answer_data['message'] = 'Пользователь не найден'
        return answer_data


def resend_verification_email(user_id) -> dict:
    """ Отправка повторного письма подтверждения.
        Возвращает словарь с success и message
    """

    answer_data = {}
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        answer_data['success'] = False
        answer_data['message'] = 'Пользователь не найден'
        return answer_data

    profile = user.profile
    if profile.pending_email:
        send_email_change_confirmation.delay(user.id, profile.pending_email)
        answer_data['success'] = True
        answer_data['message'] = f'Письмо для подтверждения нового email ({profile.pending_email}) отправлено'
        logger.info(f'Пользователь ID {user_id} запросил письмо для подтверждения нового email')
        return answer_data

    if user.profile.is_activated:
        answer_data['success'] = False
        answer_data['message'] = 'Email уже подтверждён'
        return answer_data

    send_verification_email.delay(user.id)
    answer_data['success'] = True
    answer_data['message'] = 'Письмо отправлено повторно. Проверьте почту'
    logger.info(f'Пользователь ID {user_id} заново запросил письмо для подтверждения нового email')
    return answer_data


def change_user_email(user_id, new_email) -> dict:
    """
    Обрабатывает смену email: сохраняет pending_email, сбрасывает is_activated,
    отправляет письмо подтверждения.
    Возвращает словарь с success, message.
    """

    answer_data = {}
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        answer_data['success'] = False
        answer_data['message'] = 'Пользователь не найден'
        return answer_data

    if User.objects.filter(email=new_email).exclude(id=user_id).exists():
        answer_data['success'] = False
        answer_data['message'] = 'Этот email уже используется другим пользователем'
        return answer_data

    profile = user.profile
    profile.pending_email = new_email
    profile.is_activated = False
    profile.save()

    send_email_change_confirmation.delay(user.id, new_email)
    answer_data['success'] = True
    answer_data['message'] = 'На новый email отправлено письмо для подтверждения'
    logger.info(f'Пользователь ID {user_id} изменил свою почту. Почта ожидает подтверждения')
    return answer_data


def process_password_reset(email: str, domain, protocol) -> dict:
    """ Отправка письма для восстановления пароля """

    answer_data = {}
    if not email:
        answer_data['success'] = False
        answer_data['message'] = 'Email пуст'
        return answer_data

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        answer_data['success'] = False
        answer_data['message'] = 'Пользователя с таким email не существует'
        return answer_data

    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    domain = domain
    protocol = protocol

    send_password_reset_email.delay(user.id, domain, protocol, uidb64, token)
    answer_data['success'] = True
    answer_data['message'] = 'Письмо для восстановления пароля отправлено на указанный email'
    logger.info(f'Пользователь ID {user.id} запросил восстановление пароля')
    return answer_data


def process_password_reset_confirm(uidb64: str, token: str, new_password: str) -> dict:
    """ Смена пароля через запрос о восстановления пароля через почту """

    answer_data = {}
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        answer_data['success'] = False
        answer_data['message'] = 'Ссылка для восстановления пароля недействительна или устарела'
        return answer_data

    if not default_token_generator.check_token(user, token):
        answer_data['success'] = False
        answer_data['message'] = 'Ссылка для восстановления пароля недействительна или устарела'
        return answer_data

    user.set_password(new_password)
    user.save()
    answer_data['success'] = True
    answer_data['message'] = 'Пароль успешно изменён. Теперь вы можете войти'
    logger.info(f'Пользователь ID {user.id} изменил свой пароль')
    return answer_data
