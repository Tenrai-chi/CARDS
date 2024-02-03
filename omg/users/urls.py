from django.urls import path
from django.contrib.auth import views

from .views import view_profile, CustomLoginView, CustomRegistrationView, view_rating, edit_profile, view_transactions

urlpatterns = [
    path('<int:user_id>/', view_profile, name='view_profile'),
    path('<int:user_id>/transactions', view_transactions, name='view_transactions'),
    path('<int:user_id>/edit/', edit_profile, name='edit_profile'),
    path('rating/', view_rating, name='rating'),
    path('login', CustomLoginView.as_view(), name='login'),
    path('logout', views.LogoutView.as_view(template_name='users/logout.html'), name='logout'),
    path('signup/', CustomRegistrationView.as_view(), name='signup')
]
