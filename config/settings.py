import os
from pathlib import Path

from dotenv import load_dotenv
from django.contrib.messages import constants as messages

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
DEBUG = os.getenv('DEBUG')
#todo убрать нахуй
IN_DOCKER = os.getenv('IN_DOCKER', 'false') == 'true'

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

if IN_DOCKER:
    ROOT_URLCONF = 'config.urls'
else:
    ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'

if IN_DOCKER:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME'),
            'USER': os.getenv('DB_USER'),
            'PASSWORD': os.getenv('DB_USER_PASSWORD'),
            'HOST': 'host.docker.internal',
            'PORT': os.getenv('DB_PORT'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME'),
            'USER': os.getenv('DB_USER'),
            'PASSWORD': os.getenv('DB_USER_PASSWORD'),
            'HOST': os.getenv('DB_HOST'),
            'PORT': os.getenv('DB_PORT'),
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

# Celery + RabbitMQ + Redis
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST')
RABBITMQ_PORT = os.getenv('RABBITMQ_PORT')
RABBITMQ_USER = os.getenv('RABBITMQ_USER')
RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD')

REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = os.getenv('REDIS_PORT')
REDIS_DB = os.getenv('REDIS_DB')

CELERY_BROKER_URL = f'amqp://{RABBITMQ_USER}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}//'
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

CELERY_TIMEZONE = 'Europe/Moscow'

# Сериализация
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

# Redis
CELERY_REDIS_MAX_CONNECTIONS = 20
CELERY_REDIS_RETRY_ON_TIMEOUT = True
CELERY_RESULT_EXPIRES = 86400  # 24 часа

# Повторные попытки при падении
CELERY_TASK_MAX_RETRIES = 3  # Пока 3
CELERY_TASK_RETRY_DELAY = 60
CELERY_TASK_RETRY_BACKOFF = True  # Увеличение времени между попытками
CELERY_TASK_RETRY_BACKOFF_MAX = 600  # Максимальное время между попытками

# Подтверждение задач
CELERY_TASK_ACKS_LATE = True  # Подтверждение только после выполнения задачи
CELERY_TASK_REJECT_ON_WORKER_LOST = True  # Переотправка задачи при падении воркера
CELERY_TASK_TRACK_STARTED = True  # Отслеживание статуса задач

# Брокер
CELERY_BROKER_CONNECTION_TIMEOUT = 30  # default 4 (если сеть нестабильная)
CELERY_BROKER_HEARTBEAT = 10  # Проверка соединения каждые 10 секунд
CELERY_BROKER_POOL_LIMIT = 10  # Пул соединений

# Результаты
CELERY_TASK_IGNORE_RESULT = False
CELERY_TASK_STORE_ERRORS_EVEN_IF_IGNORED = True  # Для отладки сохранение ошибок


