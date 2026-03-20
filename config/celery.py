import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('cards_celery')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'prepare_purchases_for_battle_event': {
        'task': 'exchange.tasks.preparation_battle_event',
        'schedule': crontab(day_of_month='1', hour=0, minute=0),
    },
    'accrual_of_reward_in_battle_event': {
        'task': 'exchange.tasks.accrual_of_reward',
        'schedule': crontab(day_of_month='11', hour=0, minute=0),
    },
    # 'create-transaction-test': {
    #     'task': 'users.tasks.create_transaction_test',
    #     'schedule': crontab(minute='*/1'),
    # },
}
