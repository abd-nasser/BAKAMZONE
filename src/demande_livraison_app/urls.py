from django.urls import path
from demande_livraison_app.views import (
    CalculerTarifView,
    CreerDemandeLivraisonView,
)

app_name = 'demande_livraison_app'

urlpatterns = [
    path('creer/', CreerDemandeLivraisonView.as_view(), name='creer-demande'),
    path('calculer-tarif/', CalculerTarifView.as_view(), name='calculer-tarif'),
]
