from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView
from demande_livraison_app.models import DemandeLivraison
from demande_livraison_app.pricing import calculer_tarif_livraison
from panier_app.models import ArticlePanier, Commande, LigneCommande, Panier
from .forms import (
    ChoixPalierEntrepriseForm,
    DemandeLivraisonArticleForm,
    DemandeRetraitEntrepriseForm,
    InscriptionEntrepriseForm,
    MembreAdminsEntrepriseForm,
)
from .models import Entreprise, MembreAdminsEntreprise, RetraitEntreprise

User = get_user_model()

STATUTS_COURSE_EXISTANTE = ("en_attente", "acceptee", "en_cours", "livree")
MONTANT_LIGNE_COMMANDE = ExpressionWrapper(
    F("quantite") * F("prix_unitaire"),
    output_field=DecimalField(max_digits=14, decimal_places=2),
)


class EntrepriseRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy("home_app:home")

    def test_func(self):
        return (
            self.request.user.role == "entreprise"
            and Entreprise.objects.filter(
                user_principal=self.request.user,
            ).exists()
        )

    def get_entreprise(self):
        return get_object_or_404(
            Entreprise,
            user_principal=self.request.user,
            user_principal__role="entreprise",
        )


def obtenir_solde_entreprise(entreprise):
    ventes_payees = LigneCommande.objects.filter(
        entreprise=entreprise,
        commande__statut_paiement=Commande.PAIEMENT_REUSSI,
    )
    maintenant = timezone.localtime()
    ventes_mois = ventes_payees.filter(
        commande__date_paiement__year=maintenant.year,
        commande__date_paiement__month=maintenant.month,
    )
    demandes_retrait = RetraitEntreprise.objects.filter(
        entreprise=entreprise,
    )
    montant_ventes = ventes_payees.aggregate(
        total=Sum(MONTANT_LIGNE_COMMANDE),
    )["total"] or Decimal("0.00")
    montant_ventes_mois = ventes_mois.aggregate(
        total=Sum(MONTANT_LIGNE_COMMANDE),
    )["total"] or Decimal("0.00")
    montant_reserve = demandes_retrait.filter(
        statut__in=[
            RetraitEntreprise.STATUT_EN_ATTENTE,
            RetraitEntreprise.STATUT_APPROUVE,
            RetraitEntreprise.STATUT_PAYE,
        ],
    ).aggregate(total=Sum("montant"))["total"] or Decimal("0.00")
    montant_disponible = montant_ventes - montant_reserve
    return {
        "montant_ventes": montant_ventes,
        "montant_ventes_mois": montant_ventes_mois,
        "montant_retraits_reserves": montant_reserve,
        "montant_disponible": max(montant_disponible, 0),
        "ventes_payees": ventes_payees.select_related(
            "article",
            "commande__client__user",
        ).order_by("-commande__date_paiement", "-pk")[:100],
        "demandes_retrait": demandes_retrait.select_related(
            "traite_par",
        ),
    }


class EntrepriseSoldeView(EntrepriseRequiredMixin, TemplateView):
    template_name = "entreprise_templates/entreprise_solde.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entreprise = self.get_entreprise()
        context.update({
            "entreprise": entreprise,
            "solde": obtenir_solde_entreprise(entreprise),
            "form_retrait": DemandeRetraitEntrepriseForm(),
        })
        return context


class DemanderRetraitEntrepriseView(EntrepriseRequiredMixin, View):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        entreprise = get_object_or_404(
            Entreprise.objects.select_for_update(),
            user_principal=request.user,
            user_principal__role="entreprise",
        )
        form = DemandeRetraitEntrepriseForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Saisissez un montant valide supérieur à zéro.")
            return redirect("entreprise_app:solde")

        solde = obtenir_solde_entreprise(entreprise)
        montant = form.cleaned_data["montant"]
        if montant > solde["montant_disponible"]:
            messages.error(
                request,
                "Le montant demandé dépasse votre solde disponible.",
            )
            return redirect("entreprise_app:solde")

        RetraitEntreprise.objects.create(
            entreprise=entreprise,
            montant=montant,
        )
        messages.success(
            request,
            "Votre demande de retrait a été enregistrée et sera examinée par l'administration.",
        )
        return redirect("entreprise_app:solde")


