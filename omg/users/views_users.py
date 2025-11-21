from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.db.models import F, Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.forms import Form
from django.http import HttpResponseRedirect, HttpResponse, HttpRequest
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView

from cards.models import Card, FightHistory
from common.decorators import auth_required, owner_required
from common.utils import date_time_now
from exchange.models import AmuletItem

from .forms import LoginForm, RegistrationForm, EditProfileForm
from .services_users import (add_favorite_user_service, delete_favorite_user_service, edit_profile_service,
                             view_rating_service, )
from .models import Profile, Transactions, FavoriteUsers


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


@receiver(post_save, sender=User)
def create_profile_user(sender, instance, created, **kwargs):
    """ Создание профиля пользователя.
        Создает профиль пользователя при создании экземпляра User.
    """

    if created and not Profile.objects.filter(user=instance).exists():
        Profile.objects.create(user=instance,
                               receiving_timer=date_time_now()
                               )


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
            edit_profile_service(user_id, about_user, profile_pic)

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
