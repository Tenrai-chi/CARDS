from logging import getLogger

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.db.models import F, Q
from django.forms import Form
from django.http import HttpResponseRedirect, HttpResponse, HttpRequest
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy, reverse
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_str, force_bytes
from django.views.generic import CreateView
from django.views.decorators.csrf import csrf_protect

from cards.models import FightHistory
from common.decorators import auth_required, owner_required
from exchange.models import AmuletItem

from .forms import LoginForm, RegistrationForm, EditProfileForm, CustomSetPasswordForm, CustomPasswordChangeForm
from .services_users import (add_favorite_user_service, delete_favorite_user_service, edit_profile_service,
                             view_rating_service, confirm_email, resend_verification_email, change_user_email,
                             process_password_reset, process_password_reset_confirm)
from .models import Profile, Transactions, FavoriteUsers

logger = getLogger(__name__)
signer = TimestampSigner()


class CustomLoginView(LoginView):
    """ Авторизация пользователя """

    authentication_form = LoginForm
    template_name = 'users/login.html'
    extra_context = {'title': 'Авторизация на сайте',
                     'header': 'Авторизация на сайте',
                     }

    def get_success_url(self) -> str:
        return reverse_lazy('home')


class CustomRegistrationView(CreateView):
    """ Регистрация пользователя """

    form_class = RegistrationForm
    template_name = 'users/signup.html'
    extra_context = {'title': 'Регистрация на сайте',
                     'header': 'Регистрация на сайте',
                     }

    def get_success_url(self) -> str:
        return reverse_lazy('login')

    def form_valid(self, form: Form) -> HttpResponse:
        form.save()
        return super().form_valid(form)


def verify_email(request, signed_value):
    """ Отправка письма для подтверждения почты """

    confirm_email_data: dict = confirm_email(signed_value)
    if confirm_email_data['success']:
        messages.success(request, confirm_email_data['message'])
        if confirm_email_data['user_id']:
            return HttpResponseRedirect(reverse('view_profile', kwargs={'user_id': confirm_email_data['user_id']}))
        else:
            return redirect('home')
    else:
        messages.error(request, confirm_email_data['message'])
        return redirect('home')


@csrf_protect
def resend_verification(request) -> HttpResponseRedirect:
    """ Повторная отправка письма подтверждения почты """

    if request.method != 'POST':
        messages.error(request, 'Неожиданный запрос')
        return redirect('home')

    user_id = request.POST.get('user_id')
    if not user_id:
        messages.error(request, 'Неверный запрос.')
        return redirect('home')
    resend_email_answer: dict = resend_verification_email(user_id)
    if resend_email_answer['success']:
        messages.success(request, resend_email_answer['message'])
    else:
        messages.error(request, resend_email_answer['message'])
    return HttpResponseRedirect(reverse('view_profile', kwargs={'user_id': user_id}))


def password_reset_request(request) -> HttpResponseRedirect:
    """ Запрос сброса пароля.
        Пользователь должен ввести почту, привязанную к профилю
    """

    if request.method != 'POST':
        messages.error(request, 'Неожиданный запрос')
        return redirect('home')

    if request.method == 'POST':
        email = request.POST.get('email')
        domain = request.get_host()
        protocol = 'https' if request.is_secure() else 'http'
        result: dict = process_password_reset(email, domain, protocol)
        if result['success']:
            messages.success(request, result['message'])
            return redirect('home')
        else:
            messages.error(request, result['message'])
            return redirect('password_reset')
    context = {'title': 'Смена пароля', 'header': 'Смена пароля'}
    return render(request, 'users/password_reset_form.html', context)


def password_reset_confirm(request, uidb64, token):
    """ Подтверждение сброса пароля: форма нового пароля """

    if request.method == 'POST':
        form = CustomSetPasswordForm(None, request.POST)  # user=None, валидация пароля без привязки к пользователю
        if form.is_valid():
            new_password = form.cleaned_data['new_password1']
            result = process_password_reset_confirm(uidb64, token, new_password)
            if result['success']:
                messages.success(request, result['message'])
                return redirect('login')
            else:
                messages.error(request, result['message'])
                return redirect('home')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
            context = {'form': form}
            return render(request, 'users/password_reset_confirm.html', context)
    else:

        form = CustomSetPasswordForm(None)
        context = {
            'form': form,
            'title': 'Создание нового пароля',
            'header': 'Создание нового пароля'
        }
        return render(request, 'users/password_reset_confirm.html', context)


