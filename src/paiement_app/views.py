import json
import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from panier_app.models import Commande
from .models import PaiementLigdiCash
from .services import initier_paiement_ligdicash, confirmer_paiement_ligdicah

logger = logging.getLogger(__name__)

#Fonction de retour de resultat de paiement LigdiCash
def render_paiement_result(request, *, succes: bool, title: str, message: str, paiement=None, commande=None, status: int = 200, trigger: str = "close_and_reload" ):
    response = render(request, "partials/paiement/_paiement_result.html", {
        "succes": succes,
        "title": title,
        "message": message,
        "commande": commande,
        "paiement": paiement,
        
    },
    status=status
    )
    if trigger:
        response["HX-Trigger"] = trigger
    return response


#Fonction pour extraire le payload du callback LigdiCash
def _extraire_payload_callback(request):
    if request.body:
        try:
            data = json.loads(request.body.decode('utf-8'))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("Callback LigdiCash : corps non-JSON, repli sur POST")
    return request.POST.dict()



# Fonction pour retrouver le paiemznt grace au infos du payload du callback 
def _retrouver_paiement(payload: dict) -> PaiementLigdiCash | None:
    custom_data = payload.get('custom_data')
    if isinstance(custom_data, str):
        try:
            custom_data = json.loads(custom_data)
        except json.JSONDecodeError:
            custom_data = {}
    if not isinstance(custom_data, dict):
        custom_data = {}
    
    paiement_ref = custom_data.get('paiement_ref') or payload.get("paiement_ref")
    if paiement_ref:
        paiement =  PaiementLigdiCash.objects.filter(reference=paiement_ref).first()
        if paiement:
            return paiement   
    
    Commande_ref = custom_data.get("commande_reference") or payload.get("commande_reference")
    if Commande_ref:
        paiement = (
            PaiementLigdiCash.objects.select_related("commande")
            .filter(commande__reference=Commande_ref).first()
        )
    if paiement:
        return paiement
    
    token = (
        payload.get("token")
        or payload.get("token_callback")
        or payload.get("transaction_token")
        or ""
    ).strip()
    
    if token:
        paiement = (
            PaiementLigdiCash.objects.filter(token_creation=token).first()
            or PaiementLigdiCash.objects.filter(token_callback=token).first()
        )
        if paiement:
            return paiement
    return None
    
    
class InitierPaiementView(LoginRequiredMixin, View):
    template_name = "paiement_templates/initier_paiement.html"
    

    def _get_commande_client(self, reference):
        return get_object_or_404(
            Commande,
            reference=reference,
            client__user=self.request.user,
        )

    def get(self, request, reference, *args, **kwargs):
        commande = self._get_commande_client(reference)
        if commande.statut_paiement == Commande.PAIEMENT_REUSSI:
            return render_paiement_result(request, 
                                            succes=False, 
                                            title="Erreur", 
                                            message="Cette commande est déjà payée.",
                                            commande=commande,
                                            )
        return render(request, self.template_name, {"commande": commande})


    @transaction.atomic
    def post(self, request, reference, *args, **kwargs):
        commande = get_object_or_404(
            Commande.objects.select_for_update(),
            reference=reference,
            client__user=request.user,
        )
        if commande.statut_paiement == Commande.PAIEMENT_REUSSI:
            return render_paiement_result(
            request,
            succes=False,
            title="Paiement déjà validé",
            message="Cette commande a déjà été payée avec succès.",
            commande=commande,
        )
           

        numero_client = (request.POST.get("numero_client") or "").strip()
        operateur = (request.POST.get("operateur") or "").strip()
        otp = (request.POST.get("otp") or "").strip()

        if not numero_client:
           return render_paiement_result(
               request,
               succes=False,
               title="Numéro manquant",
               message="Veuillez saisir un numéro mobile money valide.",
               commande=commande,
               status=400,
               trigger=None
               
           )

        paiement, _ = PaiementLigdiCash.objects.select_for_update().get_or_create(
            commande=commande,
            defaults={
                "montant": commande.total_a_payer,
                "numero_client": numero_client,
                "operateur": operateur,
            },
        )
        paiement.montant = commande.total_a_payer
        paiement.numero_client = numero_client
        paiement.operateur = operateur
        paiement.statut = PaiementLigdiCash.STATUT_EN_ATTENTE
        paiement.message_erreur = None

        # Appel au service LigdiCash à brancher ici (création transaction + otp éventuel)
        # resultat = ligdicash_service.initier_paiement(paiement, otp=otp)
        paiement.save(update_fields=["montant", "numero_client", "operateur", "statut", "message_erreur", "date_mise_a_jour"])
        resultat = initier_paiement_ligdicash(paiement, otp=otp)
       
        return render_paiement_result(
            request,
            succes=resultat["ok"],
            title=resultat["title"],
            message=resultat["message"],
            paiement=paiement,
            commande=commande,
            trigger="close_and_reload" if resultat["ok"] else None,
        )


@method_decorator(csrf_exempt, name="dispatch")
class LigdiCashCallbackView(View):
    def post(self, request,  *args, **kwargs):
        payload = _extraire_payload_callback(request)
        if not payload:
            logger.warning("callback LigdiCash reçu avec payload vide")
            return JsonResponse({"status":"empty_payload"}, status=400)
        
        token_cb = str(
            payload.get("token")
            or payload.get("token_callback")
            or payload.get("transaction_token")
            or ""
        ).strip()
        
        paiement = _retrouver_paiement(payload)
        if not paiement:
            logger.warning(
                "Callback LigdiCash : aucun paiment trouvé (token=%s, payload=%s)",
                token_cb,
                payload,
            )
            return JsonResponse({"status": "payment_not_found"}, status=404)
        
        try:
            paiement = confirmer_paiement_ligdicah(
                paiement_id=paiement.id,
                token_callback=token_cb,
                palyoad_cb=payload
            )
        except Exception as exc:
            logger.exception(
                "Erreur lors du traitement du callback LigdiCash pour paiement %s : %s",
                paiement.reference,
                exc,
            )
            return JsonResponse({"status": "error"}, status=500)
        
        logger.info(
            "Callback LigdiCash traité : paiement=%s, statut=%s, commande_paiement=%s",
            paiement.reference,
            paiement.statut,
            paiement.commande.statut_paiement,
            )
        return JsonResponse(
            {
                "status": "processed",
                "paiement_reference": str(paiement.reference),
                'statut_paiement': paiement.statut,
            },
            status=200
        )


class StatutPaiementView(LoginRequiredMixin, View):
    template_name = "paiement_templates/statut_paiement.html"

    def get(self, request, reference, *args, **kwargs):
        commande = get_object_or_404(
            Commande,
            reference=reference,
            client__user=request.user,
        )
        paiement = get_object_or_404(PaiementLigdiCash, commande=commande)
        if request.headers.get("HX-Request") == "true" or request.GET.get("format") == "json":
            return JsonResponse(
                {
                    "commande_reference": str(commande.reference),
                    "statut_commande": commande.statut,
                    "statut_paiement": commande.statut_paiement,
                    "statut_ligdicash": paiement.statut,
                }
            )
        return render(
            request,
            self.template_name,
            {
                "commande": commande,
                "paiement": paiement,
            },
        )