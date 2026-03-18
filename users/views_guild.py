from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse, HttpRequest
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from common.decorators import auth_required

from .forms import CreateGuildForm, EditGuildInfoForm
from .services_guild import (change_leader_guild_service, delete_guild_service, delete_member_guild_service,
                             add_member_guild_service, edit_guild_info_service, create_guild_service,
                             view_all_guilds_service)
from .models import Profile, Guild


def view_guild(request: HttpRequest, guild_id: int) -> HttpResponse:
    """ Просмотр информации о выбранной гильдии """

    guild_info = get_object_or_404(Guild, pk=guild_id)
    guild_participants = Profile.objects.filter(guild=guild_id).order_by('-guild_point')

    context = {'title': f'Избранные пользователи',
               'header': f'Избранные пользователи {request.user.username}',
               'guild_info': guild_info,
               'guild_participants': guild_participants
               }

    return render(request, 'users/view_guild.html', context)


def view_all_guilds(request: HttpRequest) -> HttpResponse:
    """ Вывод списка всех существующих гильдий с пагинацией. """

    try:
        page_num = int(request.GET.get('page', 1))
    except ValueError:
        page_num = 1
    guilds_data: dict = view_all_guilds_service(page_num)
    context = {'title': 'Таблица рейтинга',
               'header': 'Таблица рейтинга',
               'guilds': guilds_data.get('guilds'),
               'page': guilds_data.get('page'),
               }

    return render(request, 'users/view_all_guilds.html', context)


@auth_required(error_message='Для создания гильдии необходимо авторизоваться!')
def create_guild(request: HttpRequest) -> HttpResponse | HttpResponseRedirect:
    """ Создание гильдии.
        При GET запросе выводит форму для создания гильдии.
        При POST запросе и валидных данных вызывает сервис создания гильдии.
        При невалидных данных снова выводит форму.
        При ошибке направляет на домашнюю страницу.
        При успехе направляет на страницу просмотра созданной гильдии.
        При других запросах направляет на домашнюю страницу.
    """

    if request.method == 'POST':
        new_guild_form = CreateGuildForm(request.POST, request.FILES)
        if new_guild_form.is_valid():
            buff = new_guild_form.cleaned_data.get('buff')
            guild_pic = new_guild_form.cleaned_data.get('guild_pic')
            name = new_guild_form.cleaned_data.get('name')
            answer: dict = create_guild_service(request.user.id, name, guild_pic, buff)
            if answer.get('error_message'):
                messages.error(request, answer['error_message'])
                return HttpResponseRedirect(reverse('home'))

            else:
                messages.success(request, answer['success_message'])
                return HttpResponseRedirect(reverse('view_guild', kwargs={'guild_id': answer['guild_id']}))

        else:
            messages.error(request, 'Некорректные данные')
            context = {'title': f'Создание гильдии',
                       'header': f'Создание гильдии',
                       'form': new_guild_form,
                       }

            return render(request, 'users/create_guild.html', context)

    elif request.method == 'GET':
        form = CreateGuildForm()
        context = {'title': f'Создание гильдии',
                   'header': f'Создание гильдии',
                   'form': form,
                   }
        return render(request, 'users/create_guild.html', context)
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


@auth_required()
def edit_guild_info(request: HttpRequest, guild_id: int) -> HttpResponse | HttpResponseRedirect:
    """ Редактирование информации о гильдии.
        При GET запросе выводит форму изменения информации гильдии.
        При POST запросе и валидных данных вызывает сервис изменения информации гильдии.
        При ошибке выводит сообщение пользователю.
        Направляет на страницу просмотра гильдии.
        При других запросах направляет на домашнюю страницу.
    """

    guild_info = get_object_or_404(Guild, pk=guild_id)
    if request.method == 'POST':
        edit_guild_info_form = EditGuildInfoForm(request.POST, request.FILES, instance=guild_info)
        if edit_guild_info_form.is_valid():
            buff = edit_guild_info_form.cleaned_data.get('buff')
            guild_pic = edit_guild_info_form.cleaned_data.get('guild_pic')
            name = edit_guild_info_form.cleaned_data.get('name')
            answer: dict = edit_guild_info_service(request.user.id, guild_id, name, guild_pic, buff)
            if answer.get('error_message'):
                messages.error(request, answer['error_message'])
            return HttpResponseRedirect(reverse('view_guild', kwargs={'guild_id': guild_info.id}))
        else:
            messages.error(request, 'Некорректные данные!')

            context = {'title': f'Редактирование гильдии {guild_info.name}',
                       'header': f'Редактирование гильдии {guild_info.name}',
                       'guild_info': guild_info,
                       'form': edit_guild_info_form,
                       }
            return render(request, 'users/edit_guild.html', context)

    elif request.method == 'GET':
        edit_guild_info_form = EditGuildInfoForm(instance=guild_info,
                                                 initial={'name': guild_info.name,
                                                          'guild_pic': guild_info.guild_pic,
                                                          'buff': guild_info.buff})

        context = {'title': f'Редактирование гильдии {guild_info.name}',
                   'header': f'Редактирование гильдии {guild_info.name}',
                   'guild_info': guild_info,
                   'form': edit_guild_info_form,
                   }
        return render(request, 'users/edit_guild.html', context)
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


