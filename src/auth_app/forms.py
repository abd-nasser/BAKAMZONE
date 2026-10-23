from uuid import uuid4

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.text import slugify
from clients_app.models import Client
from livreurs_app.models import Livreur

User = get_user_model()


# ==========================================
# 1. FORMULAIRE DE CONNEXION UNIVERSEL
# ==========================================

class ConnexionForm(forms.Form):
    """
    Formulaire de connexion pour tous les rôles (Superuser, Admin de Bloc, Livreur, Entreprise, Client).
    Permet la connexion par Numéro de téléphone OU par Nom d'utilisateur.
    """
    identifiant = forms.CharField(
        label="Téléphone ou Nom d'utilisateur",
        widget=forms.TextInput(attrs={
            'placeholder': "Numéro (ex: 70000000) ou username",
            'class': 'input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
            'required': True,
            'autocomplete': 'username',
        }),
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={
            'placeholder': "Votre mot de passe",
            ':type': "showPassword ? 'text' : 'password'",
            'class': 'input input-bordered w-full pr-10 rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
            'required': True,
            'autocomplete': 'current-password',
        }),
    )


class ChangeCredentialForm(forms.Form):
    """Permet à un utilisateur connecté de modifier ses identifiants."""

    username = forms.CharField(
        max_length=30,
        required=False,
        label="Nom d'utilisateur",
        widget=forms.TextInput(attrs={
            "class": "input input-bordered w-full rounded-xl",
            "autocomplete": "username",
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
    old_password = forms.CharField(
        label="Mot de passe actuel",
        widget=forms.PasswordInput(attrs={
            "class": "input input-bordered w-full rounded-xl",
            "autocomplete": "current-password",
        }),
    )
    new_password = forms.CharField(
        required=False,
        label="Nouveau mot de passe",
        widget=forms.PasswordInput(attrs={
            "class": "input input-bordered w-full rounded-xl",
            "autocomplete": "new-password",
        }),
    )
    new_password_confirm = forms.CharField(
        required=False,
        label="Confirmer le nouveau mot de passe",
        widget=forms.PasswordInput(attrs={
            "class": "input input-bordered w-full rounded-xl",
            "autocomplete": "new-password",
        }),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["username"].initial = user.username or ""
        self.fields["telephone"].initial = user.telephone

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if username and User.objects.filter(
            username__iexact=username
        ).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà utilisé.")
        return username

    def clean_telephone(self):
        telephone = self.cleaned_data["telephone"].strip()
        if User.objects.filter(telephone=telephone).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("Ce numéro de téléphone est déjà utilisé.")
        return telephone

    def clean(self):
        cleaned_data = super().clean()
        old_password = cleaned_data.get("old_password")
        new_password = cleaned_data.get("new_password")
        new_password_confirm = cleaned_data.get("new_password_confirm")

        if old_password and not self.user.check_password(old_password):
            self.add_error("old_password", "Le mot de passe actuel est incorrect.")

        if new_password or new_password_confirm:
            if new_password != new_password_confirm:
                self.add_error(
                    "new_password_confirm",
                    "Les nouveaux mots de passe ne correspondent pas.",
                )
            if new_password:
                try:
                    validate_password(new_password, user=self.user)
                except DjangoValidationError as error:
                    self.add_error("new_password", error)

        username_changed = (
            cleaned_data.get("username", "") != (self.user.username or "")
        )
        telephone_changed = (
            cleaned_data.get("telephone") != self.user.telephone
        )
        if (
            not username_changed
            and not telephone_changed
            and not new_password
        ):
            raise forms.ValidationError(
                "Modifiez au moins un identifiant ou le mot de passe."
            )

        return cleaned_data

    @transaction.atomic
    def save(self):
        if not self.is_valid():
            raise ValueError("Le formulaire doit être valide avant l'enregistrement.")

        username = self.cleaned_data["username"]
        if username:
            self.user.username = username
        self.user.telephone = self.cleaned_data["telephone"]
        if self.cleaned_data["new_password"]:
            self.user.set_password(self.cleaned_data["new_password"])
        self.user.save()
        return self.user
