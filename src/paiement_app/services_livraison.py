import logging
from decimal import Decimal

import ligdicash
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from demande_livraison_app.models import DemandeLivraison
from .models import PaiementLivraisonLigdiCash
from .services import _configurer_sdk

logger = logging.getLogger(__name__)


def initier_paiement_ligdicash_livraison(
    paiement: PaiementLivraisonLigdiCash,
    otp: str = "",
) -> dict:
    """
    Initie le paiement sans redirection via le SDK LigdiCash pour une demande de livraison.
    Retourne un dictionnaire {"ok": bool, "title": str, "message": str}.
    """
    _configurer_sdk()
    demande_livraison = paiement.demande_livraison
    user = (
        demande_livraison.client.user
        if getattr(demande_livraison, "client", None)
        and getattr(demande_livraison.client, "user", None)
        else None
    )

    try:
        invoice = ligdicash.Invoice(
            currency="xof",
            description=f"Livraison BAKAMZONE #{demande_livraison.reference}",
            customer_firstname=user.first_name if user and user.first_name else "Client",
            customer_lastname=user.last_name if user and user.last_name else "BAKAMZONE",
            customer_email=user.email if user and getattr(user, "email", "") else "",
            store_name="BAKAMZONE",
        )
        invoice.add_item(
            name=f"Course de livraison #{demande_livraison.pk}",
            description=f"{demande_livraison.zone_depart.nom} -> {demande_livraison.zone_arrivee.nom}",
            quantity=1,
            unit_price=float(Decimal(str(paiement.montant))),
        )
        invoice.external_id = ""

        response = invoice.pay_without_redirection(
            otp=otp,
            customer=paiement.numero_client,
            callback_url=settings.LIGDICASH_CALLBACK_URL_LIVRAISON,
            custom_data={
                "type": "livraison",
                "demande_livraison_reference": str(demande_livraison.reference),
                "paiement_livraison_ref": str(paiement.reference),
            },
        )
    except ligdicash.AuthenticationError as exc:
        logger.exception("Erreur d'authentification avec LigdiCash : %s", exc)
        paiement.statut = PaiementLivraisonLigdiCash.STATUT_ECHOUE
        paiement.message_erreur = "Erreur d'authentification avec LigdiCash"
        paiement.save(update_fields=["statut", "message_erreur", "date_mise_a_jour"])
        if demande_livraison.statut_paiement != DemandeLivraison.PAIEMENT_REUSSI:
            demande_livraison.statut_paiement = DemandeLivraison.PAIEMENT_ECHOUE
            demande_livraison.save(update_fields=["statut_paiement"])
        return {
            "ok": False,
            "title": "Erreur d'authentification",
            "message": "Impossible de se connecter à LigdiCash. Veuillez réessayer plus tard.",
        }
    except Exception as exc:
        logger.exception("Erreur lors de l'initiation LigdiCash livraison : %s", exc)
        paiement.statut = PaiementLivraisonLigdiCash.STATUT_ECHOUE
        paiement.message_erreur = str(exc)
        paiement.save(update_fields=["statut", "message_erreur", "date_mise_a_jour"])
        if demande_livraison.statut_paiement != DemandeLivraison.PAIEMENT_REUSSI:
            demande_livraison.statut_paiement = DemandeLivraison.PAIEMENT_ECHOUE
            demande_livraison.save(update_fields=["statut_paiement"])
        return {
            "ok": False,
            "title": "Échec de l'initiation",
            "message": "Une erreur est survenue lors de l'envoi de la demande de paiement.",
        }

    raw_data = response.__dict__ if hasattr(response, "__dict__") else {"raw": str(response)}
    code = str(getattr(response, "response_code", "") or raw_data.get("response_code", ""))
    token = getattr(response, "token", "") or raw_data.get("token", "")
    texte = getattr(response, "response_text", "") or raw_data.get("response_text", "")

    paiement.reponse_API = raw_data
    if token:
        paiement.token_creation = token

    if code == "00":
        paiement.statut = PaiementLivraisonLigdiCash.STATUT_EN_ATTENTE
        paiement.message_erreur = None
        paiement.save(
            update_fields=[
                "statut",
                "message_erreur",
                "token_creation",
                "reponse_API",
                "date_mise_a_jour",
            ]
        )
        if demande_livraison.statut_paiement != DemandeLivraison.PAIEMENT_REUSSI:
            demande_livraison.statut_paiement = DemandeLivraison.PAIEMENT_EN_ATTENTE
            demande_livraison.save(update_fields=["statut_paiement"])
        return {
            "ok": True,
            "title": "Paiement initié",
            "message": texte or "Le paiement a été initié avec succès. Veuillez suivre les instructions pour le compléter.",
        }

    paiement.statut = PaiementLivraisonLigdiCash.STATUT_ECHOUE
    paiement.message_erreur = texte or f"Code réponse LigdiCash : {code}"
    paiement.save(
        update_fields=[
            "token_creation",
            "statut",
            "reponse_API",
            "message_erreur",
            "date_mise_a_jour",
        ]
    )
    if demande_livraison.statut_paiement != DemandeLivraison.PAIEMENT_REUSSI:
        demande_livraison.statut_paiement = DemandeLivraison.PAIEMENT_ECHOUE
        demande_livraison.save(update_fields=["statut_paiement"])
    return {
        "ok": False,
        "title": "Paiement refusé",
        "message": texte or "La transaction n'a pas pu être initiée par l'opérateur.",
    }