@auth_required()
def change_leader_guild_choice(request: HttpRequest, guild_id: int) -> HttpResponse | HttpResponseRedirect:
    """ Меню смены лидера гильдии.
        Выводит всех доступных для передачи лидерства участников гильдии.
    """

    guild_info = get_object_or_404(Guild, pk=guild_id)
    if request.user == guild_info.leader:
        guild_members = Profile.objects.exclude(user=request.user.id).filter(guild=guild_id)
        context = {'title': f'Смена лидера',
                   'header': f'Смена лидера',
                   'guild_members': guild_members,
                   'guild_info': guild_info,
                   }

        return render(request, 'users/change_leader_guild_choice.html', context)

    else:
        messages.error(request, 'У вас нет таких прав!')
        return HttpResponseRedirect(reverse('home'))


@auth_required()
def change_leader_guild(request: HttpRequest, guild_id: int, user_id: int) -> HttpResponseRedirect:
    """ Смена лидера гильдии на выбранного пользователя.
        Обрабатывает только POST запросы.
        Вызывает сервис для смены лидера.
        При ошибке направляет на домашнюю страницу.
        При удаче направляет на страницу просмотра гильдии.
        Выводит пользователю сообщение об успехе или ошибке.
    """

    if request.method == 'POST':
        answer: dict = change_leader_guild_service(request.user.id, guild_id, user_id)
        if answer.get('error_message'):
            messages.error(request, answer['error_message'])
            return HttpResponseRedirect(reverse('home'))

        else:
            messages.success(request, answer['success_message'])
            return HttpResponseRedirect(reverse('view_guild', kwargs={'guild_id': guild_id}))

    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


@auth_required()
def delete_member_guild(request: HttpRequest, member_id: int, guild_id: int) -> HttpResponseRedirect:
    """ Удаление пользователя из гильдии.
        Обрабатывает только POST запросы.
        Вызывает сервис удаление пользователя.
        Если был получен параметр redirect_name_url, то направляет на эту страницу (просмотр всех гильдий)
        Если параметр не был получен, то направляет на страницу просмотра гильдии.
        Выводит пользователю сообщение об успехе или ошибке.
    """

    if request.method == 'POST':
        answer: dict = delete_member_guild_service(request.user.id, member_id, guild_id)
        if answer.get('error_message'):
            messages.error(request, answer['error_message'])
        else:
            messages.success(request, answer['success_message'])

        if answer.get('redirect_name_url'):
            return HttpResponseRedirect(reverse(answer['redirect_name_url']))
        else:
            return HttpResponseRedirect(reverse('view_guild', kwargs={'guild_id': guild_id}))
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


@auth_required()
def add_member_guild(request: HttpRequest, guild_id: int) -> HttpResponseRedirect:
    """ Вступление в гильдию текущим пользователем.
        Обрабатывает только POST запросы.
        Вызывает сервис добавления пользователя в гильдию.
        При ошибке направляет на домашнюю страницу.
        При успехе направляет на страницу просмотра гильдии.
        Выводит пользователю сообщение об успехе или ошибке.
    """

    if request.method == 'POST':
        answer: dict = add_member_guild_service(request.user.id, guild_id)
        if answer.get('error_message'):
            messages.error(request, answer['error_message'])
            return HttpResponseRedirect(reverse('home'))
        else:
            messages.success(request, answer['success_message'])
            return HttpResponseRedirect(reverse('view_guild', kwargs={'guild_id': guild_id}))
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))


@auth_required()
def delete_guild(request: HttpRequest, guild_id: int) -> HttpResponseRedirect:
    """ Расформирование гильдии.
        Обрабатывает только POST запросы.
        Вызывает сервис удаления гильдии.
        При ошибке направляет на домашнюю страницу.
        При успехе направляет на страницу просмотра всех гильдий.
        Выводит пользователю сообщение об успехе или ошибке.
    """

    if request.method == 'POST':
        answer: dict = delete_guild_service(request.user.id, guild_id)
        if answer.get('error_message'):
            messages.error(request, answer['error_message'])
            return HttpResponseRedirect(reverse('home'))
        else:
            messages.success(request, answer['success_message'])
            return HttpResponseRedirect(reverse('view_all_guilds'))
    else:
        messages.error(request, 'Неожиданный запрос')
        return HttpResponseRedirect(reverse('home'))