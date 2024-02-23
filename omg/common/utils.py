import pytz

from datetime import datetime

def date_time_now():
    """ Возвращает текущее время по Московскому часовому поясу.
    """

    date_time = datetime.now(pytz.timezone('Europe/Moscow'))

    return date_time