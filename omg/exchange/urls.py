from django.urls import path
from .views import item_store, view_inventory_user, buy_item, buy_amulet


urlpatterns = [
    path('store', item_store, name='items_store'),
    path('store/<int:item_id>', buy_item, name='buy_item'),
    path('store/amulet-<int:amulet_id>', buy_amulet, name='buy_amulet'),
    path('<int:user_id>', view_inventory_user, name='inventory_user'),
]