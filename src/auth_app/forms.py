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
