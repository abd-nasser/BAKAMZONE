from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home_app.urls', namespace='home_app')),
    path('auth/', include('auth_app.urls', namespace='auth_app')),
    path('superuser/', include('superuser_app.urls', namespace='superuser_app')),
]

if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    # Support rechargement à chaud navigateur
    urlpatterns += [path("__reload__/", include("django_browser_reload.urls"))]
    # Fichiers médias et statiques en local
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += staticfiles_urlpatterns()
