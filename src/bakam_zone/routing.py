# URLPattern décrit le type des routes ; path associe le chemin au consumer Channels.
from django.urls import URLPattern, path

# Consumer qui vérifie les droits et gère le WebSocket d'une demande.
from demande_livraison_app.consumers import SuiviLivraisonConsumer


# Routes consommées par le URLRouter de l'application ASGI.
websocket_urlpatterns: list[URLPattern] = [
    path(
        # L'identifiant de la demande est extrait du chemin puis transmis au consumer.
        "ws/livraisons/<int:demande_id>/suivi/",
        SuiviLivraisonConsumer.as_asgi(),
        name="suivi_livraison",
    ),
]
