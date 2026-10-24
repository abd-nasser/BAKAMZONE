from django.urls import path

from .views import (
    AjouteArticleView,
    ArticleBlocAdminCreateView,
    ArticleBlocAdminDeleteView,
    ArticleBlocAdminUpdateView,
    EntrepriseArticleDeleteView,
    EntrepriseArticleListeView,
    EntrepriseArticleUpdateView,
)

app_name = "articles_app"

urlpatterns = [
    path("ajouter/", AjouteArticleView.as_view(), name="ajoute_article"),
    path(
        "gestionnaire/entreprises/<int:entreprise_pk>/articles/ajouter/",
        ArticleBlocAdminCreateView.as_view(),
        name="bloc-admin-ajouter-article",
    ),
    path(
        "gestionnaire/entreprises/<int:entreprise_pk>/articles/<int:pk>/modifier/",
        ArticleBlocAdminUpdateView.as_view(),
        name="bloc-admin-modifier-article",
    ),
    path(
        "gestionnaire/entreprises/<int:entreprise_pk>/articles/<int:pk>/supprimer/",
        ArticleBlocAdminDeleteView.as_view(),
        name="bloc-admin-supprimer-article",
    ),
    path("entreprise/", EntrepriseArticleListeView.as_view(), name="entreprise_articles"),
    path("<int:pk>/modifier/", EntrepriseArticleUpdateView.as_view(), name="modifier_article"),
    path("<int:pk>/supprimer/", EntrepriseArticleDeleteView.as_view(), name="supprimer_article"),
]
