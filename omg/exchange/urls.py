from django.urls import path
from .views import (item_store, view_inventory_user, buy_item, buy_amulet, sale_amulet,
                    buy_box_amulet, buy_box_book, buy_box_card)


urlpatterns = [
    path('store', item_store, name='items_store'),
    path('store/<int:item_id>', buy_item, name='buy_item'),
    path('store/box_amulet', buy_box_amulet, name='buy_box_amulet'),
    path('store/box_book', buy_box_book, name='buy_box_book'),
    path('store/box_card', buy_box_card, name='buy_box_card'),
    path('store/amulet-<int:amulet_id>', buy_amulet, name='buy_amulet'),
    path('<int:user_id>', view_inventory_user, name='inventory_user'),
    path('<int:user_id>-sale-<int:amulet_id>', sale_amulet, name='sale_amulet'),
]