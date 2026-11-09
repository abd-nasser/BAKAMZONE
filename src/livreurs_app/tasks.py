import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from livreurs_app.models import PositionLivreur

logger = logging.getLogger(__name__)


@shared_task
def purger_historique_positions_task() -> int:
    """Supprime les positions GPS plus anciennes que la durée de conservation de 7 jours."""
    date_limite = timezone.now() - timedelta(days=7)
    positions = PositionLivreur.objects.filter(horodatage__lt=date_limite)
    nombre_supprime, _ = positions.delete()
    if nombre_supprime:
        logger.info(
            "Purge de l'historique GPS terminée : %s position(s) supprimée(s).",
            nombre_supprime,
        )
    return nombre_supprime
