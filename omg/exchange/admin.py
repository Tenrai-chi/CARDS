from django.contrib import admin
from .models import SaleUserCards, ExperienceItems, UsersInventory
from .models import HistoryPurchaseItems, AmuletItem, AmuletStore, AmuletType


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
    list_display = ('id', 'name', 'experience_amount', 'price', 'gold_for_use', 'chance_drop_on_fight', 'sale_now')
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
    list_display = ('id', 'name', 'rarity',)
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name')


class AmuletItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'amulet_type', 'owner', 'card', 'bonus_hp', 'bonus_damage', 'sale_status', 'price')
    list_display_links = ('id', 'amulet_type',)
    search_fields = ('id', 'amulet_type', 'owner', 'card')


class AmuletStoreAdmin(admin.ModelAdmin):
    list_display = ('id', 'amulet_type', 'bonus_hp', 'bonus_damage', 'price', 'sale_now',)
    list_display_links = ('id', 'amulet_type')
    search_fields = ('id', 'amulet_type', 'price')


admin.site.register(AmuletType, AmuletTypeAdmin)
admin.site.register(AmuletItem, AmuletItemAdmin)
admin.site.register(AmuletStore, AmuletStoreAdmin)
admin.site.register(SaleUserCards, SaleUserCardsAdmin)
admin.site.register(ExperienceItems, ExperienceItemsAdmin)
admin.site.register(UsersInventory, UsersInventoryAdmin)
admin.site.register(HistoryPurchaseItems, HistoryPurchaseItemsAdmin)
