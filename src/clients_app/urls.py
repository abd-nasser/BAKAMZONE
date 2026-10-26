from django.urls import path

from clients_app.views import (
    ClientDashboardView,
    InscriptionClientView,
    LivreurProfilViewByClient,
)

app_name = 'clients_app'

urlpatterns = [
    path('inscription/', InscriptionClientView.as_view(), name='inscription-client'),
    path('tableau-de-bord/', ClientDashboardView.as_view(), name='tableau-de-bord'),
    path(
        'livreur/<int:pk>/profil/',
        LivreurProfilViewByClient.as_view(),
        name='profil-livreur',
    ),
]
