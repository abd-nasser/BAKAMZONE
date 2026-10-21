from django.urls import path

from livreurs_app.views import InscriptionLivreurView

app_name = 'livreurs_app'

urlpatterns = [
    path('inscription/', InscriptionLivreurView.as_view(), name='inscription-livreur'),
]
