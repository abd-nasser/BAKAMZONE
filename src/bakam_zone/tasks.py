import logging
from smtplib import SMTPException

from celery import shared_task
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail as django_send_mail
import requests

logger = logging.getLogger(__name__)


class WhatsAppTransientAPIError(Exception):
    pass


@shared_task(
    bind=True,
    autoretry_for=(SMTPException, OSError),
    retry_backoff=60,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3,
)
def send_email_task(
    self,
    subject: str,
    plain_message: str,
    recipient_list: list[str],
    from_email: str | None = None,
    html_message: str | None = None,
) -> int:
    if not recipient_list:
        raise ValueError("Au moins un destinataire doit être fourni.")

    sender = from_email or settings.DEFAULT_FROM_EMAIL
    if not sender:
        raise ValueError(
            "Configurez DEFAULT_FROM_EMAIL ou EMAIL_HOST_USER avant l'envoi."
        )

    logger.info(
        "Sending email task %s to %d recipient(s)",
        self.request.id,
        len(recipient_list),
    )
    sent_count = django_send_mail(
        subject=subject,
        message=plain_message,
        from_email=sender,
        recipient_list=recipient_list,
        html_message=html_message,
        fail_silently=False,
    )
    if sent_count == 0:
        raise RuntimeError("Le backend mail n'a envoyé aucun message.")

    logger.info("Email sent to %d recipient(s)", sent_count)
    return sent_count


@shared_task(
    bind=True,
    autoretry_for=(
        requests.ConnectionError,
        requests.Timeout,
        WhatsAppTransientAPIError,
    ),
    retry_backoff=60,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3,
)
def send_whatsapp_notification_task(
    self,
    recipient_phone: str,
    message: str,
) -> str:
    phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
    access_token = settings.WHATSAPP_ACCESS_TOKEN
    if not phone_number_id or not access_token:
        raise ImproperlyConfigured(
            "Configurez WHATSAPP_PHONE_NUMBER_ID et WHATSAPP_ACCESS_TOKEN "
            "pour activer WhatsApp Cloud API."
        )

    recipient_phone = recipient_phone.strip()
    message = message.strip()
    if not recipient_phone:
        raise ValueError("Le numéro du destinataire WhatsApp est obligatoire.")
    if not message:
        raise ValueError("Le message WhatsApp ne peut pas être vide.")

    api_url = (
        f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
        f"{phone_number_id}/messages"
    )
    logger.info(
        "Sending WhatsApp notification task %s",
        self.request.id,
    )
    response = requests.post(
        api_url,
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_phone,
            "type": "text",
            "text": {"body": message},
        },
        timeout=settings.WHATSAPP_API_TIMEOUT,
    )
    if response.status_code == 429 or response.status_code >= 500:
        raise WhatsAppTransientAPIError(
            f"WhatsApp Cloud API temporairement indisponible "
            f"(HTTP {response.status_code})."
        )
    response.raise_for_status()

    result = response.json()
    message_id = result["messages"][0]["id"]
    logger.info("WhatsApp notification accepted: %s", message_id)
    return message_id


@shared_task(bind=True)
def envoyer_notification_smartdrop_destinataire_task(self, demande_id: int, base_url: str | None = None) -> bool:
    """
    Envoie un message WhatsApp au destinataire avec le lien PWA de géolocalisation en 1 clic
    et programme le contrôle d'escalade après 3 minutes.
    """
    from demande_livraison_app.models import DemandeLivraison

    try:
        demande = DemandeLivraison.objects.select_related('livreur__user').get(pk=demande_id)
    except DemandeLivraison.DoesNotExist:
        logger.error("DemandeLivraison #%s introuvable pour Smart-Drop.", demande_id)
        return False

    url_base = base_url or getattr(settings, 'SITE_URL', 'http://localhost:8000')
    verification_url = f"{url_base.rstrip('/')}/geo/verify/{demande.token_pwa_destinataire}/"

    nom_livreur = demande.livreur.user.get_full_name() if demande.livreur else "Un livreur BAKAMZONE"
    message = (
        f"Bonjour ! Votre livraison BAKAMZONE (#{demande.pk}) est prise en charge par {nom_livreur}. "
        f"Pour recevoir votre colis directement sans attendre, cliquez sur ce lien pour partager votre position en 1 clic : "
        f"{verification_url}"
    )

    phone_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', None)
    token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', None)
    verifier_delai_reponse_destinataire_task.apply_async(
        args=[demande.pk],
        countdown=180,
    )

    if phone_id and token:
        send_whatsapp_notification_task.delay(demande.whatsapp_destinataire, message)
    else:
        logger.info(
            "[DEV MODE] WhatsApp Smart-Drop non configuré pour la demande #%s.",
            demande.pk,
        )

    return True


@shared_task(bind=True)
def verifier_delai_reponse_destinataire_task(self, demande_id: int) -> str:
    """
    Vérifie après 3 minutes si le destinataire a validé sa position GPS.
    Si non, bascule statut_destinataire vers 'alerte_assistant' pour escalade vers l'assistant du bloc.
    """
    from demande_livraison_app.models import DemandeLivraison

    try:
        demande = DemandeLivraison.objects.get(pk=demande_id)
    except DemandeLivraison.DoesNotExist:
        return "not_found"

    if not demande.position_destinataire_validee and demande.statut_destinataire == 'en_attente':
        demande.statut_destinataire = 'alerte_assistant'
        demande.save(update_fields=['statut_destinataire'])
        logger.warning(
            "Demande #%s : Délai de 3min dépassé sans position GPS du destinataire. Escalade en alerte assistant.",
            demande_id,
        )
        return "alerte_assistant"

    return "ok"
