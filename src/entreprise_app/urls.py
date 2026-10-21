from django.urls import path

from .views import ChoixPalierEntrepriseView, InscriptionEntrepriseView

app_name = "entreprise_app"

urlpatterns = [
    path("inscription/", InscriptionEntrepriseView.as_view(), name="inscription"),
    path("abonnement/palier/", ChoixPalierEntrepriseView.as_view(), name="choix-palier"),
]
