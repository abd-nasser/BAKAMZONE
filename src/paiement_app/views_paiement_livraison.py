import json
import logging
import re

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from demande_livraison_app.models import DemandeLivraison
from .models import PaiementLivraisonLigdiCash
from .services_livraison import (
    confirmer_paiement_ligdicash_livraison,
    initier_paiement_ligdicash_livraison,
)
from .views import render_paiement_result

logger = logging.getLogger(__name__)


def _montant_livraison(demande_livraison: DemandeLivraison):
    return getattr(demande_livraison, "prix", None) or getattr(demande_livraison, "montant", 0)


def _livraison_deja_payee(demande_livraison: DemandeLivraison) -> bool:
    if getattr(demande_livraison, "statut_paiement", None) == DemandeLivraison.PAIEMENT_REUSSI:
        return True

    paiement = PaiementLivraisonLigdiCash.objects.filter(
        demande_livraison=demande_livraison,
        statut=PaiementLivraisonLigdiCash.STATUT_REUSSI,
    ).exists()
    return paiement


def _extraire_payload_callback_livraison(request) -> dict:
    if request.body:
        try:
            data = json.loads(request.body.decode("utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("Callback LigdiCash livraison : corps non-JSON, repli sur POST")
    return request.POST.dict()


def _retrouver_paiement_livraison(payload: dict) -> PaiementLivraisonLigdiCash | None:
    custom_data = payload.get("custom_data")
    if isinstance(custom_data, str):
        try:
            custom_data = json.loads(custom_data)
        except json.JSONDecodeError:
            custom_data = {}
    if not isinstance(custom_data, dict):
        custom_data = {}

    paiement_livraison_ref = custom_data.get("paiement_livraison_ref") or payload.get("paiement_livraison_ref")
    if paiement_livraison_ref:
        paiement_livraison = (
            PaiementLivraisonLigdiCash.objects.select_related("demande_livraison")
            .filter(reference=paiement_livraison_ref)
            .first()
        )
        if paiement_livraison:
            return paiement_livraison

    demande_livraison_ref = (
        custom_data.get("demande_livraison_reference")
        or custom_data.get("demande_reference")
        or payload.get("demande_livraison_reference")
    )
    if demande_livraison_ref:
        paiement_livraison = (
            PaiementLivraisonLigdiCash.objects.select_related("demande_livraison")
            .filter(demande_livraison__reference=demande_livraison_ref)
            .first()
        )
        if paiement_livraison:
            return paiement_livraison

    token = str(
        payload.get("token")
        or payload.get("token_callback")
        or payload.get("transaction_token")
        or ""
    ).strip()

    if token:
        paiement_livraison = (
            PaiementLivraisonLigdiCash.objects.select_related("demande_livraison")
            .filter(token_creation=token)
            .first()
            or PaiementLivraisonLigdiCash.objects.select_related("demande_livraison")
            .filter(token_callback=token)
            .first()
        )
        if paiement_livraison:
            return paiement_livraison

    return None


class InitierPaiementLivraisonView(LoginRequiredMixin, View):
    template_name = "paiement_templates/initier_paiement_livraison.html"

    def _get_demande_client(self, reference):
        return get_object_or_404(
            DemandeLivraison.objects.select_related("client__user", "zone_depart", "zone_arrivee"),
            reference=reference,
            client__user=self.request.user,
        )

    def get(self, request, reference, *args, **kwargs):
        demande_livraison = self._get_demande_client(reference)
        is_htmx = request.headers.get("HX-Request") == "true"

        if _livraison_deja_payee(demande_livraison):
            if is_htmx:
                return render_paiement_result(
                    request,
                    succes=False,
                    title="Paiement déjà validé",
                    message="Cette livraison est déjà payée.",
                )
            messages.info(request, "Cette livraison est déjà payée.")
            return redirect("paiement_app:statut_livraison", reference=demande_livraison.reference)

        if demande_livraison.statut == "annulee":
            if is_htmx:
                return render_paiement_result(
                    request,
                    succes=False,
                    title="Livraison annulée",
                    message="Cette demande de livraison a été annulée.",
                    status=400,
                    trigger=None,
                )
            messages.error(request, "Cette demande de livraison a été annulée.")
            return redirect("clients_app:tableau-de-bord")

        if not demande_livraison.position_destinataire_validee:
            if is_htmx:
                return render_paiement_result(
                    request,
                    succes=False,
                    title="Position en attente",
                    message="Le paiement sera disponible dès que le destinataire aura validé sa position GPS.",
                    status=400,
                    trigger=None,
                )
            messages.warning(
                request,
                "Le paiement sera disponible dès que le destinataire aura validé sa position GPS.",
            )
            return redirect("clients_app:tableau-de-bord")

        paiement = PaiementLivraisonLigdiCash.objects.filter(demande_livraison=demande_livraison).first()
        return render(
            request,
            self.template_name,
            {
                "demande": demande_livraison,
                "demande_livraison": demande_livraison,
                "montant": _montant_livraison(demande_livraison),
                "paiement": paiement,
            },
        )

    @transaction.atomic
    def post(self, request, reference, *args, **kwargs):
        demande_livraison = get_object_or_404(
            DemandeLivraison.objects.select_for_update(),
            reference=reference,
            client__user=request.user,
        )
        if _livraison_deja_payee(demande_livraison):
            return render_paiement_result(
                request,
                succes=False,
                title="Paiement déjà validé",
                message="Cette livraison a déjà été payée avec succès.",
            )

        if demande_livraison.statut == "annulee":
            return render_paiement_result(
                request,
                succes=False,
                title="Livraison annulée",
                message="Impossible de payer une demande de livraison annulée.",
                status=400,
                trigger=None,
            )

        if not demande_livraison.position_destinataire_validee:
            return render_paiement_result(
                request,
                succes=False,
                title="Position en attente",
                message="Attendez la validation GPS du destinataire avant de régler la livraison.",
                status=400,
                trigger=None,
            )

        numero_client = re.sub(r"[\s\-+]", "", (request.POST.get("numero_client") or "").strip())
        operateur = (request.POST.get("operateur") or "").strip()
        otp = (request.POST.get("otp") or "").strip()

        if not numero_client or len(numero_client) < 8:
            return render_paiement_result(
                request,
                succes=False,
                title="Numéro manquant",
                message="Veuillez saisir un numéro Mobile Money valide.",
                status=400,
                trigger=None,
            )

        montant = _montant_livraison(demande_livraison)
        if not montant or montant <= 0:
            return render_paiement_result(
                request,
                succes=False,
                title="Montant invalide",
                message="Le montant de cette livraison est invalide.",
                status=400,
                trigger=None,
            )

        paiement, _ = PaiementLivraisonLigdiCash.objects.select_for_update().get_or_create(
            demande_livraison=demande_livraison,
            defaults={
                "montant": montant,
                "numero_client": numero_client,
                "operateur": operateur,
            },
        )

        paiement.montant = montant
        paiement.numero_client = numero_client
        paiement.operateur = operateur
        paiement.statut = PaiementLivraisonLigdiCash.STATUT_EN_ATTENTE
        paiement.message_erreur = None
        paiement.save(
            update_fields=[
                "montant",
                "numero_client",
                "operateur",
                "statut",
                "message_erreur",
                "date_mise_a_jour",
            ]
        )

        resultat = initier_paiement_ligdicash_livraison(paiement, otp=otp)

        return render_paiement_result(
            request,
            succes=resultat["ok"],
            title=resultat["title"],
            message=resultat["message"],
            paiement=paiement,
            trigger="close_and_reload" if resultat["ok"] else None,
        )


@method_decorator(csrf_exempt, name="dispatch")
class LigdiCashLivraisonCallbackView(View):
    def post(self, request, *args, **kwargs):
        payload = _extraire_payload_callback_livraison(request)
        if not payload:
            logger.warning("Callback LigdiCash livraison reçu avec payload vide")
            return JsonResponse({"status": "empty_payload"}, status=400)

        token_cb = str(
            payload.get("token")
            or payload.get("token_callback")
            or payload.get("transaction_token")
            or ""
        ).strip()

        paiement_livraison = _retrouver_paiement_livraison(payload)
        if not paiement_livraison:
            logger.warning(
                "Callback LigdiCash livraison : aucun paiement trouvé (token=%s, payload=%s)",
                token_cb,
                payload,
            )
            return JsonResponse({"status": "payment_not_found"}, status=404)

        try:
            paiement_livraison = confirmer_paiement_ligdicash_livraison(
                paiement_id=paiement_livraison.id,
                token_callback=token_cb,
                payload_cb=payload,
            )
        except Exception as exc:
            logger.exception(
                "Erreur lors du traitement du callback LigdiCash livraison pour paiement %s : %s",
                paiement_livraison.reference,
                exc,
            )
            return JsonResponse({"status": "error"}, status=500)

        logger.info(
            "Callback LigdiCash livraison traité : paiement=%s, statut=%s, demande=%s",
            paiement_livraison.reference,
            paiement_livraison.statut,
            paiement_livraison.demande_livraison.reference,
        )
        return JsonResponse(
            {
                "status": "processed",
                "paiement_reference": str(paiement_livraison.reference),
                "statut_paiement": paiement_livraison.statut,
            },
            status=200,
        )


class StatutPaiementLivraisonView(LoginRequiredMixin, View):
    template_name = "paiement_templates/status_paiement_livraison.html"

    def get(self, request, reference, *args, **kwargs):
        demande_livraison = get_object_or_404(
            DemandeLivraison,
            reference=reference,
            client__user=request.user,
        )

        paiement = get_object_or_404(PaiementLivraisonLigdiCash, demande_livraison=demande_livraison)
        if paiement.statut == PaiementLivraisonLigdiCash.STATUT_EN_ATTENTE and paiement.token_creation:
            try:
                paiement = confirmer_paiement_ligdicash_livraison(paiement_id=paiement.id)
                demande_livraison.refresh_from_db()
            except Exception as exc:
                logger.warning(
                    "Vérification statut livraison non bloquante échouée (%s) : %s",
                    paiement.reference,
                    exc,
                )

        if request.GET.get("format") == "json":
            return JsonResponse(
                {
                    "demande_reference": str(demande_livraison.reference),
                    "statut_demande_livraison": demande_livraison.statut,
                    "est_payee": _livraison_deja_payee(demande_livraison),
                    "statut_ligdicash": paiement.statut,
                }
            )

        return render(
            request,
            self.template_name,
            {
                "demande": demande_livraison,
                "demande_livraison": demande_livraison,
                "paiement": paiement,
                "est_payee": _livraison_deja_payee(demande_livraison),
            },
        )
