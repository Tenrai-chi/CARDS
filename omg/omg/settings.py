import os
from pathlib import Path

from django.conf.global_settings import LOGGING, SECRET_KEY
from dotenv import load_dotenv
from django.contrib.messages import constants as messages

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
DEBUG = os.getenv('DEBUG')

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'users.apps.UsersConfig',
    'cards.apps.CardsConfig',
    'exchange.apps.ExchangeConfig'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'omg.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [(os.path.join(BASE_DIR, 'templates'))],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'omg.wsgi.application'

# Для докера
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': os.getenv('DB_NAME'),
#         'USER': os.getenv('DB_USER'),
#         'PASSWORD': os.getenv('DB_USER_PASSWORD'),
#         # Для запуска через docker
#         'HOST': 'host.docker.internal',
#
#         # 'HOST': os.getenv('DB_HOST'),  # DB_HOST,
#         'PORT': os.getenv('DB_PORT'),
#     }
# }

# Для обычного запуска
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('db_name'),  # DB_NAME
        'USER': os.getenv('db_user'),  # DB_USER
        'PASSWORD': os.getenv('db_user_password'),  # DB_USER_PASSWORD
        'HOST': os.getenv('db_host'),  # DB_HOST
        'PORT': os.getenv('db_port'),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'ru'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

ABSOLUTE_URL_OVERRIDES = {
    #'bboard.rubric': lambda rec: "/bboard/%s/" % rec.pk,
}

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

MESSAGE_TAGS = {
    messages.DEBUG: 'alert-secondary',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console_handler': {
            'class': 'logging.StreamHandler',
            'formatter': 'console_formatter',
        },
        'django_server_handler': {
            'class': 'logging.StreamHandler',
            'formatter': 'django_server_formatter',
            'level': 'INFO',
        },
    },
    'formatters': {
        'console_formatter': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'datefmt': '%d/%b/%Y %H:%M:%S',
            'style': '{',
        },
        'django_server_formatter': {
            'format': '[{asctime}] {levelname} {message}',
            'datefmt': '%d/%b/%Y %H:%M:%S',
            'style': '{',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console_handler'],
            'level': 'INFO',
        },
        'django': {
            'handlers': ['django_server_handler'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['django_server_handler'],
            'level': 'INFO',
            'propagate': False,
        },
        'cards': {
            'handlers': ['console_handler'],
            'level': 'WARNING',
            'propagate': False,
        },
        'exchange': {
            'handlers': ['console_handler'],
            'level': 'WARNING',
            'propagate': False,
        },
        'users': {
            'handlers': ['console_handler'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672//'
CELERY_RESULT_BACKEND = 'rpc://'
