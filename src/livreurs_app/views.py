from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, TemplateView
from kombu.exceptions import OperationalError as CeleryOperationalError

from bakam_zone.tasks import envoyer_notification_smartdrop_destinataire_task
from demande_livraison_app.models import DemandeLivraison
from livreurs_app.forms import InscriptionLivreurForm
from livreurs_app.models import Livreur


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


class InscriptionLivreurView(SuperuserRequiredMixin, CreateView):
    model = Livreur
    form_class = InscriptionLivreurForm
    template_name = 'auth_templates/livreurs_register.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['admin_user'] = self.request.user
        return context

    def form_valid(self, form):
        self.object = form.save()
        context = {
            'livreur': self.object,
            'username': form.generated_username,
            'password': form.generated_password,
            'admin_user': self.request.user,
        }
        if self.request.headers.get('HX-Request') == 'true':
            response = render(
                self.request,
                'partials/result/livreur_success.html',
                context,
            )
            response['HX-Trigger'] = 'livreur-register-success'
            return response

        return render(self.request, self.template_name, {
            'form': self.get_form_class()(),
            'registration_success': context,
            **context,
        })

    def form_invalid(self, form):
        if self.request.headers.get('HX-Request') == 'true':
            errors = [
                (
                    form.fields[field].label if field in form.fields else 'Formulaire',
                    error,
                )
                for field, field_errors in form.errors.items()
                for error in field_errors
            ]
            return render(
                self.request,
                'partials/result/livreur_error.html',
                {'errors': errors, 'admin_user': self.request.user},
            )

        return super().form_invalid(form)


# ==============================================================================
# ESPACE LIVREUR : Dashboard personnel, gestion des courses et dispatch
# ==============================================================================

class LivreurRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Garantit que l'utilisateur connecté est un livreur avec profil actif."""
    login_url = reverse_lazy('home_app:home')

    def test_func(self):
        return (
            self.request.user.is_authenticated
            and self.request.user.role == 'livreur'
            and hasattr(self.request.user, 'livreur_profil')
            and self.request.user.livreur_profil.actif
        )


class LivreurProfilViewByLivreur(LivreurRequiredMixin, TemplateView):
    """
    Tableau de bord personnel du livreur :
    - Présentation profil & statut (En ligne / Hors ligne)
    - Demandes en attente (assignées directement ou disponibles dans son bloc)
    - Courses actives (avec suivi du Smart-Drop destinataire)
    - Historique des courses livrées
    """
    template_name = 'livreurs_templates/livreur_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        livreur = self.request.user.livreur_profil

        # 1. Demandes en attente (soit directement pour lui, soit ouvertes sur son bloc)
        demandes_en_attente = DemandeLivraison.objects.filter(
            statut='en_attente',
        ).filter(
            Q(livreur=livreur)
            | Q(livreur__isnull=True, zone_depart__bloc=livreur.blocs)
        ).select_related(
            'client__user',
            'zone_depart',
            'zone_arrivee',
        ).order_by('-date_creation')

        # 2. Courses actives (acceptées ou en cours)
        courses_actives = DemandeLivraison.objects.filter(
            livreur=livreur,
            statut__in=['acceptee', 'en_cours'],
        ).select_related(
            'client__user',
            'zone_depart',
            'zone_arrivee',
        ).order_by('-date_creation')

        # 3. Historique récent (courses terminées)
        courses_terminees = DemandeLivraison.objects.filter(
            livreur=livreur,
            statut__in=['livree', 'annulee'],
        ).select_related(
            'client__user',
            'zone_depart',
            'zone_arrivee',
        ).order_by('-date_creation')[:15]

        # 4. Avis récents
        avis_recents = livreur.avis.select_related('client__user').order_by('-date_creation')[:5]

        context.update({
            'livreur': livreur,
            'demandes_en_attente': demandes_en_attente,
            'courses_actives': courses_actives,
            'courses_terminees': courses_terminees,
            'avis_recents': avis_recents,
            'nb_favoris': livreur.nb_ajout_favoris,
        })
        return context


