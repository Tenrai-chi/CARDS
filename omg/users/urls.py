from django.urls import path
from django.contrib.auth import views

from .views import (view_profile, CustomLoginView, CustomRegistrationView, view_rating, edit_profile,
                    view_transactions, add_favorite_user, delete_favorite_user, view_favorite_users,
                    create_guild, view_guild, view_all_guilds, delete_member_guild)

urlpatterns = [
    path('<int:user_id>/', view_profile, name='view_profile'),
    path('<int:user_id>/transactions/', view_transactions, name='view_transactions'),
    path('<int:user_id>/edit/', edit_profile, name='edit_profile'),
    path('<int:user_id>/add_favorite/', add_favorite_user, name='add_favorite_user'),
    path('<int:user_id>/delete_favorite/', delete_favorite_user, name='delete_favorite_user'),
    path('rating/', view_rating, name='rating'),
    path('guilds/', view_all_guilds, name='view_all_guilds'),
    path('guilds/create/', create_guild, name='create_guild'),
    path('guilds/<int:guild_id>/', view_guild, name='view_guild'),
    path('guilds/<int:guild_id>-<int:member_id>', delete_member_guild, name='remove_member_guild'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(template_name='users/logout.html'), name='logout'),
    path('signup/', CustomRegistrationView.as_view(), name='signup'),
    path('favorite_users/', view_favorite_users, name='view_favorite_users')
]
