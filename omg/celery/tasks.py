from celery import shared_task
from logging import getLogger

logger = getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def func_1(self):
    try:
        logger.warning('ЗАПУСК ФУНКЦИИ FUNC_1')
        print('ПУПУНЯ 1')
        logger.warning('КОНЕЦ ФУНКЦИИ FUNC_1')
    except Exception as e:
        logger.error('Произошла ошибка в запуске функции FUNC_1')
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def func_2(self):
    try:
        logger.warning('ЗАПУСК ФУНКЦИИ FUNC_2')
        print('ПУПУНЯ 2')
        logger.warning('КОНЕЦ ФУНКЦИИ FUNC_2')
    except Exception as e:
        logger.error('Произошла ошибка в запуске функции FUNC_2')
        raise self.retry(exc=e)

