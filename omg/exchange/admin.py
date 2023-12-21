from django.contrib import admin
from .models import SaleUserCards, ExperienceItems, UsersInventory, HistoryPurchaseItems


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


admin.site.register(SaleUserCards, SaleUserCardsAdmin)
admin.site.register(ExperienceItems, ExperienceItemsAdmin)
admin.site.register(UsersInventory, UsersInventoryAdmin)
admin.site.register(HistoryPurchaseItems, HistoryPurchaseItemsAdmin)
