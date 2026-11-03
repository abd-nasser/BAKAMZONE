from django.urls import path
from .views import (
    EnregistrerWebPushSubscriptionView,
    SupprimerWebPushSubscriptionView,
    VapidPublicKeyView,
)

app_name = "notifications_app"

urlpatterns = [
    path("pwa/subscribe/", EnregistrerWebPushSubscriptionView.as_view(), name="subscribe"),
    path("pwa/unsubscribe/", SupprimerWebPushSubscriptionView.as_view(), name="unsubscribe"),
    path("pwa/vapid-key/", VapidPublicKeyView.as_view(), name="vapid-key"),
]
