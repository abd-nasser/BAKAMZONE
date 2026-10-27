from decimal import Decimal
from django.conf import settings
from zones_app.models import Zone


TARIF_INTRA_BLOC_DEFAUT = Decimal('1000')
TARIF_INTER_BLOCS_DEFAUT = Decimal('1500')


def obtenir_tarifs_livraison():
    """Renvoie les tarifs configurés ou par défaut (en FCFA)."""
    tarif_intra = getattr(settings, 'TARIF_LIVRAISON_INTRA_BLOC', TARIF_INTRA_BLOC_DEFAUT)
    tarif_inter = getattr(settings, 'TARIF_LIVRAISON_INTER_BLOCS', TARIF_INTER_BLOCS_DEFAUT)
    return Decimal(str(tarif_intra)), Decimal(str(tarif_inter))


def calculer_tarif_livraison(zone_depart: Zone, zone_arrivee: Zone) -> Decimal:
    """
    Calcule le montant de la course selon la matrice de zones :
    - Intra-zone / même bloc : Tarif fixe (ex: 1 000 FCFA)
    - Inter-blocs : Tarif fixe majoré (ex: 1 500 FCFA)
    """
    tarif_intra, tarif_inter = obtenir_tarifs_livraison()

    if not zone_depart or not zone_arrivee:
        return tarif_intra

    # Comparaison par bloc associé
    bloc_depart_id = getattr(zone_depart, 'bloc_id', None)
    bloc_arrivee_id = getattr(zone_arrivee, 'bloc_id', None)

    if bloc_depart_id and bloc_arrivee_id and bloc_depart_id == bloc_arrivee_id:
        return tarif_intra

    return tarif_inter
