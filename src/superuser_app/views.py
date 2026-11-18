from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Count, DecimalField, IntegerField, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from articles_app.models import Article
from blocs_app.models import Blocs
from entreprise_app.models import Entreprise, MembreAdminsEntreprise, RetraitEntreprise
from entreprise_app.views import obtenir_solde_entreprise
from superuser_app.forms import BlocForm


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin personnalisé de contrôle d'accès :
    Vérifie rigoureusement que l'utilisateur est authentifié, actif et possède
    les droits de Superuser.
    Redirige vers l'accueil avec un message d'alerte explicite si l'accès est refusé.
    """
    login_url = reverse_lazy('home_app:home')
    redirect_field_name = 'next'

    def test_func(self):
        user = self.request.user
        return bool(user.is_authenticated and user.is_active and user.is_superuser)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            messages.warning(self.request, "Veuillez vous connecter pour accéder au cockpit Superuser.")
            return super().handle_no_permission()
        messages.error(
            self.request,
            "Accès refusé. Cette section est strictement réservée à l'administration centrale (Superuser)."
        )
        return redirect('home_app:home')


class SuperuserDashboardView(SuperuserRequiredMixin, TemplateView):
    """
    Cockpit de pilotage central pour le Superuser BAKAMZONE.
    Permet la création et la supervision des blocs, équipes admins et livreurs.
    """
    template_name = 'superuser_template/superuser.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bloc_form'] = BlocForm()
        context['blocs'] = Blocs.objects.all().order_by('-date_creation')
        context['total_blocs'] = context['blocs'].count()
        context['total_entreprises'] = Entreprise.objects.count()
        context['total_retraits_attente'] = RetraitEntreprise.objects.filter(
            statut=RetraitEntreprise.STATUT_EN_ATTENTE
        ).count()
        return context


class ListeEntrepriseViewBySuperUser(SuperuserRequiredMixin, ListView):
    """
    Vue liste des entreprises partenaires pour le Superuser.
    Permet de visualiser l'ensemble des entreprises inscrites, leurs quotas,
    ainsi que les alertes sur les demandes de retraits de fonds en attente.
    """
    model = Entreprise
    template_name = 'superuser_template/entreprise_list.html'
    context_object_name = 'entreprises'
    paginate_by = 12

    def get_queryset(self):
        montant_retraits_subquery = Subquery(
            RetraitEntreprise.objects.filter(
                entreprise=OuterRef('pk'),
                statut=RetraitEntreprise.STATUT_EN_ATTENTE,
            )
            .values('entreprise')
            .annotate(total=Sum('montant'))
            .values('total')[:1],
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )

        nb_retraits_subquery = Subquery(
            RetraitEntreprise.objects.filter(
                entreprise=OuterRef('pk'),
                statut=RetraitEntreprise.STATUT_EN_ATTENTE,
            )
            .values('entreprise')
            .annotate(cnt=Count('id'))
            .values('cnt')[:1],
            output_field=IntegerField(),
        )

        nb_articles_subquery = Subquery(
            Article.objects.filter(
                entreprise=OuterRef('pk'),
                disponible=True,
            )
            .values('entreprise')
            .annotate(cnt=Count('id'))
            .values('cnt')[:1],
            output_field=IntegerField(),
        )

        nb_admins_subquery = Subquery(
            MembreAdminsEntreprise.objects.filter(
                entreprise=OuterRef('pk'),
            )
            .values('entreprise')
            .annotate(cnt=Count('id'))
            .values('cnt')[:1],
            output_field=IntegerField(),
        )

        queryset = (
            Entreprise.objects.select_related('user_principal')
            .annotate(
                nb_articles_disponibles=Coalesce(nb_articles_subquery, 0),
                nb_admins=Coalesce(nb_admins_subquery, 0),
                nb_retraits_attente=Coalesce(nb_retraits_subquery, 0),
                montant_retraits_attente=Coalesce(montant_retraits_subquery, Decimal('0.00')),
            )
            .order_by('-nb_retraits_attente', '-date_creation')
        )

        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(nom_entreprise__icontains=q)
                | Q(rc_number__icontains=q)
                | Q(user_principal__telephone__icontains=q)
                | Q(user_principal__first_name__icontains=q)
                | Q(user_principal__last_name__icontains=q)
                | Q(user_principal__email__icontains=q)
            )

        palier = self.request.GET.get('palier', '').strip()
        if palier and palier in dict(Entreprise.PALIER_CHOICES):
            queryset = queryset.filter(palier=palier)

        filtre_retrait = self.request.GET.get('retrait', '').strip()
        if filtre_retrait == 'en_attente':
            queryset = queryset.filter(nb_retraits_attente__gt=0)

        abonnement = self.request.GET.get('abonnement', '').strip()
        if abonnement == 'actif':
            queryset = queryset.filter(subscription_active=True)
        elif abonnement == 'inactif':
            queryset = queryset.filter(subscription_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        retraits_attente_qs = RetraitEntreprise.objects.filter(
            statut=RetraitEntreprise.STATUT_EN_ATTENTE
        )
        context['total_entreprises'] = Entreprise.objects.count()
        context['total_retraits_en_attente'] = retraits_attente_qs.count()
        context['montant_total_retraits_en_attente'] = (
            retraits_attente_qs.aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
        )
        context['search_query'] = self.request.GET.get('q', '').strip()
        context['selected_palier'] = self.request.GET.get('palier', '').strip()
        context['selected_retrait'] = self.request.GET.get('retrait', '').strip()
        context['selected_abonnement'] = self.request.GET.get('abonnement', '').strip()
        context['palier_choices'] = Entreprise.PALIER_CHOICES
        return context

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return ["partials/superuser/entreprise_list_results.html"]
        return [self.template_name]


class EntrepriseDetailViewBySuperUser(SuperuserRequiredMixin, DetailView):
    """
    Fiche détaillée d'une entreprise partenaire pour le Superuser.
    Présente l'état financier complet (chiffre d'affaires, solde disponible),
    la liste de ses articles (en bloc / hors bloc), son équipe d'administration
    et l'historique complet de ses demandes de retrait de fonds avec leurs statuts.
    """
    model = Entreprise
    template_name = 'superuser_template/entreprise_detail.html'
    context_object_name = 'entreprise'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entreprise = self.object

        # Calcul financier et comptable
        solde_data = obtenir_solde_entreprise(entreprise)
        context['solde_data'] = solde_data

        # Articles
        articles_qs = entreprise.articles.all().order_by('-date_creation')
        context['articles'] = articles_qs
        context['articles_en_bloc'] = articles_qs.filter(en_bloc=True)
        context['articles_hors_bloc'] = articles_qs.filter(en_bloc=False)
        context['total_articles'] = articles_qs.count()
        context['articles_disponibles_count'] = articles_qs.filter(disponible=True).count()

        # Administrateurs
        context['membres_admin'] = entreprise.membres_admin.select_related(
            'membre_admin', 'ajoute_par'
        ).order_by('-date_ajout')

        # Demandes de retraits
        retraits_qs = entreprise.retraits.select_related('traite_par').order_by('-date_demande')
        context['retraits'] = retraits_qs
        context['retraits_en_attente'] = retraits_qs.filter(statut=RetraitEntreprise.STATUT_EN_ATTENTE)
        context['nb_retraits_en_attente'] = context['retraits_en_attente'].count()
        context['retraits_traites'] = retraits_qs.exclude(statut=RetraitEntreprise.STATUT_EN_ATTENTE)

        return context


class TraiterDemandeRetraitView(SuperuserRequiredMixin, View):
    """
    Traite une demande de retrait effectuée par une entreprise partenaire.
    Actions autorisées :
      - 'approuver' : valide la demande pour mise en paiement (statut 'approuve').
      - 'payer' : clôture et valide le versement effectif (statut 'paye').
      - 'rejeter' : refuse la demande avec motif obligatoire (statut 'rejete'),
                   ce qui libère immédiatement les fonds dans le solde disponible.
    """

    def post(self, request, pk, *args, **kwargs):
        action = request.POST.get("action", "").strip().lower()
        commentaire = request.POST.get("commentaire", "").strip()

        with transaction.atomic():
            retrait = get_object_or_404(
                RetraitEntreprise.objects.select_for_update().select_related("entreprise"),
                pk=pk,
            )

            if action in ["approuver", "accepter"]:
                retrait.statut = RetraitEntreprise.STATUT_APPROUVE
                statut_label = "approuvée"
            elif action == "payer":
                retrait.statut = RetraitEntreprise.STATUT_PAYE
                statut_label = "marquée comme payée"
            elif action in ["rejeter", "refuser"]:
                if not commentaire:
                    messages.error(
                        request,
                        "Un motif ou commentaire est strictement obligatoire pour refuser une demande de retrait.",
                    )
                    return redirect("superuser_app:detail-entreprise", pk=retrait.entreprise.pk)
                retrait.statut = RetraitEntreprise.STATUT_REJETE
                statut_label = "rejetée"
            else:
                messages.error(request, f"Action « {action} » non reconnue.")
                return redirect("superuser_app:detail-entreprise", pk=retrait.entreprise.pk)

            retrait.date_traitement = timezone.now()
            retrait.traite_par = request.user
            retrait.commentaire = commentaire
            retrait.save(update_fields=["statut", "date_traitement", "traite_par", "commentaire"])

        messages.success(
            request,
            f"La demande de retrait de {retrait.montant:,.0f} FCFA pour {retrait.entreprise.nom_entreprise} a été {statut_label} avec succès.",
        )
        return redirect("superuser_app:detail-entreprise", pk=retrait.entreprise.pk)
