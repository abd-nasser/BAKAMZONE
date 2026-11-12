from django.urls import path

from .views import (
    AjouterPanierView,
    DetailCommandeView,
    ModifierPanierView,
    PanierView,
    ValiderCommandeView,
    ViderPanierView,
)

app_name = "panier_app"

urlpatterns = [
    path("", PanierView.as_view(), name="panier"),
    path("valider/", ValiderCommandeView.as_view(), name="valider_commande"),
    path(
        "commande/<uuid:reference>/",
        DetailCommandeView.as_view(),
        name="detail_commande",
    ),
    path("ajouter/<int:article_id>/", AjouterPanierView.as_view(), name="ajouter_panier"),
    path("modifier/<int:ligne_id>/", ModifierPanierView.as_view(), name="modifier_panier"),
    path("vider/", ViderPanierView.as_view(), name="vider_panier"),
]