@transaction.atomic
def confirmer_paiement_ligdicash_livraison(
    paiement_id: int,
    token_callback: str = "",
    payload_cb: dict | None = None,
) -> PaiementLivraisonLigdiCash:
    """
    Vérifie le statut réel du paiement via token_creation
    et met à jour PaiementLivraisonLigdiCash + DemandeLivraison de manière idempotente.
    """
    _configurer_sdk()
    paiement = (
        PaiementLivraisonLigdiCash.objects.select_for_update()
        .select_related("demande_livraison")
        .get(id=paiement_id)
    )
    demande_livraison = DemandeLivraison.objects.select_for_update().get(
        pk=paiement.demande_livraison_id
    )

    if token_callback:
        paiement.token_callback = token_callback

    if payload_cb is not None:
        paiement.reponse_API = {
            **(paiement.reponse_API or {}),
            "last_callback": payload_cb,
        }

    # Idempotence : déjà marqué réussi côté paiement et demande
    if (
        paiement.statut == PaiementLivraisonLigdiCash.STATUT_REUSSI
        and demande_livraison.statut_paiement == DemandeLivraison.PAIEMENT_REUSSI
    ):
        paiement.save(update_fields=["token_callback", "reponse_API", "date_mise_a_jour"])
        return paiement

    if not paiement.token_creation:
        paiement.save(update_fields=["token_callback", "reponse_API", "date_mise_a_jour"])
        return paiement

    try:
        tx_status = ligdicash.get_transaction(token=paiement.token_creation)
        tx_data = tx_status.__dict__ if hasattr(tx_status, "__dict__") else {"raw": str(tx_status)}
        paiement.reponse_API = {**(paiement.reponse_API or {}), "confirm": tx_data}
        etat = str(getattr(tx_status, "status", "") or tx_data.get("status", "")).lower()
    except Exception as exc:
        logger.exception("Erreur de confirmation LigdiCash livraison (%s) : %s", paiement.reference, exc)
        paiement.save(update_fields=["token_callback", "reponse_API", "date_mise_a_jour"])
        return paiement

    if etat in {"completed", "success", "paid"}:
        maintenant = timezone.now()
        paiement.statut = PaiementLivraisonLigdiCash.STATUT_REUSSI
        paiement.message_erreur = None
        paiement.date_paiement = paiement.date_paiement or maintenant
        paiement.save(
            update_fields=[
                "token_callback",
                "statut",
                "reponse_API",
                "message_erreur",
                "date_paiement",
                "date_mise_a_jour",
            ]
        )

        if demande_livraison.statut_paiement != DemandeLivraison.PAIEMENT_REUSSI:
            demande_livraison.statut_paiement = DemandeLivraison.PAIEMENT_REUSSI
            demande_livraison.date_paiement = paiement.date_paiement
            demande_livraison.save(update_fields=["statut_paiement", "date_paiement"])

    elif etat in {"failed", "error", "notcompleted"}:
        paiement.statut = PaiementLivraisonLigdiCash.STATUT_ECHOUE
        paiement.message_erreur = f"Transaction échouée : {etat}"
        paiement.save(
            update_fields=[
                "token_callback",
                "statut",
                "reponse_API",
                "message_erreur",
                "date_mise_a_jour",
            ]
        )
        if demande_livraison.statut_paiement != DemandeLivraison.PAIEMENT_REUSSI:
            demande_livraison.statut_paiement = DemandeLivraison.PAIEMENT_ECHOUE
            demande_livraison.save(update_fields=["statut_paiement"])

    elif etat in {"cancelled", "aborted"}:
        paiement.statut = PaiementLivraisonLigdiCash.STATUT_ANNULE
        paiement.message_erreur = f"Transaction annulée : {etat}"
        paiement.save(
            update_fields=[
                "token_callback",
                "statut",
                "reponse_API",
                "message_erreur",
                "date_mise_a_jour",
            ]
        )
        if demande_livraison.statut_paiement != DemandeLivraison.PAIEMENT_REUSSI:
            demande_livraison.statut_paiement = DemandeLivraison.PAIEMENT_NON_INITIE
            demande_livraison.save(update_fields=["statut_paiement"])

    return paiement
