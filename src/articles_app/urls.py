from django.urls import path

from .views import (
    AjouteArticleView,
    EntrepriseArticleDeleteView,
    EntrepriseArticleListeView,
    EntrepriseArticleUpdateView,
)

app_name = "articles_app"

urlpatterns = [
    path("ajouter/", AjouteArticleView.as_view(), name="ajoute_article"),
    path("entreprise/", EntrepriseArticleListeView.as_view(), name="entreprise_articles"),
    path("<int:pk>/modifier/", EntrepriseArticleUpdateView.as_view(), name="modifier_article"),
    path("<int:pk>/supprimer/", EntrepriseArticleDeleteView.as_view(), name="supprimer_article"),
]
