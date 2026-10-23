import json

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.views.generic import CreateView, ListView, TemplateView

from admins_app.forms import AdminBlocForms
from admins_app.models import AdminBloc
from entreprise_app.models import Entreprise


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


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
