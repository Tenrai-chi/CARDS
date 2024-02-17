from django.contrib import admin
from .models import Profile, Transactions, SaleStoreCards, FavoriteUsers, GuildBuff, Guild


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id',
                    'user',
                    'about_user',
                    'gold',
                    'receiving_timer',
                    'win',
                    'lose',
                    'current_card',
                    'is_activated',
                    'guild',
                    'date_guild_accession',
                    'guild_point')
    list_display_links = ('id', 'user')
    search_fields = ('id', 'user')


class TransactionsAdmin(admin.ModelAdmin):
    list_display = ('id', 'date_and_time', 'user', 'comment', 'before', 'after')


class SaleStoreCardsAdmin(admin.ModelAdmin):
    list_display = ('id', 'sold_card', 'transaction')


class FavoriteUsersAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'favorite_user')


class GuildBuffAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'numeric_value')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name')


class GuildAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'leader', 'number_of_participants', 'guild_pic', 'date_create', 'rating', 'buff', 'date_last_change_buff')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name')


admin.site.register(FavoriteUsers, FavoriteUsersAdmin)
admin.site.register(SaleStoreCards, SaleStoreCardsAdmin)
admin.site.register(Transactions, TransactionsAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(GuildBuff, GuildBuffAdmin)
admin.site.register(Guild, GuildAdmin)

