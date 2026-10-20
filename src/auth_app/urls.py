from django.urls import path
from auth_app.views import ConnexionHTMXView, DeconnexionView

app_name = 'auth_app'

urlpatterns = [
    path('connexion-htmx/', ConnexionHTMXView.as_view(), name='connexion_htmx'),
    path('deconnexion/', DeconnexionView.as_view(), name='deconnexion'),
]
