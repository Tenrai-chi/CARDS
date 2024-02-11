from django.contrib import admin
from .models import SaleUserCards, ExperienceItems, UsersInventory
from .models import HistoryPurchaseItems, AmuletItem, AmuletType


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
                    'sale_now', 'chance_drop_on_fight', 'chance_drop_on_box')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name')


class AmuletItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'amulet_type', 'owner', 'card')
    list_display_links = ('id', 'amulet_type',)
    search_fields = ('id', 'amulet_type', 'owner', 'card')


admin.site.register(AmuletType, AmuletTypeAdmin)
admin.site.register(AmuletItem, AmuletItemAdmin)
admin.site.register(SaleUserCards, SaleUserCardsAdmin)
admin.site.register(ExperienceItems, ExperienceItemsAdmin)
admin.site.register(UsersInventory, UsersInventoryAdmin)
admin.site.register(HistoryPurchaseItems, HistoryPurchaseItemsAdmin)
