from django.contrib import admin
from .models import Profile, Transactions, SaleStoreCards, FavoriteUsers


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id',
                    'user',
                    'about_user',
                    'gold',
                    'receiving_timer',
                    'win',
                    'lose',
                    'current_card',
                    'is_activated')
    list_display_links = ('id', 'user')
    search_fields = ('id', 'user')


class TransactionsAdmin(admin.ModelAdmin):
    list_display = ('id', 'date_and_time', 'user', 'comment', 'before', 'after')


class SaleStoreCardsAdmin(admin.ModelAdmin):
    list_display = ('id', 'sold_card', 'transaction')


class FavoriteUsersAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'favorite_user')


admin.site.register(FavoriteUsers, FavoriteUsersAdmin)
admin.site.register(SaleStoreCards, SaleStoreCardsAdmin)
admin.site.register(Transactions, TransactionsAdmin)
admin.site.register(Profile, ProfileAdmin)
