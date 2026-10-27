from django.urls import path
from livreurs_app.views import (
    AccepterDemandeLivraisonView,
    ChangerStatutCourseView,
    InscriptionLivreurView,
    LivreurProfilViewByLivreur,
    RefuserDemandeLivraisonView,
    ToggleDisponibiliteLivreurView,
)

app_name = 'livreurs_app'

urlpatterns = [
    path('inscription/', InscriptionLivreurView.as_view(), name='inscription-livreur'),
    path('tableau-de-bord/', LivreurProfilViewByLivreur.as_view(), name='tableau-de-bord'),
    path('profil/', LivreurProfilViewByLivreur.as_view(), name='livreur-profil-perso'),
    path('disponibilite/', ToggleDisponibiliteLivreurView.as_view(), name='toggle-disponibilite'),
    path('demande/<int:pk>/accepter/', AccepterDemandeLivraisonView.as_view(), name='accepter-demande'),
    path('demande/<int:pk>/refuser/', RefuserDemandeLivraisonView.as_view(), name='refuser-demande'),
    path('demande/<int:pk>/statut/', ChangerStatutCourseView.as_view(), name='changer-statut-demande'),
]