class EntrepriseLivraisonsArticlesView(EntrepriseRequiredMixin, TemplateView):
    template_name = "entreprise_templates/entreprise_livraisons_articles.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entreprise = self.get_entreprise()
        lignes_commande = list(LigneCommande.objects.filter(
            entreprise=entreprise,
            article__entreprise=entreprise,
            article__en_bloc=False,
            commande__statut_paiement=Commande.PAIEMENT_REUSSI,
        ).exclude(
            commande__statut=Commande.STATUT_ANNULEE,
        ).select_related(
            "article",
            "commande__zone_arrivee__bloc",
            "commande__client__user",
        ).order_by("-commande__date_creation", "commande_id", "id"))
        lignes_par_commande = {}
        for ligne in lignes_commande:
            lignes_par_commande.setdefault(ligne.commande_id, []).append(ligne)

        demandes = DemandeLivraison.objects.filter(
            Q(ligne_commande__in=lignes_commande)
            | Q(lignes_commande__in=lignes_commande),
        ).distinct().select_related(
            "zone_depart__bloc",
            "ligne_commande",
        ).prefetch_related(
            "lignes_commande",
        ).order_by("-date_creation")
        courses_par_commande = {}
        for demande in demandes:
            demande.lignes_livrees = list(demande.lignes_commande.all())
            if demande.ligne_commande_id:
                commande_id = demande.ligne_commande.commande_id
            else:
                commande_id = demande.lignes_livrees[0].commande_id
            if not demande.lignes_livrees and demande.ligne_commande_id:
                demande.lignes_livrees = [demande.ligne_commande]
            courses_par_commande.setdefault(commande_id, []).append(demande)

        commandes_entreprise = [
            {
                "commande": lignes[0].commande,
                "lignes": lignes,
                "courses_livraison": courses_par_commande.get(commande_id, []),
                "peut_creer_course": not any(
                    demande.statut in STATUTS_COURSE_EXISTANTE
                    for demande in courses_par_commande.get(commande_id, [])
                ),
            }
            for commande_id, lignes in lignes_par_commande.items()
        ]
        context.update({
            "entreprise": entreprise,
            "commandes_entreprise": commandes_entreprise,
            "livraison_form": DemandeLivraisonArticleForm(),
        })
        return context


class CreerLivraisonCommandeEntrepriseView(EntrepriseRequiredMixin, View):
    @transaction.atomic
    def post(self, request, commande_id, *args, **kwargs):
        entreprise = self.get_entreprise()
        lignes = list(
            LigneCommande.objects.select_for_update().select_related(
                "article",
                "commande__client__user",
                "commande__zone_arrivee",
            ).filter(
                commande_id=commande_id,
                entreprise=entreprise,
                article__entreprise=entreprise,
                article__en_bloc=False,
                commande__statut_paiement=Commande.PAIEMENT_REUSSI,
            ).order_by("pk")
        )
        if not lignes:
            raise Http404

        commande = lignes[0].commande
        if commande.statut == Commande.STATUT_ANNULEE:
            messages.error(request, "Une commande annulée ne peut pas être expédiée.")
            return redirect("entreprise_app:livraisons-articles")

        form = DemandeLivraisonArticleForm(request.POST)
        if not form.is_valid():
            messages.error(
                request,
                "Choisissez une zone de départ valide avec des coordonnées GPS.",
            )
            return redirect("entreprise_app:livraisons-articles")

        lignes_ids = [ligne.pk for ligne in lignes]
        if DemandeLivraison.objects.filter(
            Q(ligne_commande__in=lignes_ids)
            | Q(lignes_commande__in=lignes_ids),
            statut__in=STATUTS_COURSE_EXISTANTE,
        ).exists():
            messages.info(request, "Une course existe déjà pour cette commande.")
            return redirect("entreprise_app:livraisons-articles")

        zone_depart = form.cleaned_data["zone_depart"]
        zone_arrivee = commande.zone_arrivee
        telephone_destinataire = commande.client.user.telephone
        latitude_depart = form.cleaned_data["latitude_depart"]
        longitude_depart = form.cleaned_data["longitude_depart"]
        description = "; ".join(
            f"{ligne.nom_article} × {ligne.quantite}"
            for ligne in lignes
        ) + f" — commande {commande.reference}"
        demande = DemandeLivraison.objects.create(
            client=commande.client,
            ligne_commande=lignes[0],
            zone_depart=zone_depart,
            zone_arrivee=zone_arrivee,
            latitude_depart=latitude_depart,
            longitude_depart=longitude_depart,
            latitude_arrivee=commande.latitude_livraison,
            longitude_arrivee=commande.longitude_livraison,
            description_colis=description,
            prix=calculer_tarif_livraison(zone_depart, zone_arrivee),
            position_destinataire_validee=True,
            latitude_destinataire_reelle=commande.latitude_livraison,
            longitude_destinataire_reelle=commande.longitude_livraison,
            statut_destinataire="position_recue",
            whatsapp_destinataire=telephone_destinataire,
        )
        demande.lignes_commande.set(lignes)
        messages.success(
            request,
            f"La course groupée #{demande.pk} est publiée aux livreurs du bloc "
            f"{zone_depart.bloc.nom}. Aucun frais n'a été encaissé.",
        )
        return redirect("entreprise_app:livraisons-articles")


