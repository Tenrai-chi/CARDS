from django.urls import path
from .views import (view_cards, view_user_cards, view_card, card_store, buy_card, get_card,
                    create_card, card_sale, buy_card_user, view_user_cards_for_sale,
                    select_favorite_card, fight, card_level_up, level_up_with_item,
                    remove_from_sale_card, view_all_sale_card)

from exchange.views import change_amulet_menu, remove_amulet, change_amulet

urlpatterns = [
    path('card_store/', card_store, name='card_store'),
    path('get_card/', get_card, name='get_card'),
    path('all_sale_cards/', view_all_sale_card, name='view_all_sale_card'),
    path('fight-<int:protector_id>/', fight, name='fight'),
    path('<int:card_id>-buy/', buy_card, name='buy_card'),

    path('user_cards-<int:user_id>/', view_user_cards, name='user_cards'),
    path('user_cards-<int:user_id>/sale/', view_user_cards_for_sale, name='user_cards_sale'),

    path('card_sale-<int:card_id>/', card_sale, name='card_sale'),
    path('card_resale-<int:card_id>/', remove_from_sale_card, name='remove_from_sale_card'),
    path('card_sale-<int:card_id>/buy/', buy_card_user, name='buy_card_user'),

    path('card-<int:card_id>/', view_card, name='card'),
    path('card-<int:card_id>/amulets', change_amulet_menu, name='change_amulet_menu'),
    path('card-<int:card_id>/amulets/remove-<int:amulet_id>', remove_amulet, name='remove_amulet'),
    path('card-<int:card_id>/amulets/change-<int:amulet_id>', change_amulet, name='change_amulet'),
    path('card-<int:card_id>/level_up/', card_level_up, name='level_up'),
    path('card-<int:card_id>/level_up/<int:item_id>/', level_up_with_item, name='level_up_with_item'),

    path('ffflx/', create_card, name='create_card'),
    path('aw<int:selected_card>aw/', select_favorite_card, name='select_favorite_card'),
    path('', view_cards, name='cards'),
]
