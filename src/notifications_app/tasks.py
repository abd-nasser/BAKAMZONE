import json
import logging
from celery import shared_task
from django.conf import settings
from django.urls import reverse

from demande_livraison_app.models import DemandeLivraison

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def envoyer_notification_webpush_task(
    self,
    user_id: int,
    title: str,
    body: str,
    target_url: str | None = None,
    icon: str | None = None,
    badge: str | None = None,
) -> dict:
    """
    Envoie une notification Web Push à tous les terminaux enregistrés pour un utilisateur.
    Supprime automatiquement les abonnements expirés ou révoqués (HTTP 410 Gone / 404 Not Found).
    """
    from .models import WebPushSubscription

    subscriptions = WebPushSubscription.objects.filter(user_id=user_id, actif=True)
    if not subscriptions.exists():
        logger.info("Aucun terminal Web Push actif trouvé pour l'utilisateur #%s", user_id)
        return {"user_id": user_id, "sent": 0, "status": "no_subscription"}

    private_key = getattr(settings, "VAPID_PRIVATE_KEY", "")
    if not private_key:
        logger.error("Clé privée VAPID absente : notification Web Push non envoyée.")
        return {
            "user_id": user_id,
            "sent": 0,
            "status": "configuration_error",
        }

    from pywebpush import WebPushException, webpush

    payload = json.dumps(
        {
            "title": title,
            "body": body,
            "url": target_url or "/",
            "icon": icon or "/static/icons/icon-192x192.png",
            "badge": badge or "/static/icons/icon-192x192.png",
        }
    )

    admin_email = getattr(settings, "VAPID_ADMIN_EMAIL", "admin@bakamzone.com")
    vapid_claims = {"sub": f"mailto:{admin_email}"}

    sent_count = 0
    removed_count = 0

    for sub in subscriptions:
        subscription_info = {
            "endpoint": sub.endpoint,
            "keys": {
                "p256dh": sub.p256dh,
                "auth": sub.auth,
            },
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=private_key,
                vapid_claims=vapid_claims,
                timeout=10,
            )
            sent_count += 1
        except WebPushException as ex:
            status_code = getattr(getattr(ex, "response", None), "status_code", None)
            if status_code in (404, 410):
                logger.warning(
                    "Abonnement WebPush #%s révoqué ou expiré (HTTP %s). Suppression.",
                    sub.pk,
                    status_code,
                )
                sub.delete()
                removed_count += 1
            elif status_code is None or status_code == 429 or status_code >= 500:
                logger.warning(
                    "Erreur WebPush temporaire sur l'abonnement #%s.",
                    sub.pk,
                    exc_info=True,
                )
                countdown = min(60 * 2**self.request.retries, 600)
                raise self.retry(exc=ex, countdown=countdown)
            else:
                logger.error(
                    "Erreur WebPush permanente sur l'abonnement #%s (HTTP %s).",
                    sub.pk,
                    status_code,
                    exc_info=True,
                )
                raise

    return {
        "user_id": user_id,
        "sent": sent_count,
        "removed": removed_count,
        "mode": "real",
    }


@shared_task(bind=True)
def notifier_nouveau_message_support_task(self, message_id: int) -> str:
    """
    Détermine le destinataire d'un SupportMessage (client ou assistant du bloc)
    et programme l'envoi de la notification Web Push.
    """
    from admins_app.models import AdminBloc
    from clients_app.models import SupportMessage

    try:
        message = SupportMessage.objects.select_related(
            "conversation__client__user",
            "conversation__bloc",
            "sender",
        ).get(pk=message_id)
    except SupportMessage.DoesNotExist:
        logger.error("SupportMessage #%s introuvable pour notification WebPush.", message_id)
        return "message_not_found"

    conversation = message.conversation
    client_user = conversation.client.user
    bloc = conversation.bloc
    sender = message.sender

    chat_url = reverse("clients_app:chat-assistant", kwargs={"pk": conversation.pk})
    apercu_texte = message.content[:100] + ("..." if len(message.content) > 100 else "")

    if sender.pk == client_user.pk:
        # Le client a envoyé un message -> Notifier l'assistant actif du bloc
        assistants = AdminBloc.objects.filter(
            bloc=bloc,
            poste="assistant",
            actif=True,
            user__is_active=True,
        ).select_related("user")

        expediteur_nom = sender.get_full_name() or sender.username
        title = f"Nouveau message de {expediteur_nom} ({bloc.nom})"

        for assistant in assistants:
            envoyer_notification_webpush_task.delay(
                user_id=assistant.user.pk,
                title=title,
                body=apercu_texte,
                target_url=chat_url,
            )
        return f"notified_{assistants.count()}_assistants"
    else:
        # L'assistant a répondu -> Notifier le client
        title = f"Message de l'assistance ({bloc.nom})"
        envoyer_notification_webpush_task.delay(
            user_id=client_user.pk,
            title=title,
            body=apercu_texte,
            target_url=chat_url,
        )
        return "notified_client"


@shared_task
def notifier_acceptation_demande_livraison_task(demande_id: int) -> str:
    """Notifie le client lorsqu'un livreur accepte sa demande de livraison."""
    try:
        demande = DemandeLivraison.objects.select_related(
            "client__user",
            "livreur__user",
        ).get(pk=demande_id)
    except DemandeLivraison.DoesNotExist:
        logger.error(
            "Demande de livraison #%s introuvable pour notification push.",
            demande_id,
        )
        return "demande_not_found"

    livreur_user = demande.livreur.user
    nom_livreur = livreur_user.get_full_name() or livreur_user.username
    envoyer_notification_webpush_task.delay(
        user_id=demande.client.user_id,
        title="Votre demande de livraison a été acceptée",
        body=f"{nom_livreur} a accepté votre demande de livraison #{demande.pk}.",
        target_url=reverse("clients_app:tableau-de-bord"),
    )
    return "notified_client"
