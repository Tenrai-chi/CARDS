import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'omg.omg.settings')

app = Celery('celery_project')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

app.conf.beat_schedule = {
    'run-func-1-every-day-month': {
        'task': 'celery.task.func_1',
        'schedule': crontab(day_of_month='5', hour=13, minute=0),
        # 'schedule': crontab(day_of_month='1', hour=0, minute=0),
    },
    'run-func-2-every-11-day-month': {
        'task': 'celery.task.func_2',
        'schedule': crontab(day_of_month='11', hour=0, minute=0),
    }
}
