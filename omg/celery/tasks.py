from celery import shared_task


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def func_1(self):
    try:
        print('ЗАПУСК ФУНКЦИИ ТЕСТ 1')
    except Exception as e:
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def func_2(self):
    try:
        print('ЗАПУСК ФУНКЦИИ ТЕСТ 2')
    except Exception as e:
        raise self.retry(exc=e)