# todo Вынести в сервис
@auth_required()
@owner_required()
def change_password(request, user_id):
    if request.method != 'POST':
        messages.error(request, 'Неожиданный запрос')
        return redirect('home')

    form = CustomPasswordChangeForm(request.user, request.POST)
    if form.is_valid():
        form.save()
        update_session_auth_hash(request, form.user)
        messages.success(request, 'Пароль успешно изменён.')
        return HttpResponseRedirect(reverse('view_profile', kwargs={'user_id': user_id}))
    else:
        # Возвращаем на страницу редактирования с ошибками
        # Нужно передать ошибки формы в контекст
        profile = request.user.profile
        edit_profile_form = EditProfileForm(instance=profile)
        context = {
            'title': 'Редактирование профиля',
            'header': f'Редактирование профиля {request.user.username}',
            'user_info': profile,
            'form': edit_profile_form,
            'password_form': form,
        }
        messages.error(request, 'Ошибка при смене пароля. Проверьте введённые данные.')
        return render(request, 'users/edit_profile.html', context)


# todo Вынести в сервис
def confirm_new_email(request, signed_value):
    """ Подтверждение нового email после смены """

    try:
        # Распаковываем значение: user_id:new_email
        data = signer.unsign(signed_value, max_age=172800)  # 2 дня
        user_id_str, new_email = data.split(':', 1)
        user_id = int(user_id_str)
        user = User.objects.get(id=user_id)
        profile = user.profile

        # Проверяем, что пользователь ожидает подтверждения этого email
        if profile.pending_email != new_email:
            messages.error(request, 'Недействительная ссылка.')
            return redirect('home')

        # Обновляем email и активируем
        user.email = new_email
        user.save()
        profile.is_activated = True
        profile.pending_email = None
        profile.save()

        messages.success(request, 'Email успешно изменён и подтверждён.')
        return redirect('view_profile', user_id=user.id)

    except SignatureExpired:
        messages.error(request, 'Срок действия ссылки истёк. Запросите смену email повторно.')
        return redirect('home')
    except (BadSignature, ValueError, User.DoesNotExist):
        messages.error(request, 'Недействительная ссылка.')
        return redirect('home')

def view_profile(request: HttpRequest, user_id: int) -> HttpResponse:
    """ Просмотр профиля пользователя.
        У гостей профиля и хозяина выводятся разные данные.
        Если пользователь не авторизован, то информации по минимуму.
    """

    user = get_object_or_404(User, pk=user_id)
    if user == request.user:
        fight_history = FightHistory.objects.filter(Q(winner=user) | Q(loser=user)).order_by('-id')[:50]
        amulet = AmuletItem.objects.filter(card=user.profile.current_card).last()

        context = {'title': f'Просмотр профиля {user.username}',
                   'header': f'Просмотр профиля {user.username}',
                   'user_info': user,
                   'fight_history': fight_history,
                   'amulet': amulet
                   }
    else:
        if request.user.is_authenticated:
            favorite_user = FavoriteUsers.objects.filter(user=request.user.id, favorite_user=user_id).last()
            wins_vs_users = FightHistory.objects.filter(winner=request.user, loser=user).count()
            losses_vs_users = FightHistory.objects.filter(winner=user, loser=request.user).count()
            context = {'title': f'Просмотр профиля {user.username}',
                       'header': f'Просмотр профиля {user.username}',
                       'user_info': user,
                       'favorite_user': favorite_user,
                       'wins_vs_users': wins_vs_users,
                       'losses_vs_users': losses_vs_users,
                       }
        else:
            context = {'title': f'Просмотр профиля {user.username}',
                       'header': f'Просмотр профиля {user.username}',
                       'user_info': user,
                       }

    return render(request, 'users/view_profile.html', context)


def view_rating(request: HttpRequest) -> HttpResponse:
    """ Выводит таблицу рейтинга пользователей с учетом пагинации """

    try:
        page_num = int(request.GET.get('page', 1))
    except ValueError:
        page_num = 1
    users_data: dict = view_rating_service(page_num)
    context = {'title': 'Таблица рейтинга',
               'header': 'Таблица рейтинга',
               'users': users_data.get('users'),
               'page': users_data.get('page'),
               }

    return render(request, 'users/rating.html', context)


