from django.urls import path

from admins_app.views import (
    AdminBlocCreateView,
    AdminBlocPostDashboardView,
    GestionnaireStockDashboardView,
    GestionnaireStockEntrepriseDetailView,
    SuperviseurFlotteDashbordView,
)

app_name = 'admins_app'

urlpatterns = [
    path('creer/', AdminBlocCreateView.as_view(), name='creer-admin-bloc'),
    path(
        'tableau-de-bord/stock/',
        GestionnaireStockDashboardView.as_view(),
        name='tableau-de-bord-stock',
    ),
    path(
        'entreprises/<int:pk>/',
        GestionnaireStockEntrepriseDetailView.as_view(),
        name='entreprise-detail-stock',
    ),
    path(
        'tableau-de-bord/responsable/',
        AdminBlocPostDashboardView.as_view(poste='responsable'),
        name='tableau-de-bord-responsable',
    ),
    path(
        'tableau-de-bord/flotte/',
        SuperviseurFlotteDashbordView.as_view(),
        name='tableau-de-bord-flotte',
    ),
    path(
        'tableau-de-bord/assistant/',
        AdminBlocPostDashboardView.as_view(poste='assistant'),
        name='tableau-de-bord-assistant',
    ),
]
