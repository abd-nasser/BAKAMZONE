import logging #logger les erreurs
from decimal import Decimal #typé en les montant en format decimaux
from django.conf import settings # importer les clé et token API
from django.db import transaction #pour atomiser les ecriture et en base
from django.db.models.functions import Greatest
from django.utils import timezone
from django.db.models import F

import ligdicash
from articles_app.models import Article
from panier_app.models import Commande
from .models import PaiementLigdiCash

logger = logging.getLogger(__name__)

def _configurer_sdk():
    ligdicash.api_key = settings.LIGDICASH_API_KEY
    ligdicash.auth_token = settings.LIGDICASH_AUTH_TOKEN
    ligdicash.platform = settings.LIGDICASH_PLATFORM
    

def initier_paiement_ligdicash(paiement: PaiementLigdiCash, otp: str='') -> dict:
    """ 
        Initie le paiement sans redirection via le SDK LigdiCash.
        Retourne un dictionnaire {"ok": bool, "title : str, "message" : str}
    
    """
    _configurer_sdk()
    commande = paiement.commande
    try:
        invoice = ligdicash.Invoice(
            currency="xof",
            description=f"Facture BAKAMZONE - Commande #{commande.reference}",
            customer_first_name=commande.client.user.first_name if commande.client.user.first_name else "Client",
            customer_last_name=commande.client.user.last_name if commande.client.user.last_name else "BAKAMZONE",
            customer_phone_number=paiement.numero_client,
            amount=Decimal(str (paiement.montant)),
        )
        response = invoice.pay_without_redirection(
            otp=otp,
            callback_url=settings.LIGDICASH_CALLBACK_URL,
            custom_data={"commande_reference": str(commande.reference), "paiement_ref": str(paiement.reference)},
            external_id="" 
        )
        
    except ligdicash.AuthenticationError as exc:
        logger.exception("Erreur d'authentification avec LigdiCash : %s", exc)
        paiement.statut = PaiementLigdiCash.STATUT_ECHOUE
        paiement.message_erreur = f"Erreur d'authentification avec LigdiCash"
        paiement.save(update_fields=["statut", "message_erreur", "date_mise_a_jour"])  
        return {"ok": False, 
                "title": "Erreur d'authentification", 
                "message": "Impossible de se connecter à LigdiCash. Veuillez réessayer plus tard."
                }  
    except Exception as exc:
        logger.exception("Erreur lors de l'initiation LigdiCash : %s", exc)
        paiement.statut = PaiementLigdiCash.STATUT_ECHOUE
        paiement.message_erreur = str(exc)
        paiement.save(update_fields=["statut", "message_erreur", "date_mise_a_jour"])
        return {
            "ok": False,
            "title": "Échec de l'initiation",
            "message": "Une erreur est survenue lors de l'envoi de la demande de paiement.",
        }
    
    raw_data = response.__dict__ if hasattr(response, "__dict__") else { "raw": str(response) }
    code = str(getattr(response, "response_code", "") or raw_data.get("response_code", ""))
    token = getattr(response, "token", "") or raw_data.get("token", "")
    texte = getattr(response, "response_text", "") or raw_data.get("response_text", "")
    
    paiement.reponse_API = raw_data
    if token:
        paiement.token_creation = token
    
    if code == "00":
        paiement.statut = PaiementLigdiCash.STATUT_EN_ATTENTE
        paiement.message_erreur = None
        paiement.save(update_fields=["statut", "message_erreur", "token_creation", "reponse_API", "date_mise_a_jour"])
        return {
            "ok": True,
            "title": "Paiement initié",
            "message": texte or "La demande de paiement a été envoyée. Veuillez valider la transaction sur votre téléphone.",
        }
    
    paiement.statut = PaiementLigdiCash.STATUT_ECHOUE
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
    
    
@transaction.atomic
def confirmer_paiement_ligdicash(paiement_id: int, token_callback: str = "", palyoad_cb: dict | None = None) -> PaiementLigdiCash:
    """
    Vérifie le statut réel d'un paiement auprès de ligdicash via token_creation
    et met à jour le paiement + la commande de maniere idempotente 
    
    """
    _configurer_sdk()
    paiement = (
        PaiementLigdiCash.objects.select_for_update()
        .select_related('commande')
        .get(pk=paiement_id)
        
        )
    commande =  Commande.objects.select_for_update().select_related("panier", "client", "zone_arrivee").get(pk=paiement.commande_id)
    
    if token_callback:
        paiement.token_callback = token_callback
    
    if palyoad_cb is not None:
        paiement.reponse_API = {**(paiement.reponse_API or {}), "last_callback":palyoad_cb}
    
    #Indempotence : Si déjà marqué réussi, on ne réaplique pas la validation commande
    if paiement.statut == PaiementLigdiCash.STATUT_REUSSI and commande.statut_paiement == Commande.PAIEMENT_REUSSI:
        paiement.save(update_fields=["token_callback", "reponse_API","date_mise_a_jour"])
        return paiement
    
    if not paiement.token_creation:
        paiement.save(update_fields=["token_callback", "reponse_API","date_mise_a_jour"])
        return paiement
    
    try:
        tx_status = ligdicash.get_transaction(token=paiement.token_creation)
        tx_data = tx_status.__dict__ if hasattr(tx_status, "__dict__") else {'raw': str(tx_status)}
        paiement.reponse_API = {**(paiement.reponse_API or {}), "confirm":tx_data} 
        etat = str(getattr(tx_status, 'status', "") or tx_data.get('status', "")).lower()
    except Exception as exc :
        logger.exception("Erreur lors de la confirmation LigdiCas (%s): %s", paiement.reference, exc)
        paiement.save(update_fields=["token_callback", "reponse_API","date_mise_a_jour"])
        return paiement
    
    if etat in {"completed","success", "paid"}:
        paiement.statut = PaiementLigdiCash.STATUT_REUSSI
        paiement.message_erreur = None
        paiement.save(update_fields=[
            "token_callbak",
            "statut",
            "reponse_API",
            "message_erreur",
            "date_mise_a_jour",
        ])
        
        if commande.statut_paiement != Commande.PAIEMENT_REUSSI:
            commande.statut_paiement = Commande.PAIEMENT_REUSSI
            commande.date_paiement = timezone.now()
            commande.save(update_fields=["statut_paiement", "date_paiement"])
            
            #Décrementation atomique du stock pour chaque ligne de la commande 
            lignes = commande.lignes.select_related("article").all()
            for ligne in lignes:
                if not ligne.article_id:
                    continue
                
                #si l'article est hors bloc, on décremente directement sa quantite disponible
                if not ligne.article.en_bloc:
                    Article.objects.filter(pk=ligne.article_id).update(
                        quantite_disponible=Greatest(
                            F("quantite_disponible") - ligne.quantite,
                            0,
                        )
                    )
    elif etat in {"failed","error","notcompleted",}:
        paiement.statut = PaiementLigdiCash.STATUT_ECHOUE
        paiement.message_erreur = f"Transaction échouée : {etat}"
        paiement.date_mise_a_jour = timezone.now()
        paiement.save(update_fields=[
            "token_callback",
            "statut",
            "reponse_API",
            "message_erreur",
            "date_mise_a_jour",
        ])
    elif etat in {"cancelled","aborted"}:
        paiement.statut = PaiementLigdiCash.STATUT_ANNULE
        paiement.message_erreur = f"Transaction annulée : {etat}"
        paiement.date_mise_a_jour = timezone.now()
        paiement.save(update_fields=[
            "token_callback",
            "statut",
            "reponse_API",
            "message_erreur",
            "date_mise_a_jour",
        ])  
    return paiement
        
        