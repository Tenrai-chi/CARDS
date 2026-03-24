from django.urls import path
from django.contrib.auth import views

from .views_users import (view_profile, CustomLoginView, CustomRegistrationView, view_rating, edit_profile,
                          view_transactions, add_favorite_user, delete_favorite_user, view_favorite_users,
                          verify_email, resend_verification, password_reset_request, password_reset_confirm,
                          change_password, confirm_new_email)

from .views_guild import (create_guild, view_guild, view_all_guilds, delete_member_guild,
                          add_member_guild, change_leader_guild_choice, change_leader_guild,
                          edit_guild_info, delete_guild)

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(next_page='home'), name='logout'),
    path('signup/', CustomRegistrationView.as_view(), name='signup'),

    path('<int:user_id>/', view_profile, name='view_profile'),
    path('<int:user_id>/transactions/', view_transactions, name='view_transactions'),
    path('<int:user_id>/edit/', edit_profile, name='edit_profile'),
    path('favorite_users/', view_favorite_users, name='view_favorite_users'),
    path('<int:user_id>/add_favorite/', add_favorite_user, name='add_favorite_user'),
    path('<int:user_id>/delete_favorite/', delete_favorite_user, name='delete_favorite_user'),

    path('rating/', view_rating, name='rating'),
    path('guilds/', view_all_guilds, name='view_all_guilds'),
    path('guilds/create/', create_guild, name='create_guild'),
    path('guilds/<int:guild_id>/', view_guild, name='view_guild'),
    path('guilds/<int:guild_id>/delete', delete_guild, name='delete_guild'),
    path('guilds/<int:guild_id>/edit/', edit_guild_info, name='edit_guild_info'),
    path('guilds/<int:guild_id>/change_leader_guild_choice/', change_leader_guild_choice, name='change_leader_guild_choice'),
    path('guilds/<int:guild_id>/<int:user_id>/change_leader_guild/', change_leader_guild, name='change_leader_guild'),
    path('guilds/<int:guild_id>/join/', add_member_guild, name='add_member_guild'),
    path('guilds/<int:guild_id>-<int:member_id>/', delete_member_guild, name='remove_member_guild'),

    path('verify/<str:signed_value>/', verify_email, name='verify_email'),
    path('resend_verification/', resend_verification, name='resend_verification'),
    path('password_reset/', password_reset_request, name='password_reset'),
    path('reset/<uidb64>/<token>/', password_reset_confirm, name='password_reset_confirm'),
    path('change-password/<int:user_id>/', change_password, name='change_password'),
    path('confirm-new-email/<str:signed_value>/', confirm_new_email, name='confirm_new_email'),
]