class EntrepriseDashboardContextMixin:
    def get_dashboard_context(self, entreprise, context=None):
        context = context or {}
        admin_form = context.get("form")
        if admin_form is None:
            admin_form = MembreAdminsEntrepriseForm(entreprise=entreprise)
        available_article_count = entreprise.articles.filter(
            disponible=True
        ).count()
        panier_stats = {
            row["article_id"]: row
            for row in ArticlePanier.objects.filter(
                article__entreprise=entreprise,
                panier__statut=Panier.STATUT_ACTIF,
            ).values("article_id").annotate(
                paniers_actifs=Count("panier_id", distinct=True),
                quantite_panier=Sum("quantite"),
            )
        }
        commande_stats = {
            row["article_id"]: row
            for row in LigneCommande.objects.filter(
                entreprise=entreprise,
            ).exclude(
                commande__statut=Commande.STATUT_ANNULEE,
            ).values("article_id").annotate(
                paniers_commandes=Count("commande__panier_id", distinct=True),
                quantite_commandee=Sum("quantite"),
                quantite_payee=Sum(
                    "quantite",
                    filter=Q(
                        commande__statut_paiement=Commande.PAIEMENT_REUSSI,
                    ),
                ),
            )
        }
        article_usage_stats = []
        stats_totaux = {
            "paniers_actifs": 0,
            "quantite_panier": 0,
            "paniers_commandes": 0,
            "quantite_commandee": 0,
            "quantite_payee": 0,
        }
        for article in entreprise.articles.order_by("nom"):
            active_stats = panier_stats.get(article.pk, {})
            order_stats = commande_stats.get(article.pk, {})
            stats = {
                "article": article,
                "paniers_actifs": active_stats.get("paniers_actifs", 0),
                "quantite_panier": active_stats.get("quantite_panier") or 0,
                "paniers_commandes": order_stats.get("paniers_commandes", 0),
                "quantite_commandee": order_stats.get("quantite_commandee") or 0,
                "quantite_payee": order_stats.get("quantite_payee") or 0,
            }
            article_usage_stats.append(stats)
            for key in stats_totaux:
                if key not in {"paniers_actifs", "paniers_commandes"}:
                    stats_totaux[key] += stats[key]

        stats_totaux["paniers_actifs"] = ArticlePanier.objects.filter(
            article__entreprise=entreprise,
            panier__statut=Panier.STATUT_ACTIF,
        ).values("panier_id").distinct().count()
        stats_totaux["paniers_commandes"] = LigneCommande.objects.filter(
            entreprise=entreprise,
        ).exclude(
            commande__statut=Commande.STATUT_ANNULEE,
        ).values("commande__panier_id").distinct().count()

        context.update({
            "entreprise": entreprise,
            "solde_entreprise": obtenir_solde_entreprise(entreprise),
            "admin_members": entreprise.membres_admin.select_related(
                "membre_admin",
                "ajoute_par",
            ).order_by("-date_ajout"),
            "article_count": entreprise.articles.count(),
            "available_article_count": available_article_count,
            "admin_count": entreprise.nb_admins_actuels,
            "admin_form": admin_form,
            "article_usage_stats": article_usage_stats,
            "article_usage_totals": stats_totaux,
        })
        context["can_add_admin"] = context["admin_count"] < entreprise.quota_admins
        context["can_add_article"] = available_article_count < entreprise.quota_articles
        return context


class InscriptionEntrepriseView(CreateView):
    form_class = InscriptionEntrepriseForm
    template_name = "auth_templates/entreprise_register.html"
    success_url = reverse_lazy("home_app:home")

    def form_valid(self, form):
        try:
            self.object = form.save()
        except IntegrityError:
            if not User.objects.filter(
                telephone=form.cleaned_data["telephone"]
            ).exists():
                raise
            form.add_error(
                "telephone",
                "Ce numéro de téléphone vient d'être utilisé. Veuillez en choisir un autre.",
            )
            return self.form_invalid(form)

        if self.request.headers.get("HX-Request") == "true":
            response = render(
                self.request,
                "partials/result/entreprise_success.html",
            )
            response["HX-Trigger"] = "entreprise-register-success"
            return response

        messages.success(
            self.request,
            "Le compte de votre entreprise est créé. Connectez-vous pour choisir "
            "votre palier d'abonnement.",
        )
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        if self.request.headers.get("HX-Request") == "true":
            errors = [
                (
                    form.fields[field].label if field in form.fields else "Formulaire",
                    error,
                )
                for field, field_errors in form.errors.items()
                for error in field_errors
            ]
            return render(
                self.request,
                "partials/result/entreprise_error.html",
                {"errors": errors},
            )

        return super().form_invalid(form)

