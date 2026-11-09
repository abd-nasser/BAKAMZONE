from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from clients_app.models import Client
from demande_livraison_app.forms import DemandeLivraisonForm
from demande_livraison_app.models import DemandeLivraison
from demande_livraison_app.pricing import (
    calculer_tarif_livraison,
    obtenir_tarifs_livraison,
)
from notifications_app.services import programmer_notification_position_destinataire
from zones_app.models import Zone


class ClientRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin garantissant que l'utilisateur connecté est un client authentifié avec profil."""
    login_url = reverse_lazy('home_app:home')

    def test_func(self):
        return (
            self.request.user.is_authenticated
            and self.request.user.role == 'client'
            and Client.objects.filter(user=self.request.user).exists()
        )


class CreerDemandeLivraisonView(ClientRequiredMixin, CreateView):
    """
    Vue permettant au client de créer une demande de livraison avec :
    - Sélection des zones départ / arrivée
    - Capture de la position GPS par Alpine.js
    - Calcul automatique et dynamique du tarif (intra-zone ou inter-blocs)
    """
    model = DemandeLivraison
    form_class = DemandeLivraisonForm
    template_name = 'demande_livraison_templates/creer_demande.html'
    success_url = reverse_lazy('clients_app:tableau-de-bord')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tarif_intra, tarif_inter = obtenir_tarifs_livraison()
        context.update({
            'zones': Zone.objects.select_related('bloc').all().order_by('bloc__nom', 'nom'),
            'tarif_intra': int(tarif_intra),
            'tarif_inter': int(tarif_inter),
            'client': Client.objects.get(user=self.request.user),
        })
        return context

    def form_valid(self, form):
        client = Client.objects.get(user=self.request.user)
        self.object = form.save(client=client)
        messages.success(
            self.request,
            f"Votre demande de livraison #{self.object.pk} a bien été enregistrée pour un montant de {self.object.prix} FCFA.",
        )
        return redirect(self.success_url)


class CalculerTarifView(View):
    """Endpoint utilitaire renvoyant le tarif calculé en JSON."""
    def get(self, request, *args, **kwargs):
        zone_depart_id = request.GET.get('zone_depart')
        zone_arrivee_id = request.GET.get('zone_arrivee')

        zone_depart = Zone.objects.filter(pk=zone_depart_id).first() if zone_depart_id else None
        zone_arrivee = Zone.objects.filter(pk=zone_arrivee_id).first() if zone_arrivee_id else None

        if not zone_depart or not zone_arrivee:
            return JsonResponse({'prix': None, 'type': 'indefini'})

        prix = calculer_tarif_livraison(zone_depart, zone_arrivee)
        est_intra = (zone_depart.bloc_id == zone_arrivee.bloc_id)

        return JsonResponse({
            'prix': int(prix),
            'est_intra': est_intra,
            'type_label': "Intra-bloc" if est_intra else "Inter-blocs",
            'formatted': f"{int(prix):,} FCFA".replace(",", " "),
        })


class DestinataireGeoView(View):
    """
    Endpoint public PWA éphémère accessible par le destinataire via le lien WhatsApp.
    Permet de valider et transmettre sa position GPS réelle en 1 clic sans compte.
    """
    template_name = 'demande_livraison_templates/destinataire_geo.html'

    def get(self, request, token_pwa_destinataire, *args, **kwargs):
        demande = get_object_or_404(
            DemandeLivraison.objects.select_related('livreur__user', 'client__user', 'zone_arrivee'),
            token_pwa_destinataire=token_pwa_destinataire,
        )
        return render(
            request,
            self.template_name,
            {
                'demande': demande,
                'deja_valide': demande.position_destinataire_validee,
                'token': token_pwa_destinataire,
            },
        )

    def post(self, request, token_pwa_destinataire, *args, **kwargs):
        latitude = request.POST.get('latitude') or request.POST.get('latitude_destinataire_reelle')
        longitude = request.POST.get('longitude') or request.POST.get('longitude_destinataire_reelle')

        if not latitude or not longitude:
            demande = get_object_or_404(
                DemandeLivraison.objects.select_related(
                    'livreur__user',
                    'client__user',
                    'zone_arrivee',
                ),
                token_pwa_destinataire=token_pwa_destinataire,
            )
            return render(
                request,
                self.template_name,
                {
                    'demande': demande,
                    'error': "Veuillez autoriser et capturer votre position GPS pour continuer.",
                    'token': token_pwa_destinataire,
                },
            )

        try:
            latitude = Decimal(str(latitude).strip())
            longitude = Decimal(str(longitude).strip())
            if (
                not latitude.is_finite()
                or not longitude.is_finite()
                or not -90 <= latitude <= 90
                or not -180 <= longitude <= 180
            ):
                raise ValueError("Coordonnées GPS hors limites.")
        except (InvalidOperation, ValueError, TypeError):
            demande = get_object_or_404(
                DemandeLivraison.objects.select_related(
                    'livreur__user',
                    'client__user',
                    'zone_arrivee',
                ),
                token_pwa_destinataire=token_pwa_destinataire,
            )
            return render(
                request,
                self.template_name,
                {
                    'demande': demande,
                    'error': "Coordonnées GPS reçues invalides.",
                    'token': token_pwa_destinataire,
                },
            )

        with transaction.atomic():
            # Le verrou garantit que deux soumissions concurrentes ne déclenchent
            # qu'une notification lors de la première validation.
            demande = get_object_or_404(
                DemandeLivraison.objects.select_for_update(),
                token_pwa_destinataire=token_pwa_destinataire,
            )
            premiere_validation = not demande.position_destinataire_validee
            demande.latitude_destinataire_reelle = latitude
            demande.longitude_destinataire_reelle = longitude
            demande.position_destinataire_validee = True
            demande.statut_position_destinataire = 'position_recue'
            demande.save(update_fields=[
                'latitude_destinataire_reelle',
                'longitude_destinataire_reelle',
                'position_destinataire_validee',
                'statut_position_destinataire',
            ])

        notification_warning = ''
        # La PWA peut être réutilisée pour corriger les coordonnées, mais la Web Push
        # n'est déclenchée qu'au premier passage à l'état validé.
        if (
            premiere_validation
            and demande.livreur_id
            and demande.statut in ('acceptee', 'en_cours')
        ):
            notification_programmee = (
                programmer_notification_position_destinataire(demande)
            )
            if not notification_programmee:
                notification_warning = (
                    "Votre position a été enregistrée, mais la notification du client "
                    "n'a pas pu être programmée."
                )

        if request.headers.get('HX-Request') == 'true':
            return render(
                request,
                'partials/demande_livraison/destinataire_geo_success.html',
                {
                    'demande': demande,
                    'notification_warning': notification_warning,
                },
            )

        return render(
            request,
            self.template_name,
            {
                'demande': demande,
                'deja_valide': True,
                'success': True,
                'token': token_pwa_destinataire,
                'notification_warning': notification_warning,
            },
        )
