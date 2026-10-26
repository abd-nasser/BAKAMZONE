import logging
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail as django_send_mail

#Initialisation du logger
logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_task(self, subject, plain_message, from_email, recipient_list, html_message):
    #Sécurité si from email est vide ou None
    from_email = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', None))
    try:
        logger.info(f"[Celery] Début d'envoi d'email à {recipient_list} - sujet: {subject}")
        django_send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False
        )

        logger.info(f"[Celery] Email envoyé avec succès à {recipient_list}")
        return f"Email envoyé à {recipient_list}"
    
    except Exception as exc:
        logger.error(f"[Celery] Échec envoi email à {recipient_list} : {exc}", exc_info=True)
        raise self.retry(exc=exc)

    