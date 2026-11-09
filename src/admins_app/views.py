import json
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import CreateView, DetailView, ListView, TemplateView

from admins_app.forms import AdminBlocForms
from admins_app.models import AdminBloc
from articles_app.forms import ArticleBlocAdminForm
from entreprise_app.models import Entreprise
from articles_app.models import StockBloc
from clients_app.models import SupportConversation, SupportMessage

from demande_livraison_app.models import DemandeLivraison
from livreurs_app.models import Livreur
from notifications_app.services import programmer_notification_position_destinataire


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

class AdminBlocPostDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "admins_templates/admin_bloc_post_dashboard.html"
    poste = None
    dashboard_details = {
        "responsable": {
            "title": "Espace Responsable de Bloc",
            "description": "Supervision des activités et de l'équipe de votre bloc.",
        },
        "superviseur_flotte": {
            "title": "Espace Superviseur de Flotte",
            "description": "Suivi opérationnel de la flotte de livreurs de votre bloc.",
        },
        "assistant": {
            "title": "Espace Assistant Opérationnel",
            "description": "Accès aux opérations quotidiennes de votre bloc.",
        },
    }

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        admin_bloc = AdminBloc.objects.filter(
            user=request.user,
            poste=self.poste,
            actif=True,
        ).select_related("bloc").first()
        if request.user.role != "bloc_admin" or admin_bloc is None:
            return HttpResponseForbidden(
                "Ce tableau de bord n'est pas accessible à ce compte."
            )
        self.admin_bloc = admin_bloc
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "admin_bloc": self.admin_bloc,
            "bloc": self.admin_bloc.bloc,
            **self.dashboard_details[self.poste],
        })
        return context

class AdminBlocCreateView(SuperuserRequiredMixin, CreateView):
    model = AdminBloc
    form_class = AdminBlocForms
    template_name = 'blocs_templates/admin_bloc_register.html'

    def form_valid(self, form):
        self.object = form.save()
        
        response = render(
            self.request,
            'partials/result/admin_bloc_success.html',
            {
                'admin_bloc': self.object,
                'username': form.generated_username,
                'password': form.generated_password,
            },
        )
        response['HX-Trigger'] = json.dumps({
            'adminBlocCreated': {
                'id': self.object.pk,
                'nom': self.object.user.get_full_name(),
                'bloc': self.object.bloc.nom,
            },
        })
        return response

    def form_invalid(self, form):
        errors = [
            error
            for field_errors in form.errors.values()
            for error in field_errors
        ]
        response = render(
            self.request,
            'partials/result/admin_bloc_error.html',
            {'errors': errors},
        )
        response['HX-Trigger'] = 'adminBlocFormInvalid'
        return response


######################################################################################################
#________________________________________GESTIONNAIRE_DE_STOCK_____________________________________________
############################################################################################################################
class GestionnaireStockDashboardView(LoginRequiredMixin, ListView):
    model = Entreprise
    context_object_name = "entreprises"
    template_name = "admins_templates/gestionnaire_stock_dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        admin_bloc = AdminBloc.objects.filter(
            user=request.user,
            poste="gestionnaire_stock",
            actif=True,
        ).select_related("bloc", "user").first()
        if request.user.role != "bloc_admin" or admin_bloc is None:
            return HttpResponseForbidden(
                "Ce tableau de bord est réservé aux gestionnaires de stock actifs."
            )

        self.admin_bloc = admin_bloc
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Entreprise.objects.annotate(
            article_count=Count("articles", distinct=True),
        ).order_by("nom_entreprise")
        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(
                Q(nom_entreprise__icontains=search)
                | Q(address__icontains=search)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "admin_bloc": self.admin_bloc,
            "bloc": self.admin_bloc.bloc,
            "search_query": self.request.GET.get("q", ""),
        })
        return context

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return ["partials/admins/gestionnaire_stock_entreprises.html"]
        return [self.template_name]

class GestionnaireStockEntrepriseDetailView(LoginRequiredMixin, DetailView):
    model = Entreprise
    context_object_name = "entreprise"
    template_name = "admins_templates/gestionnaire_stock_entreprise_detail.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        self.admin_bloc = AdminBloc.objects.filter(
            user=request.user,
            poste="gestionnaire_stock",
            actif=True,
        ).select_related("bloc", "user").first()
        if request.user.role != "bloc_admin" or self.admin_bloc is None:
            return HttpResponseForbidden(
                "Cette page est réservée aux gestionnaires de stock actifs."
            )
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return get_object_or_404(
            Entreprise.objects,
            pk=self.kwargs["pk"],
        )

    def get_context_data(self, **kwargs):
        """Expose the block, scoped articles, and their management forms."""
        article_form = kwargs.pop("article_form", None)
        form_article = kwargs.pop("form_article", None)
        open_modal = kwargs.pop("open_modal", None)
        context = super().get_context_data(**kwargs)
        articles = list(
            self.object.articles.prefetch_related(
                Prefetch(
                    "stocks_blocs",
                    queryset=StockBloc.objects.filter(bloc=self.admin_bloc.bloc),
                    to_attr="stock_du_bloc",
                ),
            ).order_by("-date_creation")
        )
        for article in articles:
            article.admin_form = (
                article_form
                if article == form_article
                else ArticleBlocAdminForm(
                    user=self.request.user,
                    entreprise=self.object,
                    instance=article,
                )
            )
        context.update({
            "admin_bloc": self.admin_bloc,
            "bloc": self.admin_bloc.bloc,
            "articles": articles,
            "create_article_form": (
                article_form
                if form_article is None and article_form is not None
                else ArticleBlocAdminForm(
                    user=self.request.user,
                    entreprise=self.object,
                )
            ),
            "open_modal": open_modal,
        })
        return context




