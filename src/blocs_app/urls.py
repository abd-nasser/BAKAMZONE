from django.urls import path

from blocs_app.views import BlocCreateView

app_name = 'blocs_app'

urlpatterns = [
    path('creer/', BlocCreateView.as_view(), name='creer-bloc'),
]