class AccepterDemandeLivraisonView(LivreurRequiredMixin, View):
    """
    Action pour le livreur d'accepter une demande de livraison.
    Déclenche l'envoi de la notification WhatsApp Smart-Drop au destinataire.
    """
    def post(self, request, pk, *args, **kwargs):
        livreur = request.user.livreur_profil
        demande_eligible = DemandeLivraison.objects.filter(
            pk=pk,
            statut='en_attente',
        ).filter(
            Q(livreur=livreur)
            | Q(livreur__isnull=True, zone_depart__bloc_id=livreur.blocs_id)
        )
        accepte = demande_eligible.update(
            livreur=livreur,
            statut='acceptee',
            date_acceptation=timezone.now(),
            statut_destinataire='en_attente',
        )
        if not accepte:
            messages.error(
                request,
                "Cette course n'est plus disponible ou ne relève pas de votre bloc.",
            )
            return redirect('livreurs_app:tableau-de-bord')

        demande = DemandeLivraison.objects.get(pk=pk)

        # Déclenchement Celery du message WhatsApp avec lien PWA éphémère
        base_url = request.build_absolute_uri('/')[:-1]
        try:
            envoyer_notification_smartdrop_destinataire_task.delay(
                demande.pk,
                base_url=base_url,
            )
        except CeleryOperationalError:
            messages.error(
                request,
                f"Course #{demande.pk} acceptée, mais la notification WhatsApp n'a pas pu être programmée. Veuillez prévenir l'assistance.",
            )
            return redirect('livreurs_app:tableau-de-bord')

        messages.success(
            request,
            f"Course #{demande.pk} acceptée. La notification WhatsApp de validation de position a été programmée.",
        )
        return redirect('livreurs_app:tableau-de-bord')


class RefuserDemandeLivraisonView(LivreurRequiredMixin, View):
    """
    Action pour le livreur de refuser une demande de livraison qui lui était destinée.
    Remet la demande en disponibilité pour les autres livreurs du bloc.
    """
    def post(self, request, pk, *args, **kwargs):
        livreur = request.user.livreur_profil
        demande = get_object_or_404(DemandeLivraison, pk=pk, statut='en_attente')

        if demande.livreur == livreur:
            demande.livreur = None
            demande.save(update_fields=['livreur'])
            messages.info(
                request,
                f"Course #{demande.pk} déclinée. Elle reste disponible pour les autres livreurs de votre bloc.",
            )

        return redirect('livreurs_app:tableau-de-bord')


class ChangerStatutCourseView(LivreurRequiredMixin, View):
    """
    Permet au livreur de faire avancer une course active :
    - 'en_cours' (colis récupéré)
    - 'livree' (colis remis au destinataire)
    """
    def post(self, request, pk, *args, **kwargs):
        livreur = request.user.livreur_profil
        demande = get_object_or_404(DemandeLivraison, pk=pk, livreur=livreur)
        nouveau_statut = request.POST.get('statut')

        if nouveau_statut in ['en_cours', 'livree']:
            demande.statut = nouveau_statut
            if nouveau_statut == 'livree':
                demande.date_livraison = timezone.now()
                Livreur.objects.filter(pk=livreur.pk).update(nb_livraisons=F('nb_livraisons') + 1)
            demande.save()
            messages.success(
                request,
                f"Course #{demande.pk} mise à jour : {demande.get_statut_display()}.",
            )

        return redirect('livreurs_app:tableau-de-bord')


class ToggleDisponibiliteLivreurView(LivreurRequiredMixin, View):
    """Bascule le statut de disponibilité en ligne / hors ligne du livreur."""
    def post(self, request, *args, **kwargs):
        livreur = request.user.livreur_profil
        livreur.disponible = not livreur.disponible
        livreur.save(update_fields=['disponible'])

        statut_label = "en ligne (disponible pour les courses)" if livreur.disponible else "hors ligne"
        messages.info(request, f"Vous êtes maintenant {statut_label}.")
        return redirect('livreurs_app:tableau-de-bord')
