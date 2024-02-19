from django.contrib import admin

from .models import ClassCard, Type, Rarity, Card, CardStore, FightHistory, HistoryReceivingCards


class CardAdmin(admin.ModelAdmin):
    list_display = ('id',
                    'owner',
                    'class_card',
                    'type',
                    'rarity',
                    'hp',
                    'damage',
                    'experience_bar',
                    'level',
                    'sale_status',
                    'price')


class RarityAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'drop_chance',
                    'max_level',
                    'min_damage',
                    'max_damage',
                    'min_hp',
                    'max_hp',
                    'coefficient_damage_for_level',
                    'coefficient_hp_for_level')


class ClassCardAdmin(admin.ModelAdmin):
    list_display = ('name', 'skill', 'description', 'description_for_history_fight', 'numeric_value', 'chance_use')


class CardStoreAdmin(admin.ModelAdmin):
    list_display = ('id', 'class_card', 'type', 'rarity', 'hp', 'damage', 'sale_now', 'price')
    list_display_links = ('id', 'class_card')
    search_fields = ('id', 'class_card')


class FightHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'date_and_time', 'winner', 'loser', 'card_winner', 'card_loser')
    list_display_links = ('id', 'date_and_time', 'winner', 'loser')
    search_fields = ('id', 'winner', 'loser')


class TypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'better', 'worst')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name')


class HistoryReceivingCardsAdmin(admin.ModelAdmin):
    list_display = ('id', 'date_and_time', 'card', 'user', 'method_receiving')
    list_display_links = ('id', 'date_and_time', 'card', 'user')
    search_fields = ('id', 'user', 'method_receiving')


admin.site.register(Type, TypeAdmin)
admin.site.register(HistoryReceivingCards, HistoryReceivingCardsAdmin)
admin.site.register(FightHistory, FightHistoryAdmin)
admin.site.register(Card, CardAdmin)
admin.site.register(ClassCard, ClassCardAdmin)
admin.site.register(Rarity, RarityAdmin)
admin.site.register(CardStore, CardStoreAdmin)
