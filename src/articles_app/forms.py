from django import forms
from django.db import transaction

from admins_app.models import AdminBloc
from entreprise_app.models import Entreprise, MembreAdminsEntreprise

from .models import Article, StockBloc


class DateTimeLocalInput(forms.DateTimeInput):
    input_type = "datetime-local"


class ArticleEntrepriseForm(forms.ModelForm):
    """Ajoute un article hors bloc pour l'entreprise de l'utilisateur."""

    class Meta:
        model = Article
        fields = (
            "nom",
            "description",
            "prix",
            "prix_promo",
            "image",
            "disponible",
            "date_expiration",
        )
        labels = {
            "nom": "Nom de l'article",
            "description": "Description",
            "prix": "Prix",
            "prix_promo": "Prix promotionnel (facultatif)",
            "image": "Image de l'article",
            "disponible": "Article disponible",
            "date_expiration": "Date d'expiration (facultative)",
        }
        widgets = {
            "nom": forms.TextInput(attrs={
                "class": "input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors",
                "placeholder": "Ex. : Riz local",
                "autocomplete": "off",
            }),
            "description": forms.Textarea(attrs={
                "class": "textarea textarea-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors",
                "placeholder": "Décrivez votre article",
                "rows": 4,
            }),
            "prix": forms.NumberInput(attrs={
                "class": "input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors",
                "placeholder": "Ex. : 2500",
                "min": "0",
                "step": "0.01",
            }),
            "prix_promo": forms.NumberInput(attrs={
                "class": "input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors",
                "placeholder": "Facultatif",
                "min": "0",
                "step": "0.01",
            }),
            "image": forms.ClearableFileInput(attrs={
                "class": "file-input file-input-bordered w-full rounded-xl",
                "accept": "image/*",
            }),
            "disponible": forms.CheckboxInput(attrs={
                "class": "checkbox checkbox-success rounded-lg",
            }),
            "date_expiration": DateTimeLocalInput(
                attrs={
                    "class": "input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors",
                },
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["date_expiration"].input_formats = [
            "%Y-%m-%dT%H:%M",
            *self.fields["date_expiration"].input_formats,
        ]

    def _get_entreprise(self):
        entreprise = None

        if self.user.role == "entreprise":
            entreprise = Entreprise.objects.filter(
                user_principal=self.user
            ).first()
        elif self.user.role == "entreprise_admin":
            membre_admin = MembreAdminsEntreprise.objects.select_related(
                "entreprise"
            ).filter(membre_admin=self.user).first()
            if membre_admin is not None:
                entreprise = membre_admin.entreprise

        if entreprise is None:
            raise forms.ValidationError(
                "Votre compte n'est associé à aucune entreprise autorisée."
            )

        return entreprise

    def save(self, commit=True):
        article = super().save(commit=False)
        article.entreprise = self._get_entreprise()
        if article._state.adding:
            article.en_bloc = False

        if commit:
            article.save()
            self.save_m2m()

        return article


class ArticleBlocAdminForm(forms.ModelForm):
    """Ajoute un article d'entreprise dans le bloc de l'administrateur."""

    class Meta:
        model = Article
        fields = (
            "entreprise",
            "nom",
            "description",
            "prix",
            "prix_promo",
            "image",
            "disponible",
            "date_expiration",
        )
        labels = {
            **ArticleEntrepriseForm.Meta.labels,
            "entreprise": "Entreprise propriétaire",
        }
        widgets = {
            **ArticleEntrepriseForm.Meta.widgets,
            "entreprise": forms.Select(attrs={
                "class": "select select-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors",
            }),
        }

    def __init__(self, *args, user, entreprise=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.entreprise = entreprise
        if entreprise is None:
            self.fields["entreprise"].queryset = Entreprise.objects.order_by(
                "nom_entreprise"
            )
        else:
            self.fields.pop("entreprise")
        self.fields["date_expiration"].input_formats = [
            "%Y-%m-%dT%H:%M",
            *self.fields["date_expiration"].input_formats,
        ]

    def clean(self):
        cleaned_data = super().clean()
        if self.user.role != "bloc_admin":
            raise forms.ValidationError(
                "Seuls les administrateurs de bloc peuvent utiliser ce formulaire."
            )

        self.admin_bloc = AdminBloc.objects.filter(
            user=self.user,
            poste="gestionnaire_stock",
            actif=True,
        ).select_related("bloc").first()
        if self.admin_bloc is None:
            raise forms.ValidationError(
                "Aucun poste de gestionnaire de stock actif n'est associé à cet administrateur."
            )

        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        article = super().save(commit=False)
        if self.entreprise is not None:
            article.entreprise = self.entreprise
        article.en_bloc = True

        if commit:
            article.save()
            self.save_m2m()
            StockBloc.objects.get_or_create(
                article=article,
                bloc=self.admin_bloc.bloc,
            )

        return article
