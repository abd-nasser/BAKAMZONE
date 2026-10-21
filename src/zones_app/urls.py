from django.urls import path

from zones_app.views import ZoneCreateView

app_name = 'zones_app'

urlpatterns = [
    path('creer/', ZoneCreateView.as_view(), name='creer-zone'),
]
