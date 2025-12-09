import os

from celery import Celery
from celery.schedules import crontab

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'omg.omg.settings')

app = Celery('celery_project',
             broker='amqp://guest:guest@localhost:5672//'
             )

# app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='Europe/Moscow',
    enable_utc=False,
    result_expires=3600,
)

app.conf.broker_connection_retry_on_startup = True

app.conf.beat_schedule = {
    'run-func-1-every-day-month': {
        'task': 'celery.tasks.func_1',
        'schedule': crontab(day_of_month='8', hour=12, minute=19),
        # 'schedule': crontab(day_of_month='1', hour=0, minute=0),
    },
    'run-func-2-every-11-day-month': {
        'task': 'celery.tasks.func_2',
        'schedule': crontab(day_of_month='11', hour=0, minute=0),
    }
}
