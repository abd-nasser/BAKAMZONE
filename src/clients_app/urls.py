from django.urls import path

from clients_app.views import (
    ClientBlocDetailView,
    ClientDashboardView,
    ClientArticleDetailView,
    InscriptionClientView,
    LivreurProfilViewByClient,
    StartBlocSupportChatView,
    SupportChatView,
    ToggleFavoriArticleView,
    ToggleFavoriLivreurView,
)

app_name = 'clients_app'

urlpatterns = [
    path('inscription/', InscriptionClientView.as_view(), name='inscription-client'),
    path('tableau-de-bord/', ClientDashboardView.as_view(), name='tableau-de-bord'),
    path(
        'articles/<int:pk>/',
        ClientArticleDetailView.as_view(),
        name='detail-article',
    ),
    path(
        'articles/<int:pk>/favori/',
        ToggleFavoriArticleView.as_view(),
        name='toggle-favori-article',
    ),
    path(
        'blocs/<int:pk>/',
        ClientBlocDetailView.as_view(),
        name='detail-bloc',
    ),
    path(
        'blocs/<int:pk>/support/',
        StartBlocSupportChatView.as_view(),
        name='demarrer-chat-assistant',
    ),
    path(
        'support/conversations/<int:pk>/',
        SupportChatView.as_view(),
        name='chat-assistant',
    ),
    path(
        'livreur/<int:pk>/profil/',
        LivreurProfilViewByClient.as_view(),
        name='profil-livreur',
    ),
    path(
        'livreur/<int:pk>/favori/',
        ToggleFavoriLivreurView.as_view(),
        name='toggle-favori-livreur',
    ),
]