@auth_required()
@owner_required()
def edit_profile(request: HttpRequest, user_id: int) -> HttpResponseRedirect | HttpResponse:
    """ Изменение профиля пользователя
        При GET запросе выводит форму изменения профиля.
        При POST запросе и валидных данных изменяет данные в профиле.
        Вызывает сервис изменения данных профиля и направляет на страницу просмотра профиля.
        При невалидных данных снова показывает форму.
        При других запросах направляет на домашнюю страницу.
    """

    profile = Profile.objects.get(user=request.user.id)
    if request.method == 'POST':
        edit_profile_form = EditProfileForm(request.POST, request.FILES, instance=profile)
        if edit_profile_form.is_valid():
            about_user = edit_profile_form.cleaned_data['about_user']
            profile_pic = edit_profile_form.cleaned_data['profile_pic']
            new_email = edit_profile_form.cleaned_data.get('email')
            edit_profile_service(user_id, about_user, profile_pic)

            current_email = request.user.email
            if new_email and new_email != current_email:
                success, msg = change_user_email(user_id, new_email)
                if success:
                    messages.success(request, msg)
                else:
                    messages.error(request, msg)

            return HttpResponseRedirect(reverse('view_profile', kwargs={'user_id': user_id}))

        else:
            edit_profile_form = EditProfileForm(instance=profile, initial={'about_user': profile.about_user,
                                                                           'profile_pic': profile.profile_pic})
            messages.warning(request, 'Некорректные данные!')
            context = {'title': f'Редактирование профиля',
                       'header': f'Редактирование профиля {request.user.username}',
                       'user_info': profile,
                       'form': edit_profile_form,
                       }

            return render(request, 'users/edit_profile.html', context)
    elif request.method == 'GET':
        edit_profile_form = EditProfileForm(instance=profile,
                                            initial={'about_user': profile.about_user, 'profile_pic': profile.profile_pic})
        context = {'title': f'Редактирование профиля',
                   'header': f'Редактирование профиля {request.user.username}',
                   'user_info': profile,
                   'form': edit_profile_form,
                   }
        return render(request, 'users/edit_profile.html', context)

    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


@auth_required()
@owner_required()
def view_transactions(request: HttpRequest, user_id: int) -> HttpResponseRedirect | HttpResponse:
    """ Вывод истории движений денежных средств пользователя """

    transactions = Transactions.objects.filter(user_id=user_id).order_by('-date_and_time').annotate(
        result=F('after') - F('before'))[:250]
    context = {'title': f'Транзакции',
               'header': f'Транзакции пользователя {request.user.username}',
               'transactions': transactions,
               'user': request.user,
               }

    return render(request, 'users/transactions.html', context)


@auth_required()
def add_favorite_user(request: HttpRequest, user_id: int) -> HttpResponseRedirect:
    """ Добавление в избранное выбранного пользователя.
        Обрабатывает только POST запросы.
        Вызывает сервис для добавления в избранное.
        При ошибке направляет на главную страницу.
        При успехе направляет на страницу пользователя.
        Выводит пользователю сообщение об успехе или ошибке.
    """

    if request.method == 'POST':
        answer: dict = add_favorite_user_service(request.user.id, user_id)
        if answer.get('error_message'):
            messages.error(request, answer['error_message'])
            return HttpResponseRedirect(reverse('home'))
        else:
            messages.success(request, answer['success_message'])
            return HttpResponseRedirect(reverse('view_profile', kwargs={'user_id': user_id}))
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


@auth_required()
def delete_favorite_user(request: HttpRequest, user_id: int) -> HttpResponseRedirect:
    """ Удаление пользователя из списка избранных.
        Обрабатывает только POST запросы.
        Вызывает сервис для удаления пользователя из избранного.
        При ошибке направляет на главную страницу.
        При успехе направляет на страницу пользователя.
        Выводит пользователю сообщение об успехе или ошибке.
    """

    if request.method == 'POST':
        answer: dict = delete_favorite_user_service(request.user.id, user_id)
        if answer.get('error_message'):
            messages.error(request, answer['error_message'])
            return HttpResponseRedirect(reverse('home'))
        else:
            messages.success(request, answer['success_message'])
            return HttpResponseRedirect(reverse('view_profile', kwargs={'user_id': user_id}))
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


@auth_required()
def view_favorite_users(request: HttpRequest) -> HttpResponse:
    """ Вывод списка избранных пользователей """

    favorite_users = FavoriteUsers.objects.filter(user=request.user.id)
    context = {'title': f'Избранные пользователи',
               'header': f'Избранные пользователи {request.user.username}',
               'favorite_users': favorite_users,
               }

    return render(request, 'users/favorite_users.html', context)


