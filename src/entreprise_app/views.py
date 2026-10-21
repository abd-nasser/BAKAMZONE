from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from .forms import ChoixPalierEntrepriseForm, InscriptionEntrepriseForm
from .models import Entreprise


class InscriptionEntrepriseView(CreateView):
    form_class = InscriptionEntrepriseForm
    template_name = "auth_templates/entreprise_register.html"
    success_url = reverse_lazy("home_app:home")

    def form_valid(self, form):
        messages.success(
            self.request,
            "Le compte de votre entreprise est créé. Connectez-vous pour choisir "
            "votre palier d'abonnement.",
        )
        return super().form_valid(form)


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
