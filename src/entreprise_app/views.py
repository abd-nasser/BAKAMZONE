from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import (
    ChoixPalierEntrepriseForm,
    InscriptionEntrepriseForm,
    MembreAdminsEntrepriseForm,
)
from .models import Entreprise, MembreAdminsEntreprise

User = get_user_model()


class EntrepriseDashboardContextMixin:
    def get_dashboard_context(self, entreprise, context=None):
        context = context or {}
        admin_form = context.get("form")
        if admin_form is None:
            admin_form = MembreAdminsEntrepriseForm(entreprise=entreprise)
        available_article_count = entreprise.articles.filter(
            disponible=True
        ).count()
        context.update({
            "entreprise": entreprise,
            "admin_members": entreprise.membres_admin.select_related(
                "membre_admin",
                "ajoute_par",
            ).order_by("-date_ajout"),
            "article_count": entreprise.articles.count(),
            "available_article_count": available_article_count,
            "admin_count": entreprise.nb_admins_actuels,
            "admin_form": admin_form,
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
        return redirect("entreprise_app:detail")

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