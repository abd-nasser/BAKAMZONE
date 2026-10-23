from uuid import uuid4

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.text import slugify

from .models import Entreprise, MembreAdminsEntreprise

User = get_user_model()


class InscriptionEntrepriseForm(forms.ModelForm):
    """Crée le compte du responsable et le profil de son entreprise."""

    first_name = forms.CharField(
        max_length=30,
        label="Prénom du responsable",
        widget=forms.TextInput(attrs={
            "class": "input input-bordered w-full rounded-xl",
            "autocomplete": "given-name",
        }),
    )
    last_name = forms.CharField(
        max_length=30,
        label="Nom du responsable",
        widget=forms.TextInput(attrs={
            "class": "input input-bordered w-full rounded-xl",
            "autocomplete": "family-name",
        }),
    )
    telephone = forms.CharField(
        max_length=20,
        label="Téléphone du responsable",
        widget=forms.TextInput(attrs={
            "class": "input input-bordered w-full rounded-xl",
            "autocomplete": "tel",
            "placeholder": "Ex. : 70000000",
        }),
    )
    email = forms.EmailField(
        required=False,
        label="Adresse e-mail (facultatif)",
        widget=forms.EmailInput(attrs={
            "class": "input input-bordered w-full rounded-xl",
            "autocomplete": "email",
        }),
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={
            "class": "input input-bordered w-full rounded-xl",
            "autocomplete": "new-password",
        }),
    )
    password_confirm = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(attrs={
            "class": "input input-bordered w-full rounded-xl",
            "autocomplete": "new-password",
        }),
    )

    class Meta:
        model = Entreprise
        fields = ("nom_entreprise", "logo", "rc_number", "address")
        widgets = {
            "nom_entreprise": forms.TextInput(attrs={
                "class": "input input-bordered w-full rounded-xl",
                "autocomplete": "organization",
            }),
            "logo": forms.ClearableFileInput(attrs={
                "class": "file-input file-input-bordered w-full",
                "accept": "image/*",
            }),
            "rc_number": forms.TextInput(attrs={
                "class": "input input-bordered w-full rounded-xl",
            }),
            "address": forms.Textarea(attrs={
                "class": "textarea textarea-bordered w-full rounded-xl",
                "rows": 3,
                "autocomplete": "street-address",
            }),
        }

    def clean_telephone(self):
        telephone = self.cleaned_data["telephone"].strip()
        if User.objects.filter(telephone=telephone).exists():
            raise forms.ValidationError("Ce numéro de téléphone est déjà utilisé.")
        return telephone

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error("password_confirm", "Les mots de passe ne correspondent pas.")
        if password:
            user = User(
                telephone=cleaned_data.get("telephone", ""),
                first_name=cleaned_data.get("first_name", ""),
                last_name=cleaned_data.get("last_name", ""),
                email=cleaned_data.get("email", ""),
            )
            try:
                validate_password(password, user=user)
            except ValidationError as error:
                self.add_error("password", error)
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        entreprise = super().save(commit=False)
        user = User(
            telephone=self.cleaned_data["telephone"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            email=self.cleaned_data.get("email") or "",
            role="entreprise",
        )
        user.set_password(self.cleaned_data["password"])
        entreprise.user_principal = user

        if commit:
            user.save()
            entreprise.save()
        return entreprise


class ChoixPalierEntrepriseForm(forms.ModelForm):
    """Modifie uniquement le palier, sans activer l'abonnement."""

    palier = forms.ChoiceField(
        label="Palier d'abonnement",
        choices=tuple(
            choice for choice in Entreprise.PALIER_CHOICES
            if choice[0] != "pas_defini"
        ),
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Entreprise
        fields = ("palier",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.palier == "pas_defini":
            self.initial["palier"] = None


class MembreAdminsEntrepriseForm(forms.Form):
    """Crée un compte administrateur et l'associe à l'entreprise du responsable."""

    first_name = forms.CharField(
        max_length=30,
        label="Prénom",
        widget=forms.TextInput(attrs={
            "class": "input input-bordered w-full rounded-xl",
            "autocomplete": "given-name",
        }),
    )
    last_name = forms.CharField(
        max_length=30,
        label="Nom",
        widget=forms.TextInput(attrs={
            "class": "input input-bordered w-full rounded-xl",
            "autocomplete": "family-name",
        }),
    )
    telephone = forms.CharField(
        max_length=20,
        label="Téléphone",
        widget=forms.TextInput(attrs={
            "class": "input input-bordered w-full rounded-xl",
            "autocomplete": "tel",
        }),
    )
    email = forms.EmailField(
        required=False,
        label="Adresse e-mail (facultatif)",
        widget=forms.EmailInput(attrs={
            "class": "input input-bordered w-full rounded-xl",
            "autocomplete": "email",
        }),
    )

    def __init__(self, *args, entreprise, **kwargs):
        super().__init__(*args, **kwargs)
        self.entreprise = entreprise
        self.generated_username = None
        self.generated_password = None

    def clean_telephone(self):
        telephone = self.cleaned_data["telephone"].strip()
        if User.objects.filter(telephone=telephone).exists():
            raise forms.ValidationError("Ce numéro de téléphone est déjà utilisé.")
        return telephone

    def _generate_username(self):
        base_username = slugify(
            f"{self.cleaned_data['first_name']}.{self.cleaned_data['last_name']}"
        ).replace("-", "_") or "admin"
        while True:
            username = f"{base_username[:21]}_{uuid4().hex[:8]}"
            if not User.objects.filter(username__iexact=username).exists():
                return username

    @transaction.atomic
    def save(self):
        self.generated_username = self._generate_username()
        self.generated_password = uuid4().hex
        membre_admin = User(
            username=self.generated_username,
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            telephone=self.cleaned_data["telephone"],
            email=self.cleaned_data.get("email") or "",
            role="entreprise_admin",
        )
        membre_admin.set_password(self.generated_password)
        membre_admin.save()

        return MembreAdminsEntreprise.objects.create(
            entreprise=self.entreprise,
            membre_admin=membre_admin,
            ajoute_par=self.entreprise.user_principal,
        )