class InscriptionEntrepriseAdminView(
    EntrepriseDashboardContextMixin,
    LoginRequiredMixin,
    CreateView,
):
    form_class = MembreAdminsEntrepriseForm
    template_name = "entreprise_templates/entreprise_detail.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if (
            request.user.role != "entreprise"
            or not Entreprise.objects.filter(user_principal=request.user).exists()
        ):
            messages.error(
                request,
                "Seul le responsable d'une entreprise peut créer un compte administrateur.",
            )
            return redirect("home_app:home")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return redirect("entreprise_app:entreprise-detail")

    def get_entreprise(self):
        if not hasattr(self, "entreprise"):
            self.entreprise = get_object_or_404(
                Entreprise,
                user_principal=self.request.user,
            )
        return self.entreprise

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.pop("instance", None)
        kwargs["entreprise"] = self.get_entreprise()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return self.get_dashboard_context(self.get_entreprise(), context)

    @transaction.atomic
    def form_valid(self, form):
        entreprise = get_object_or_404(
            Entreprise.objects.select_for_update(),
            user_principal=self.request.user,
        )
        form.entreprise = entreprise
        quota = entreprise.quota_admins
        if entreprise.nb_admins_actuels >= quota:
            if quota == 0:
                form.add_error(
                    None,
                    "Choisissez d'abord un palier d'abonnement pour obtenir un quota "
                    "d'administrateurs.",
                )
            else:
                form.add_error(
                    None,
                    f"Le quota de {quota} administrateur(s) de votre palier est atteint.",
                )
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                self.object = form.save()
        except IntegrityError:
            if not User.objects.filter(
                telephone=form.cleaned_data["telephone"]
            ).exists():
                raise
            form.add_error(
                "telephone",
                "Ce numéro de téléphone vient d'être utilisé. Veuillez en choisir un autre.",
            )
            return self.form_invalid(form)

        registration_success = {
            "membre_admin": self.object,
            "username": form.generated_username,
            "password": form.generated_password,
            "dashboard_refresh": self.request.headers.get("HX-Request") == "true",
        }
        registration_success.update(
            self.get_dashboard_context(entreprise)
        )
        if self.request.headers.get("HX-Request") == "true":
            response = render(
                self.request,
                "partials/result/entreprise_admin_success.html",
                registration_success,
            )
            response["HX-Trigger"] = "entreprise-admin-register-success"
            return response

        return render(
            self.request,
            self.template_name,
            {
                "form": self.get_form_class()(entreprise=entreprise),
                "registration_success": registration_success,
                **self.get_dashboard_context(entreprise),
            },
        )

    def form_invalid(self, form):
        if self.request.headers.get("HX-Request") == "true":
            errors = [
                (
                    form.fields[field].label if field in form.fields else "Formulaire",
                    error,
                )
                for field, field_errors in form.errors.items()
                for error in field_errors
            ]
            return render(
                self.request,
                "partials/result/entreprise_admin_error.html",
                {"errors": errors},
            )

        return render(
            self.request,
            self.template_name,
            self.get_dashboard_context(self.get_entreprise(), {"form": form}),
        )

class ChoixPalierEntrepriseView(UpdateView):
    model = Entreprise
    form_class = ChoixPalierEntrepriseForm
    template_name = "entreprise_templates/choix_palier.html"
    success_url = reverse_lazy("home_app:home")

    DESCRIPTIONS_PALIERS = {
        "standard": "Pour démarrer avec une présence simple dans le réseau.",
        "pro": "Pour développer votre activité et gérer plusieurs administrateurs.",
        "premium": "Pour les entreprises ayant des besoins de gestion plus importants.",
    }

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(
                request,
                "Connectez-vous avec le compte de votre entreprise pour choisir un palier.",
            )
            return redirect("home_app:home")
        if not Entreprise.objects.filter(user_principal=request.user).exists():
            messages.error(
                request,
                "Seul le responsable d'un compte entreprise peut choisir son palier.",
            )
            return redirect("home_app:home")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return Entreprise.objects.get(user_principal=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["paliers"] = [
            {
                "value": value,
                "label": label,
                "description": self.DESCRIPTIONS_PALIERS[value],
                "quota_articles": Entreprise.QUOTAS_ARTICLES[value],
                "quota_admins": Entreprise.QUOTAS_ADMINS[value],
            }
            for value, label in Entreprise.PALIER_CHOICES
            if value != "pas_defini"
        ]
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "Votre palier a été enregistré. L'abonnement reste inactif tant qu'il "
            "n'a pas été activé par le processus de souscription.",
        )
        return response


class EntrepriseDetailView(
    EntrepriseDashboardContextMixin,
    LoginRequiredMixin,
    DetailView,
):
    model = Entreprise
    template_name = "entreprise_templates/entreprise_detail.html"
    context_object_name = "entreprise"

    def get_object(self, queryset=None):
        return get_object_or_404(
            Entreprise,
            user_principal=self.request.user,
            user_principal__role="entreprise",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return self.get_dashboard_context(self.object, context)