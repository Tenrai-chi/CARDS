from .models import Profile, Transactions

from common.utils import date_time_now
from common.utils import create_new_card


def user_level_up(user_id: int) -> None:
    """ Увеличение уровня и количества слотов для карт и амулетов """

    profile = Profile.objects.get(user=user_id)
    profile.level += 1
    profile.card_slots += 5
    profile.amulet_slots += 8

    profile.gold += 2000
    Transactions.objects.create(date_and_time=date_time_now(),
                                user=profile.user,
                                before=profile.gold - 2000,
                                after=profile.gold,
                                comment='Награда за повышение уровня'
                                )

    profile.save()

    if profile.level % 5 == 0:
        create_new_card(profile.user, ur_box=True)