###########################################################################################################################""
#_____________________________________________SUPERVISEUR_FLOTTE________________________________________
############################################################################################################################
class SuperviseurFlotteRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        self.admin_bloc = AdminBloc.objects.filter(
            user=request.user,
            poste="superviseur_flotte",
            actif=True,
        ).select_related("bloc", "user").first()
        if request.user.role != "bloc_admin" or self.admin_bloc is None:
            return HttpResponseForbidden(
                "Cet espace est réservé aux superviseurs de flotte actifs."
            )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "admin_bloc": self.admin_bloc,
            "bloc": self.admin_bloc.bloc,
        })
        return context


class LivreurListView(SuperviseurFlotteRequiredMixin, ListView):
    model = Livreur
    context_object_name = "livreurs"
    template_name = "admins_templates/superviseur_livreurs.html"
    title = "Espace Superviseur de Flotte"
    description = "Suivi opérationnel de la flotte de livreurs de votre bloc."

    def get_queryset(self):
        queryset = Livreur.objects.filter(
            blocs=self.admin_bloc.bloc,
        ).select_related("user", "blocs", "zone_actuelle").order_by(
            "user__last_name",
            "user__first_name",
        )
        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__telephone__icontains=search)
                | Q(user__username__icontains=search)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "title": self.title,
            "description": self.description,
            "search_query": self.request.GET.get("q", ""),
        })
        return context

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return ["partials/admins/superviseur_flotte_livreurs.html"]
        return [self.template_name]


