from django.http import HttpResponseRedirect
from django.contrib import messages
from django.urls import reverse
from functools import wraps


def auth_required(error_message: str = 'Вы должны авторизоваться', redirect_url_name: str = 'home'):
    """ Декоратор проверки аутентификации у views.
        Используется у views, которые должны перенаправлять пользователя на другую страницу,
        при отсутствии аутентификации.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, error_message)
                return HttpResponseRedirect(reverse(redirect_url_name))
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def owner_required(error_message: str = 'У вас нет доступа к этому ресурсу', redirect_url_name: str = 'home'):
    """ Декоратор, который проверяет, является ли текущий пользователь владельцем ресурса.
        Используется у views, которые предоставляют информацию с ограниченным доступом.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            target_user_id = kwargs.get('user_id')
            if request.user.id != target_user_id:
                messages.error(request, error_message)
                return HttpResponseRedirect(reverse(redirect_url_name))
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
