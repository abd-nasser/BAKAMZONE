import json
import logging
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse
from django.views import View
from .models import WebPushSubscription

logger = logging.getLogger(__name__)


class EnregistrerWebPushSubscriptionView(View):
    """
    Enregistre ou met à jour la souscription Web Push de l'utilisateur connecté.
    Accepte les données au format JSON (W3C PushSubscription.toJSON()) ou form-data.
    """

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentification requise."}, status=401)

        if request.content_type == "application/json":
            try:
                data = json.loads(request.body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return JsonResponse({"error": "Format JSON invalide."}, status=400)
            if not isinstance(data, dict):
                return JsonResponse({"error": "Un objet JSON est requis."}, status=400)
            keys = data.get("keys")
            if not isinstance(keys, dict):
                return JsonResponse({"error": "Les clés de souscription sont invalides."}, status=400)
            endpoint = data.get("endpoint")
            p256dh = keys.get("p256dh")
            auth = keys.get("auth")
        else:
            endpoint = request.POST.get("endpoint")
            p256dh = request.POST.get("p256dh")
            auth = request.POST.get("auth")

        if not all(isinstance(value, str) for value in (endpoint, p256dh, auth)):
            return JsonResponse(
                {"error": "Paramètres endpoint, p256dh et auth requis."},
                status=400,
            )
        endpoint = endpoint.strip()
        p256dh = p256dh.strip()
        auth = auth.strip()

        if not endpoint or not p256dh or not auth:
            return JsonResponse(
                {"error": "Paramètres endpoint, p256dh et auth requis."},
                status=400,
            )

        subscription, created = WebPushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "user": request.user,
                "p256dh": p256dh,
                "auth": auth,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255],
                "actif": True,
            },
        )

        logger.info(
            "Abonnement Web Push %s pour l'utilisateur #%s (ID: %s)",
            "créé" if created else "actualisé",
            request.user.pk,
            subscription.pk,
        )

        return JsonResponse(
            {
                "success": True,
                "created": created,
                "subscription_id": subscription.pk,
            },
            status=201 if created else 200,
        )


class SupprimerWebPushSubscriptionView(View):
    """
    Désactive ou supprime une souscription Web Push pour l'utilisateur connecté.
    """

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentification requise."}, status=401)

        if request.content_type == "application/json":
            try:
                data = json.loads(request.body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return JsonResponse({"error": "Format JSON invalide."}, status=400)
            if not isinstance(data, dict):
                return JsonResponse({"error": "Un objet JSON est requis."}, status=400)
            endpoint = data.get("endpoint")
        else:
            endpoint = request.POST.get("endpoint")

        if not isinstance(endpoint, str) or not endpoint.strip():
            return JsonResponse({"error": "Endpoint requis."}, status=400)
        endpoint = endpoint.strip()

        deleted_count, _ = WebPushSubscription.objects.filter(
            user=request.user,
            endpoint=endpoint,
        ).delete()

        return JsonResponse(
            {"success": True, "deleted": deleted_count > 0},
            status=200,
        )


class VapidPublicKeyView(View):
    """
    Expose la clé publique VAPID pour permettre au front-end PWA
    d'initialiser le pushManager.subscribe({applicationServerKey: ...}).
    """

    def get(self, request, *args, **kwargs):
        public_key = getattr(settings, "VAPID_PUBLIC_KEY", "")
        if not public_key:
            return JsonResponse(
                {"error": "Les notifications Push ne sont pas configurées."},
                status=503,
            )
        return JsonResponse({"public_key": public_key})


class ServiceWorkerView(View):
    """Serves the worker at the site root so it can control the whole PWA."""

    def get(self, request, *args, **kwargs):
        worker_path = Path(settings.BASE_DIR) / "static" / "sw.js"
        try:
            worker_file = worker_path.open("rb")
        except OSError as exc:
            logger.exception("Impossible de lire le service worker Web Push.")
            raise Http404("Service worker indisponible.") from exc

        response = FileResponse(worker_file, content_type="application/javascript")
        response["Service-Worker-Allowed"] = "/"
        response["Cache-Control"] = "no-cache"
        return response
