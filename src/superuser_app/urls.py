from django.urls import path
from superuser_app.views import (
    SuperuserDashboardView,
    ListeEntrepriseViewBySuperUser,
    EntrepriseDetailViewBySuperUser,
    TraiterDemandeRetraitView,
)

app_name = 'superuser_app'

urlpatterns = [
    path('', SuperuserDashboardView.as_view(), name='dashboard'),
    path('entreprises/', ListeEntrepriseViewBySuperUser.as_view(), name='liste-entreprises'),
    path('entreprises/<int:pk>/', EntrepriseDetailViewBySuperUser.as_view(), name='detail-entreprise'),
    path('retraits/<int:pk>/traiter/', TraiterDemandeRetraitView.as_view(), name='traiter-retrait'),
]



