from celery import shared_task

from django.contrib.auth.models import User
from .models import Transactions

from common.utils import date_time_now


@shared_task(acks_late=True)
def create_transaction_test():
    """ тестовая задача для celery """

    current_user = User.objects.get(id=1)
    new_transaction = Transactions.objects.create(user=current_user,
                                                  date_and_time=date_time_now(),
                                                  before=300,
                                                  after=300,
                                                  comment='TEST CELERY')
    new_transaction.save()
    return f"Transaction {new_transaction.id} created"
