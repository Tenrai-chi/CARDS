from django.contrib import admin
from .models import (SaleUserCards, ExperienceItems, UsersInventory,
                     HistoryPurchaseItems, AmuletItem, AmuletType, AmuletRarity,
                     UpgradeItemsType, UpgradeItemsUsers, InitialEventAwards)


class SaleUserCardsAdmin(admin.ModelAdmin):
    list_display = ('id',
                    'date_and_time',
                    'buyer',
                    'salesman',
                    'card',
                    'price',
                    'transaction_buyer',
                    'transaction_salesman')


class ExperienceItemsAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'rarity', 'experience_amount', 'price', 'gold_for_use',
                    'chance_drop_on_fight', 'chance_drop_on_box', 'sale_now')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name')


class UsersInventoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'item', 'amount')
    list_display_links = ('id', 'owner', 'item')
    search_fields = ('id', 'name', 'item')


class HistoryPurchaseItemsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'date_and_time', 'item', 'amount', 'transaction')
    list_display_links = ('id', 'user')
    search_fields = ('id', 'date_and_time', 'user', 'item')


class AmuletTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'rarity', 'bonus_hp', 'bonus_damage', 'price',
                    'sale_now', 'discount', 'discount_now')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name')


class AmuletItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'amulet_type', 'owner', 'card', 'upgrades')
    list_display_links = ('id', 'amulet_type',)
    search_fields = ('id', 'amulet_type', 'owner', 'card')


class AmuletRarityAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'chance_drop_on_fight', 'chance_drop_on_box', 'max_upgrade')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name')


class UpgradeItemsTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'type', 'amount_up')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name')


class UpgradeItemsUsersAdmin(admin.ModelAdmin):
    list_display = ('id', 'upgrade_item_type', 'owner', 'amount')
    list_display_links = ('id', 'upgrade_item_type')
    search_fields = ('id', 'upgrade_item_type')


class InitialEventAwardsAdmin(admin.ModelAdmin):
    list_display = ('id', 'day_event_visit', 'type_award', 'amount_or_rarity_award', 'description')
    list_display_links = ('id',)
    search_fields = ('id', 'type_award', 'description')


admin.site.register(InitialEventAwards, InitialEventAwardsAdmin)
admin.site.register(UpgradeItemsUsers, UpgradeItemsUsersAdmin)
admin.site.register(UpgradeItemsType, UpgradeItemsTypeAdmin)
admin.site.register(AmuletRarity, AmuletRarityAdmin)
admin.site.register(AmuletType, AmuletTypeAdmin)
admin.site.register(AmuletItem, AmuletItemAdmin)
admin.site.register(SaleUserCards, SaleUserCardsAdmin)
admin.site.register(ExperienceItems, ExperienceItemsAdmin)
admin.site.register(UsersInventory, UsersInventoryAdmin)
admin.site.register(HistoryPurchaseItems, HistoryPurchaseItemsAdmin)
