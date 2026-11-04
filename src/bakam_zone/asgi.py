"""
ASGI config for bakam_zone project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

# Ajoute la session et l'utilisateur Django au scope des connexions WebSocket.
from channels.auth import AuthMiddlewareStack
# Sélectionne HTTP ou WebSocket et distribue les URL WebSocket.
from channels.routing import ProtocolTypeRouter, URLRouter
# Refuse les connexions provenant de navigateurs dont l'origine n'est pas autorisée.
from channels.security.websocket import OriginValidator
# Lit la liste d'origines configurée dans les paramètres Django.
from django.conf import settings
# Construit l'application ASGI HTTP standard de Django.
from django.core.asgi import get_asgi_application

# Indique à Django quels paramètres charger pour initialiser son environnement.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bakam_zone.settings')

# Initialiser Django avant d'importer les routes qui chargent les modèles d'application.
django_asgi_app = get_asgi_application()

from bakam_zone.routing import websocket_urlpatterns

# Conserve le traitement HTTP Django et ajoute une branche WebSocket authentifiée et filtrée.
application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': OriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns),
        ),
        settings.WEBSOCKET_ALLOWED_ORIGINS,
    ),
})
