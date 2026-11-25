import logging

# Expose une erreur reconnue lorsque Celery ne peut pas joindre son broker.
from kombu.exceptions import OperationalError as CeleryOperationalError
# Construit l'URL de retour qui sera ouverte depuis la notification Web Push.
from django.urls import reverse

# La fonction reçoit la demande validée et délègue l'envoi au système Web Push existant.
from demande_livraison_app.models import DemandeLivraison
from notifications_app.tasks import envoyer_notification_webpush_task

logger = logging.getLogger(__name__)


def programmer_notification_position_destinataire(demande: DemandeLivraison) -> bool:
    """Programme une unique Web Push signalant que la position destinataire est disponible."""
    if demande.paiement_requis and not demande.est_payee:
        title = "Position reçue — Réglez votre livraison"
        body = (
            f"Le destinataire de votre course #{demande.pk} a partagé sa position. "
            "Validez le paiement pour autoriser le décollage du livreur."
        )
        target_url = reverse(
            "paiement_app:initier_livraison",
            kwargs={"reference": demande.reference},
        )
    else:
        title = "Position du destinataire disponible"
        body = (
            f"Le destinataire de votre course #{demande.pk} a partagé "
            "sa position. Le suivi GPS peut démarrer."
        )
        target_url = reverse("clients_app:tableau-de-bord")

    try:
        envoyer_notification_webpush_task.delay(
            user_id=demande.client.user_id,
            title=title,
            body=body,
            target_url=target_url,
        )
    except CeleryOperationalError:
        logger.exception(
            "Impossible de programmer la Web Push de position pour la demande #%s.",
            demande.pk,
        )
        return False

    return True
