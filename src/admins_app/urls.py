from django.urls import path

from admins_app.views import AdminBlocCreateView

app_name = 'admins_app'

urlpatterns = [
    path('creer/', AdminBlocCreateView.as_view(), name='creer-admin-bloc'),
]
