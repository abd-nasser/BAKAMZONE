from django.urls import path

from clients_app.views import InscriptionClientView

app_name = 'clients_app'

urlpatterns = [
    path('inscription/', InscriptionClientView.as_view(), name='inscription-client'),
]
