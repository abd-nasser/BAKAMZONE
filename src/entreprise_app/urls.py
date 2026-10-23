from django.urls import path

from .views import (
    ChoixPalierEntrepriseView,
    EntrepriseDetailView,
    InscriptionEntrepriseAdminView,
    InscriptionEntrepriseView,
)

app_name = "entreprise_app"

urlpatterns = [
    path("inscription/", InscriptionEntrepriseView.as_view(), name="inscription"),
    path(
        "administrateurs/inscription/",
        InscriptionEntrepriseAdminView.as_view(),
        name="inscription-admin",
    ),
    path("tableau-de-bord/", EntrepriseDetailView.as_view(), name="entreprise-detail"),
    path("abonnement/palier/", ChoixPalierEntrepriseView.as_view(), name="choix-palier"),
]
