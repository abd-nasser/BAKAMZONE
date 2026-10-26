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