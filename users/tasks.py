from celery import shared_task

from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import send_mail
from django.core.signing import TimestampSigner
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags

from .utils import generate_verification_url
# from .models import Transactions
# from common.utils import date_time_now

signer = TimestampSigner()


@shared_task(acks_late=True)
def send_verification_email(user_id: int) -> None:
    """ Асинхронная отправка письма для подтверждения почты.
        Отправляется автоматически при регистрации
    """

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    verification_url = generate_verification_url(user_id)
    context = {'user': user,
               'verification_url': verification_url,
               'site_name': settings.SITE_NAME}

    subject = 'Подтверждение email'
    html_message = render_to_string('users/verification_email.html', context)
    plain_message = strip_tags(html_message)

    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
    )


@shared_task
def send_password_reset_email(user_id: int, domain: str, protocol: str, uidb64: str, token: str) -> None:
    """ Задача по отправке письма для сброса пароля """

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    context = {
        'user': user,
        'domain': domain,
        'protocol': protocol,
        'uidb64': uidb64,
        'token': token,
        'site_name': settings.SITE_NAME,
    }
    subject = 'Восстановление пароля'
    html_message = render_to_string('users/password_reset_email.html', context)
    plain_message = strip_tags(html_message)

    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
    )


@shared_task(acks_late=True)
def send_email_change_confirmation(user_id: int, new_email: str) -> None:
    """ Отправление письма для подтверждения нового email """

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return

    signed_value = signer.sign(f'{user.id}:{new_email}')
    path = reverse('confirm_new_email', kwargs={'signed_value': signed_value})
    base_url = settings.SITE_URL.rstrip('/')
    confirmation_url = f'{base_url}{path}'

    context = {
        'user': user,
        'new_email': new_email,
        'confirmation_url': confirmation_url,
        'site_name': settings.SITE_NAME,
    }
    subject = 'Подтверждение нового email'
    html_message = render_to_string('users/email_change_confirmation.html', context)
    plain_message = strip_tags(html_message)

    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [new_email],
        html_message=html_message,
    )

# @shared_task(acks_late=True)
# def create_transaction_test():
#     """ Тестовая задача для celery """
#
#     current_user = User.objects.get(id=1)
#     new_transaction = Transactions.objects.create(user=current_user,
#                                                   date_and_time=date_time_now(),
#                                                   before=300,
#                                                   after=300,
#                                                   comment='TEST CELERY')
#     new_transaction.save()
#     return f'Transaction {new_transaction.id} created'

