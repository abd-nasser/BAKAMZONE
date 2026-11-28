
import logging
from datetime import timedelta
from decimal import Decimal

import ligdicash
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from entreprise_app.models import Entreprise
from .models import PaiementAbonnementLigdiCash
from .services import _configurer_sdk

logger = logging.getLogger(__name__)


def preparer_paiement_abonnement(
    entreprise,
    palier,
    numero_client,
    operateur,
    promo=True,
    duree_jours=30,
):
    """Crée une transaction locale en attente avec le montant calculé côté serveur."""
    montant = PaiementAbonnementLigdiCash.obtenir_tarif(palier=palier, promo=promo)
    return PaiementAbonnementLigdiCash.objects.create(
        entreprise=entreprise,
        palier=palier,
        est_promotionnel=bool(promo),
        duree_jours=duree_jours,
        montant=montant,
        numero_client=str(numero_client).strip(),
        operateur=str(operateur).strip().upper(),
        statut=PaiementAbonnementLigdiCash.STATUT_EN_ATTENTE,
    )

def initier_paiement_abonnement(
    paiement: PaiementAbonnementLigdiCash,
    otp: str = "",
) -> dict:
    """
    Initie le paiement d'abonnement sans redirection via le SDK LigdiCash.
    Retourne un dictionnaire {"ok": bool, "title": str, "message": str}.
    """
    _configurer_sdk()
    entreprise = paiement.entreprise
    user = getattr(entreprise, "user_principal", None)

    try:
        invoice = ligdicash.Invoice(
            currency="xof",
            description=(
                f"Abonnement {paiement.get_palier_display()} - "
                f"{entreprise.nom_entreprise} #{paiement.reference}"
            ),
            customer_firstname=user.first_name if user and user.first_name else "Entreprise",
            customer_lastname=user.last_name if user and user.last_name else entreprise.nom_entreprise,
            customer_email=user.email if user and getattr(user, "email", "") else "",
            store_name="BAKAMZONE",
        )
        invoice.add_item(
            name=f"Abonnement palier {paiement.get_palier_display()}",
            description=(
                f"{entreprise.nom_entreprise} ({paiement.duree_jours} jours)"
            ),
            quantity=1,
            unit_price=float(Decimal(str(paiement.montant))),
        )
        invoice.external_id = ""

        response = invoice.pay_without_redirection(
            otp=otp,
            customer=paiement.numero_client,
            callback_url=settings.LIGDICASH_CALLBACK_URL_ABONNEMENT,
            custom_data={
                "type": "abonnement",
                "paiement_abonnement_ref": str(paiement.reference),
                "entreprise_id": entreprise.pk,
                "palier": paiement.palier,
            },
        )
    except ligdicash.AuthenticationError as exc:
        logger.exception("Erreur d'authentification avec LigdiCash (abonnement) : %s", exc)
        paiement.statut = PaiementAbonnementLigdiCash.STATUT_ECHOUE
        paiement.message_erreur = "Erreur d'authentification avec LigdiCash"
        paiement.save(update_fields=["statut", "message_erreur", "date_mise_a_jour"])
        return {
            "ok": False,
            "title": "Erreur d'authentification",
            "message": "Impossible de se connecter à LigdiCash. Veuillez réessayer plus tard.",
        }
    except Exception as exc:
        logger.exception("Erreur lors de l'initiation LigdiCash abonnement : %s", exc)
        paiement.statut = PaiementAbonnementLigdiCash.STATUT_ECHOUE
        paiement.message_erreur = str(exc)
        paiement.save(update_fields=["statut", "message_erreur", "date_mise_a_jour"])
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
        paiement.statut = PaiementAbonnementLigdiCash.STATUT_EN_ATTENTE
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
        return {
            "ok": True,
            "title": "Paiement initié",
            "message": (
                texte
                or "Le paiement a été initié avec succès. Veuillez suivre les instructions pour le compléter."
            ),
        }

    paiement.statut = PaiementAbonnementLigdiCash.STATUT_ECHOUE
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
    return {
        "ok": False,
        "title": "Paiement refusé",
        "message": texte or "La transaction n'a pas pu être initiée par l'opérateur.",
    }
    
    
def _calculer_nouvelle_date_fin(entreprise:Entreprise, duree_jours:int, maintenant):
    base = maintenant
    if (
        hasattr(entreprise, "date_fin_abonnement")
        and entreprise.date_fin_abonnement
        and entreprise.date_fin_abonnement > maintenant
    ):
        base = entreprise.date_fin_abonnement
    return base + timedelta(days=duree_jours)



@transaction.atomic
def confirmer_paiement_abonnement(
    paiement_id: int,
    token_callback: str = "",
    payload_cb: dict | None = None,
) -> PaiementAbonnementLigdiCash:
    """
    Vérifie le statut réel du paiement d'abonnement via token_creation
    et active/prolonge le palier sur Entreprise de manière idempotente.
    """
    _configurer_sdk()
    paiement = (
        PaiementAbonnementLigdiCash.objects.select_for_update()
        .select_related("entreprise")
        .get(id=paiement_id)
    )
    entreprise = Entreprise.objects.select_for_update().get(pk=paiement.entreprise_id)

    if token_callback:
        paiement.token_callback = token_callback

    if payload_cb is not None:
        paiement.reponse_API = {
            **(paiement.reponse_API or {}),
            "last_callback": payload_cb,
        }

    if (
        paiement.statut == PaiementAbonnementLigdiCash.STATUT_REUSSI
        and paiement.abonnement_active
        and entreprise.subscription_active
        and entreprise.palier == paiement.palier
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
        logger.exception("Erreur de confirmation LigdiCash abonnement (%s) : %s", paiement.reference, exc)
        paiement.save(update_fields=["token_callback", "reponse_API", "date_mise_a_jour"])
        return paiement

    if etat in {"completed", "success", "paid"}:
        maintenant = timezone.now()
        paiement.statut = PaiementAbonnementLigdiCash.STATUT_REUSSI
        paiement.message_erreur = None
        paiement.date_paiement = paiement.date_paiement or maintenant
        paiement.abonnement_active = True
        paiement.save(
            update_fields=[
                "token_callback",
                "statut",
                "reponse_API",
                "message_erreur",
                "date_paiement",
                "abonnement_active",
                "date_mise_a_jour",
            ]
        )

        entreprise.palier = paiement.palier
        entreprise.subscription_active = True
        champs_entreprise = ["palier", "subscription_active"]
        if hasattr(entreprise, "date_fin_abonnement"):
            entreprise.date_fin_abonnement = _calculer_nouvelle_date_fin(
                entreprise=entreprise,
                duree_jours=paiement.duree_jours,
                maintenant=maintenant,
            )
            champs_entreprise.append("date_fin_abonnement")
        entreprise.save(update_fields=champs_entreprise)

    elif etat in {"failed", "error", "notcompleted"}:
        paiement.statut = PaiementAbonnementLigdiCash.STATUT_ECHOUE
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

    elif etat in {"cancelled", "aborted"}:
        paiement.statut = PaiementAbonnementLigdiCash.STATUT_ANNULE
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

    return paiement