from django.conf.urls.static import static
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from cards.views import (home, get_award_start_event, menu_team_template_battle_event,
                         set_team_template_battle_event, fight_day_battle_event)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('cards/', include('cards.urls')),
    path('users/', include('users.urls')),
    path('battle_event_fight-<int:enemy_id>/', fight_day_battle_event, name='fight_day_battle_event'),
    path('inventory/', include('exchange.urls')),
    path('get_start_event_award', get_award_start_event, name='get_start_event_award'),
    path('be-team-menu/<int:place>/', menu_team_template_battle_event, name='be_team_menu'),
    path('be-team-set/<int:place>-<int:current_card_id>/', set_team_template_battle_event, name='be_team_set'),
    path('<str:theme>/', home, name='home'),
    path('', home, name='home'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