class DemandeLivraisonListView(SuperviseurFlotteRequiredMixin, ListView):
    model = DemandeLivraison
    context_object_name = "demandes_livraison"
    template_name = "admins_templates/superviseur_demandes_livraison.html"

    def get_queryset(self):
        bloc = self.admin_bloc.bloc
        queryset = DemandeLivraison.objects.filter(
            Q(zone_depart__bloc=bloc)
            | Q(zone_arrivee__bloc=bloc)
            | Q(livreur__blocs=bloc)
        ).select_related(
            "client__user",
            "livreur__user",
            "zone_depart",
            "zone_arrivee",
        ).distinct()
        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(
                Q(client__user__first_name__icontains=search)
                | Q(client__user__last_name__icontains=search)
                | Q(client__user__telephone__icontains=search)
                | Q(description_colis__icontains=search)
                | Q(zone_depart__nom__icontains=search)
                | Q(zone_arrivee__nom__icontains=search)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        return context


class SuperviseurFlotteDashbordView(SuperviseurFlotteRequiredMixin, TemplateView):
    template_name = "admins_templates/superviseur_flotte_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bloc = self.admin_bloc.bloc
        demandes_livraison = DemandeLivraison.objects.filter(
            Q(zone_depart__bloc=bloc)
            | Q(zone_arrivee__bloc=bloc)
            | Q(livreur__blocs=bloc)
        ).distinct()
        suivi_livraisons = DemandeLivraison.objects.filter(
            statut__in=("acceptee", "en_cours"),
            livreur__blocs=bloc,
            livreur__actif=True,
            position_destinataire_validee=True,
            latitude_destinataire_reelle__isnull=False,
            longitude_destinataire_reelle__isnull=False,
        ).select_related(
            "client__user",
            "livreur__user",
            "zone_depart",
            "zone_arrivee",
        ).order_by("-date_creation")
        context.update({
            "livreurs_count": Livreur.objects.filter(blocs=bloc).count(),
            "demandes_livraison_count": demandes_livraison.count(),
            "suivi_livraisons": suivi_livraisons,
            "tracking_config": {
                "tile_url": settings.OPENSTREETMAP_TILE_URL,
                "deliveries": [{
                    "id": demande.pk,
                    "label": f"Livraison #{demande.pk}",
                    "livreur": demande.livreur.user.get_full_name(),
                    "client": demande.client.user.get_full_name(),
                    "depart": demande.zone_depart.nom,
                    "arrivee": demande.zone_arrivee.nom,
                    "ws_path": f"/ws/livraisons/{demande.pk}/suivi/",
                } for demande in suivi_livraisons],
            },
        })
        return context


##########################################################################################################################################
#__________________________________________________________ASSISTANT_OPERATIONNEL____________________________________________________________
#############################################################################################################################################

class AssistantOperationnelDashboardView(AdminBlocPostDashboardView):
    template_name = "admins_templates/assistant_operationnel_dashboard.html"
    poste = "assistant"
    active_delivery_statuses = ("acceptee", "en_cours")

    def get_active_deliveries(self):
        bloc = self.admin_bloc.bloc
        return DemandeLivraison.objects.filter(
            statut__in=self.active_delivery_statuses,
        ).filter(
            Q(zone_depart__bloc=bloc)
            | Q(zone_arrivee__bloc=bloc)
            | Q(livreur__blocs=bloc)
        ).select_related(
            "client__user",
            "livreur__user",
            "zone_depart",
            "zone_arrivee",
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        livraisons = self.get_active_deliveries()
        context.update({
            "title": "Espace Assistant Opérationnel",
            "description": "Suivi des livraisons actives et résolution des alertes de votre bloc.",
            "livraisons_actives": livraisons.order_by("-date_creation"),
            "alertes_destinataire": livraisons.filter(
                statut_position_destinataire="alerte_assistant",
            ).order_by("-date_creation"),
        })
        return context

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return ["partials/admins/assistant_operationnel_livraisons.html"]
        return [self.template_name]

    def post(self, request, *args, **kwargs):
        demande = get_object_or_404(
            self.get_active_deliveries(),
            pk=request.POST.get("demande_id"),
        )
        action = request.POST.get("action")

        if action == "marquer_injoignable":
            if demande.statut_position_destinataire != "alerte_assistant":
                messages.error(
                    request,
                    "Seules les demandes en alerte peuvent être marquées injoignables.",
                )
                return redirect("admins_app:tableau-de-bord-assistant")
            demande.statut_position_destinataire = "injoignable"
            demande.save(update_fields=["statut_position_destinataire"])
            messages.success(
                request,
                f"Le destinataire de la demande #{demande.pk} est marqué injoignable.",
            )
            return redirect("admins_app:tableau-de-bord-assistant")

        if action == "enregistrer_position":
            try:
                latitude = Decimal(request.POST.get("latitude", "").strip())
                longitude = Decimal(request.POST.get("longitude", "").strip())
            except InvalidOperation:
                latitude = longitude = None

            if (
                latitude is None
                or longitude is None
                or not latitude.is_finite()
                or not longitude.is_finite()
                or not -90 <= latitude <= 90
                or not -180 <= longitude <= 180
                or latitude.as_tuple().exponent < -6
                or longitude.as_tuple().exponent < -6
            ):
                messages.error(
                    request,
                    "Coordonnées invalides. Saisissez une latitude entre -90 et 90 "
                    "et une longitude entre -180 et 180, avec au plus 6 décimales.",
                )
                return redirect("admins_app:tableau-de-bord-assistant")

            with transaction.atomic():
                # Reprendre le verrou sur la ligne pour ne notifier que la première validation.
                demande = get_object_or_404(
                    DemandeLivraison.objects.select_for_update(of=("self",))
                    .filter(
                        pk=demande.pk,
                        statut__in=self.active_delivery_statuses,
                    )
                    .filter(
                        Q(zone_depart__bloc=self.admin_bloc.bloc)
                        | Q(zone_arrivee__bloc=self.admin_bloc.bloc)
                        | Q(livreur__blocs=self.admin_bloc.bloc)
                    ),
                )
                premiere_validation = not demande.position_destinataire_validee
                demande.latitude_destinataire_reelle = latitude
                demande.longitude_destinataire_reelle = longitude
                demande.position_destinataire_validee = True
                demande.statut_position_destinataire = "position_recue"
                demande.save(update_fields=[
                    "latitude_destinataire_reelle",
                    "longitude_destinataire_reelle",
                    "position_destinataire_validee",
                    "statut_position_destinataire",
                ])

            if (
                premiere_validation
                and demande.livreur_id
                and not programmer_notification_position_destinataire(demande)
            ):
                messages.warning(
                    request,
                    f"La position de la demande #{demande.pk} est enregistrée, "
                    "mais la notification du client n'a pas pu être programmée.",
                )
            messages.success(
                request,
                f"La position du destinataire de la demande #{demande.pk} a été enregistrée.",
            )
            return redirect("admins_app:tableau-de-bord-assistant")

        messages.error(request, "Action de résolution inconnue.")
        return redirect("admins_app:tableau-de-bord-assistant")


class AssistantSupportInboxView(AdminBlocPostDashboardView):
    template_name = "admins_templates/assistant_support_inbox.html"
    poste = "assistant"

    def get_template_names(self):
        if (
            self.request.headers.get("HX-Request") == "true"
            and self.request.headers.get("HX-Target")
            == "assistant-support-conversations"
        ):
            return ["partials/admins/assistant_support_conversations.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "title": "Messages des clients",
            "conversations": SupportConversation.objects.filter(
                bloc=self.admin_bloc.bloc,
                bloc__actif=True,
            ).select_related(
                "client__user",
                "bloc",
            ).prefetch_related(
                Prefetch(
                    "messages",
                    queryset=SupportMessage.objects.order_by("-created_at")[:1],
                    to_attr="recent_messages",
                ),
            ).order_by("-updated_at"),
        })
        return context
