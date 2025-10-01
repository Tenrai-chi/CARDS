from django.urls import path

from .views import (item_store, view_inventory_user, buy_item, buy_amulet, sale_amulet,
                    buy_and_open_box_amulet, buy_and_open_box_book, buy_box_card, buy_upgrade_item,
                    menu_enhance_card, enhance_card)


urlpatterns = [

    path('store/box_amulet/', buy_and_open_box_amulet, name='buy_box_amulet'),
    path('store/buy_box_book/', buy_and_open_box_book, name='buy_box_book'),
    path('store/box_card/', buy_box_card, name='buy_box_card'),
    path('store/amulet-<int:amulet_id>/', buy_amulet, name='buy_amulet'),
    path('store/buy_upgrade_item-<int:upgrade_item_id>/', buy_upgrade_item, name='buy_upgrade_item'),

    path('store/<int:item_id>/', buy_item, name='buy_item'),
    path('store/<str:store_filter>/', item_store, name='items_store'),
    path('<int:user_id>/<str:inventory_filter>/', view_inventory_user, name='inventory_user'),
    path('<int:user_id>-sale-<int:amulet_id>/', sale_amulet, name='sale_amulet'),

    path('card-<int:card_id>/', menu_enhance_card, name='menu_enhance_card'),
    path('card-<int:card_id>/up_item-<int:up_item_id>', enhance_card, name='enhance_card'),
]
