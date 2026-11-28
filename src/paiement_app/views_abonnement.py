import json
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView

from entreprise_app.models import Entreprise
from .models import PaiementAbonnementLigdiCash
from .services_abonnement import (
    confirmer_paiement_abonnement,
    initier_paiement_abonnement,
    preparer_paiement_abonnement,
)

logger = logging.getLogger(__name__)


def _extraire_payload_callback(request):
    """Extrait le payload JSON ou form-encoded envoyé par LigdiCash."""
    if request.content_type and "application/json" in request.content_type:
        try:
            body = request.body.decode("utf-8") if request.body else "{}"
            data = json.loads(body)
            return data if isinstance(data, dict) else {"raw": data}
        except Exception:
            logger.warning("Payload JSON invalide reçu sur le callback abonnement LigdiCash")
            return {}
    if request.POST:
        return request.POST.dict()
    if request.GET:
        return request.GET.dict()
    return {}


def _retrouver_paiement_abonnement(payload):
    """Retrouve un PaiementAbonnementLigdiCash à partir de custom_data ou des tokens."""
    if not isinstance(payload, dict):
        return None

    custom_data = payload.get("custom_data")
    if isinstance(custom_data, str):
        try:
            custom_data = json.loads(custom_data)
        except Exception:
            custom_data = {}

    if isinstance(custom_data, dict):
        ref = custom_data.get("paiement_abonnement_ref")
        if ref:
            paiement = PaiementAbonnementLigdiCash.objects.filter(reference=ref).first()
            if paiement:
                return paiement

    for cle in ("token", "invoice_token", "transaction_token"):
        token = payload.get(cle)
        if token:
            token_str = str(token).strip()
            paiement = PaiementAbonnementLigdiCash.objects.filter(
                token_creation=token_str
            ).first()
            if paiement:
                return paiement
            paiement = PaiementAbonnementLigdiCash.objects.filter(
                token_callback=token_str
            ).first()
            if paiement:
                return paiement

    return None


