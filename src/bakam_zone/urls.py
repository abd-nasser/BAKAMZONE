from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from demande_livraison_app.views import DestinataireGeoView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home_app.urls', namespace='home_app')),
    path('auth/', include('auth_app.urls', namespace='auth_app')),
    path('superuser/', include('superuser_app.urls', namespace='superuser_app')),
    path('blocs/', include('blocs_app.urls', namespace='blocs_app')),
    path('admins/', include('admins_app.urls', namespace='admins_app')),
    path('livreurs/', include('livreurs_app.urls', namespace='livreurs_app')),
    path('zones/', include('zones_app.urls', namespace='zones_app')),
    path('clients/', include('clients_app.urls', namespace='clients_app')),
    path('entreprises/', include('entreprise_app.urls', namespace='entreprise_app')),
    path('articles/', include('articles_app.urls', namespace='articles_app')),
    path('demandes/', include('demande_livraison_app.urls', namespace='demande_livraison_app')),
    # Ephemeral PWA endpoint public pour la validation de position GPS par le destinataire (WhatsApp Smart-Drop)
    path('geo/verify/<uuid:token_pwa_destinataire>/', DestinataireGeoView.as_view(), name='destinataire-geo'),
]

if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    # Support rechargement à chaud navigateur
    urlpatterns += [path("__reload__/", include("django_browser_reload.urls"))]
    # Fichiers médias et statiques en local
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += staticfiles_urlpatterns()
