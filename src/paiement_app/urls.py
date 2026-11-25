from django.urls import path
from .views import (
    InitierPaiementView,
    LigdiCashCallbackView,
    StatutPaiementView,
    
)

from .views_paiement_livraison import (
    InitierPaiementLivraisonView,
    StatutPaiementLivraisonView,
    LigdiCashLivraisonCallbackView,
)

app_name = "paiement_app"

urlpatterns = [
    # Initiation du paiement (GET formulaire / POST soumission HTMX + toast)
    path(
        "commande/<uuid:reference>/initier/",
        InitierPaiementView.as_view(),
        name="initier-paiement",
    ),
    # Consultation du statut (page complète ou réponse HTMX/JSON pour le polling)
    path(
        "commande/<uuid:reference>/statut/",
        StatutPaiementView.as_view(),
        name="statut-paiement",
    ),
    # Endpoint de callback / webhook appelé par LigdiCash (sans CSRF)
    path(
        "callback/ligdicash/",
        LigdiCashCallbackView.as_view(),
        name="callback_ligdicash",
    ),
    
    # Flux Livraison (DemandeLivraison)
    path(
        "livraison/<uuid:reference>/initier/",
        InitierPaiementLivraisonView.as_view(),
        name="initier_livraison",
    ),
    path(
        "livraison/<uuid:reference>/statut/",
        StatutPaiementLivraisonView.as_view(),
        name="statut_livraison",
    ),
    path(
        "callback/livraison/",
        LigdiCashLivraisonCallbackView.as_view(),
        name="callback_livraison",
    ),
    
    
]