from django.conf.urls.static import static
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from cards.views import home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('cards/', include('cards.urls')),
    path('users/', include('users.urls')),
    path('inventory/', include('exchange.urls')),
    path('', home, name='home'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
