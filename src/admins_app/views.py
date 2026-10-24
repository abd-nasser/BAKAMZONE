import json

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.views.generic import CreateView, DetailView, ListView, TemplateView

from admins_app.forms import AdminBlocForms
from admins_app.models import AdminBloc
from articles_app.forms import ArticleBlocAdminForm
from entreprise_app.models import Entreprise
from articles_app.models import StockBloc

from livreurs_app.models import Livreur
from commandes_app.models import Commande


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
class SuperviseurFlotteDashbordView(LoginRequiredMixin, ListView):
    model = Livreur
    context_object_name = "livreurs"
    template_name = "admins_templates/superviseur_livreurs.html"
    title = "Espace Superviseur de Flotte"
    description = "Suivi opérationnel de la flotte de livreurs de votre bloc."

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
                "Ce tableau de bord est réservé aux superviseurs de flotte actifs."
            )
        return super().dispatch(request, *args, **kwargs)

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
            "admin_bloc": self.admin_bloc,
            "bloc": self.admin_bloc.bloc,
            "title": self.title,
            "description": self.description,
            "search_query": self.request.GET.get("q", ""),
        })
        return context

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return ["partials/admins/superviseur_flotte_livreurs.html"]
        return [self.template_name]