from django.urls import path

from .views import (
    ChoixPalierEntrepriseView,
    DemanderRetraitEntrepriseView,
    EntrepriseDetailView,
    EntrepriseLivraisonsArticlesView,
    EntrepriseSoldeView,
    CreerLivraisonCommandeEntrepriseView,
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
    path("solde/", EntrepriseSoldeView.as_view(), name="solde"),
    path(
        "solde/demander-retrait/",
        DemanderRetraitEntrepriseView.as_view(),
        name="demander-retrait",
    ),
    path(
        "livraisons/articles/",
        EntrepriseLivraisonsArticlesView.as_view(),
        name="livraisons-articles",
    ),
    path(
        "livraisons/commandes/<int:commande_id>/creer/",
        CreerLivraisonCommandeEntrepriseView.as_view(),
        name="creer-livraison-commande",
    ),
    path("abonnement/palier/", ChoixPalierEntrepriseView.as_view(), name="choix-palier"),
]
