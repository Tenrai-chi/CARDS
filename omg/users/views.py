from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.core.paginator import Paginator
from django.views.generic import CreateView
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.db.models import F, Q

from .models import Profile
from .forms import LoginForm, RegistrationForm, EditProfileForm

from cards.models import FightHistory


def view_profile(request, user_id):
    """ Просмотр профиля пользователя """

    user = get_object_or_404(User, pk=user_id)
    if user == request.user:
        fight_history = FightHistory.objects.filter(Q(winner=user) | Q(loser=user)).order_by('-id')
        context = {'title': f'Просмотр профиля {user.username}',
                   'header': f'Просмотр профиля {user.username}',
                   'user_info': user,
                   'fight_history': fight_history,
                   }
    else:
        context = {'title': f'Просмотр профиля {user.username}',
                   'header': f'Просмотр профиля {user.username}',
                   'user_info': user
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