class InitierPaiementAbonnementView(LoginRequiredMixin, View):
    """Initie le paiement LigdiCash pour le palier choisi par l'entreprise."""

    template_name = "paiement_templates/initier_paiement_abonnement.html"
    
    def get(self, request, *args, **kwargs):
        entreprise = get_object_or_404(
            Entreprise,
            user_principal=request.user,
            user_principal__role="entreprise",
        )

        paliers_valides = {
            PaiementAbonnementLigdiCash.PALIER_STANDARD: "Standard",
            PaiementAbonnementLigdiCash.PALIER_PRO: "Pro",
            PaiementAbonnementLigdiCash.PALIER_PREMIUM: "Premium",
        }

        palier_demande = (
            request.GET.get("palier")
            or (entreprise.palier if entreprise.palier in paliers_valides else "")
            or PaiementAbonnementLigdiCash.PALIER_STANDARD
        ).strip()

        if palier_demande not in paliers_valides:
            messages.error(request, "Palier d'abonnement inconnu.")
            return redirect("entreprise_app:choix-palier")

        est_promo = True
        montant = PaiementAbonnementLigdiCash.obtenir_tarif(
            palier=palier_demande,
            promo=est_promo,
        )

        context = {
            "entreprise": entreprise,
            "palier_code": palier_demande,
            "palier_label": paliers_valides[palier_demande],
            "est_promo": est_promo,
            "montant": montant,
            "duree_jours": 30,
            "quota_articles": Entreprise.QUOTAS_ARTICLES.get(palier_demande, 0),
            "quota_admins": Entreprise.QUOTAS_ADMINS.get(palier_demande, 0),
        }
        return render(
            request,
            "paiement_templates/initier_paiement_abonnement.html",
            context,
        )
    
    
    
    def post(self, request, *args, **kwargs):
        entreprise = get_object_or_404(
            Entreprise,
            user_principal=request.user,
            user_principal__role="entreprise",
        )

        palier = (request.POST.get("palier") or entreprise.palier or "").strip()
        numero_client = (request.POST.get("numero_client") or "").strip()
        operateur = (request.POST.get("operateur") or "").strip().upper()
        otp = (request.POST.get("otp") or "").strip()
        promo = request.POST.get("promo", "true").lower() in {"1", "true", "yes", "on"}

        valeurs_valides = {
            PaiementAbonnementLigdiCash.PALIER_STANDARD,
            PaiementAbonnementLigdiCash.PALIER_PRO,
            PaiementAbonnementLigdiCash.PALIER_PREMIUM,
        }
        if palier not in valeurs_valides:
            msg = "Sélectionnez un palier valide (Standard, Pro ou Premium)."
            if request.headers.get("HX-Request") == "true":
                return render(
                    request,
                    "partials/result/paiement_result.html",
                    {"succes": False, "title": "Palier invalide", "message": msg},
                )
            messages.error(request, msg)
            return redirect("entreprise_app:choix-palier")

        if not numero_client or not operateur:
            msg = "Renseignez votre numéro mobile money et l'opérateur."
            if request.headers.get("HX-Request") == "true":
                return render(
                    request,
                    "partials/result/paiement_result.html",
                    {"succes": False, "title": "Informations manquantes", "message": msg},
                )
            messages.error(request, msg)
            return redirect("entreprise_app:choix-palier")

        paiement = preparer_paiement_abonnement(
            entreprise=entreprise,
            palier=palier,
            numero_client=numero_client,
            operateur=operateur,
            promo=promo,
        )
        resultat = initier_paiement_abonnement(paiement, otp=otp)

        if request.headers.get("HX-Request") == "true":
            response = render(
                request,
                "partials/result/paiement_result.html",
                {
                    "succes": resultat["ok"],
                    "title": resultat["title"],
                    "message": resultat["message"],
                    "paiement": paiement,
                    "entreprise": entreprise,
                },
            )
            if resultat["ok"]:
                response["HX-Trigger"] = "close_and_reload"
            return response

        if resultat["ok"]:
            messages.success(request, resultat["message"])
        else:
            messages.error(request, resultat["message"])
        return redirect("paiement_app:statut-abonnement", reference=paiement.reference)


@method_decorator(csrf_exempt, name="dispatch")
class LigdiCashAbonnementCallbackView(View):
    """Endpoint webhook dédié aux confirmations de paiement d'abonnement."""

    def post(self, request, *args, **kwargs):
        payload = _extraire_payload_callback(request)
        token_cb = str(
            payload.get("token")
            or payload.get("invoice_token")
            or payload.get("transaction_token")
            or ""
        ).strip()

        paiement = _retrouver_paiement_abonnement(payload)
        if not paiement:
            logger.warning(
                "Callback abonnement LigdiCash reçu sans correspondance : %s",
                payload,
            )
            return JsonResponse(
                {"status": "ignored", "detail": "Paiement abonnement introuvable"},
                status=200,
            )

        confirmer_paiement_abonnement(
            paiement_id=paiement.pk,
            token_callback=token_cb,
            payload_cb=payload,
        )
        return JsonResponse(
            {"status": "ok", "reference": str(paiement.reference)},
            status=200,
        )



class StatutPaiementAbonnementView(LoginRequiredMixin, DetailView):
    """Affiche l'état d'une transaction d'abonnement et synchronise si en attente."""

    model = PaiementAbonnementLigdiCash
    slug_field = "reference"
    slug_url_kwarg = "reference"
    template_name = "paiement_templates/statut_abonnement.html"
    context_object_name = "paiement"

    def get_queryset(self):
        return PaiementAbonnementLigdiCash.objects.select_related("entreprise").filter(
            entreprise__user_principal=self.request.user
        )

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if (
            self.object.statut == PaiementAbonnementLigdiCash.STATUT_EN_ATTENTE
            and self.object.token_creation
        ):
            self.object = confirmer_paiement_abonnement(paiement_id=self.object.pk)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)