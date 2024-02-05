from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.db.models import F, Q

from .models import Profile, Transactions, FavoriteUsers
from .forms import LoginForm, RegistrationForm, EditProfileForm
from exchange.models import AmuletItem

from cards.models import FightHistory


def view_profile(request, user_id):
    """ Просмотр профиля пользователя """

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
        favorite_user = FavoriteUsers.objects.filter(user=request.user, favorite_user=user_id).last()
        wins_vs_users = FightHistory.objects.filter(winner=request.user, loser=user).count()
        losses_vs_users = FightHistory.objects.filter(winner=user, loser=request.user).count()
        context = {'title': f'Просмотр профиля {user.username}',
                   'header': f'Просмотр профиля {user.username}',
                   'user_info': user,
                   'favorite_user': favorite_user,
                   'wins_vs_users': wins_vs_users,
                   'losses_vs_users': losses_vs_users,
                   }

    return render(request, 'users/view_profile.html', context)


class CustomLoginView(LoginView):
    """ Авторизация пользователя """

    authentication_form = LoginForm
    template_name = 'users/login.html'
    extra_context = {'title': 'Авторизация на сайте',
                     'header': 'Авторизация на сайте',
                     }

    def get_success_url(self):
        return reverse_lazy('home')


class CustomRegistrationView(CreateView):
    """ Регистрация пользователя """

    form_class = RegistrationForm
    template_name = 'users/signup.html'
    extra_context = {'title': 'Регистрация на сайте',
                     'header': 'Регистрация на сайте',
                     }

    def get_success_url(self):
        return reverse_lazy('login')

    def form_valid(self, form):
        user = form.save()
        return super().form_valid(form)


def view_rating(request):
    """ Просмотр таблицы рейтинга пользователей """

    users = User.objects.all().annotate(rating=500 + F('profile__win') * 25 - F('profile__lose') * 20).order_by('-rating')
    context = {'title': 'Таблица рейтинга',
               'header': 'Таблица рейтинга',
               'users': users,
               }

    return render(request, 'users/rating.html', context)


def edit_profile(request, user_id):
    if user_id == request.user.id:
        profile = Profile.objects.get(user=request.user)

        if request.method == 'POST':
            edit_profile_form = EditProfileForm(request.POST, request.FILES, instance=profile)
            if edit_profile_form.is_valid():
                edit_profile_form.save()

                return HttpResponseRedirect(f'/users/{user_id}')
            else:
                edit_profile_form = EditProfileForm(instance=profile, initial={'about_user': profile.about_user,
                                                                               'profile_pic': profile.profile_pic})
                context = {'title': f'Редактирование профиля',
                           'header': f'Редактирование профиля {request.user.username}',
                           'user_info': profile,
                           'form': edit_profile_form,
                           }

                return render(request, 'users/edit_profile.html', context)
        else:
            edit_profile_form = EditProfileForm(instance=profile, initial={'about_user': profile.about_user,
                                                                           'profile_pic': profile.profile_pic})
            context = {'title': f'Редактирование профиля',
                       'header': f'Редактирование профиля {request.user.username}',
                       'user_info': profile,
                       'form': edit_profile_form,
                       }

            return render(request, 'users/edit_profile.html', context)
    else:
        messages.error(request, 'Вы не можете редактировать этот профиль!')

        return HttpResponseRedirect(reverse('home'))


def view_transactions(request, user_id):
    """ Выводит историю движений денежных средств пользователя
    """
    if request.user.is_authenticated and request.user.id == user_id:
        transactions = Transactions.objects.filter(user=request.user)
        context = {'title': f'Транзакции',
                   'header': f'Транзакции пользователя {request.user.username}',
                   'transactions': transactions,
                   'user': request.user,
                   }

        return render(request, 'users/transactions.html', context)

    else:
        messages.error(request, 'Произошла ошибка!')

        return HttpResponseRedirect(reverse('home'))


def add_favorite_user(request, user_id: int):
    """ Добавляет в избранное выбранного пользователя
    """
    if request.user.id != user_id:
        try:
            record = FavoriteUsers.objects.get(user=request.user, favorite_user=user_id)
            messages.error(request, 'Произошла ошибка!')

            return HttpResponseRedirect(reverse('home'))

        except FavoriteUsers.DoesNotExist:
            user = User.objects.filter(pk=user_id).last()
            favorite_users_count = FavoriteUsers.objects.filter(user=request.user).count()
            if favorite_users_count == 50:
                message = 'Достигнут предел избранных пользователей! Для добавления новых освободите место'
                messages.error(request, message)

                return HttpResponseRedirect(f'/users/{user_id}')
            if user:
                new_favorite_user = FavoriteUsers.objects.create(user=request.user,
                                                                 favorite_user=user)
                new_favorite_user.save()

                return HttpResponseRedirect(f'/users/{user_id}')
            else:
                messages.error(request, 'Произошла ошибка!')

                return HttpResponseRedirect(reverse('home'))

    else:
        messages.error(request, 'Произошла ошибка!')

        return HttpResponseRedirect(reverse('home'))


def delete_favorite_user(request, user_id):
    """ Удаляет пользователя из списка избранных
    """

    if request.user.id != user_id:
        try:
            record = FavoriteUsers.objects.get(user=request.user, favorite_user=user_id)
            record.delete()

            return HttpResponseRedirect(f'/users/{user_id}')

        except FavoriteUsers.DoesNotExist:
            messages.error(request, 'Произошла ошибка!')

            return HttpResponseRedirect(reverse('home'))
    else:
        messages.error(request, 'Произошла ошибка!')

        return HttpResponseRedirect(reverse('home'))


def view_favorite_users(request):
    """ Выводит список избранных пользователей.
    """

    favorite_users = FavoriteUsers.objects.filter(user=request.user)
    context = {'title': f'Избранные пользователи',
               'header': f'Избранные пользователи {request.user.username}',
               'favorite_users': favorite_users,
               }

    return render(request, 'users/favorite_users.html', context)

