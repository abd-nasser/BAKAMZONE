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
# 1. FORMULAIRE CLIENT
# ==========================================

class InscriptionClientForm(forms.ModelForm):
    """Inscription du compte utilisateur et de son profil client."""
    username = forms.CharField(
        max_length=30,
        label="Nom d'utilisateur",
        widget=forms.TextInput(attrs={
            'placeholder': "Nom d'utilisateur",
            'class': 'input input-bordered w-full rounded-xl',
        }),
    )
    first_name = forms.CharField(
        max_length=30,
        label="Prénom",
        widget=forms.TextInput(attrs={
            'placeholder': 'Prénom',
            'class': 'input input-bordered w-full rounded-xl',
        }),
    )
    last_name = forms.CharField(
        max_length=30,
        label="Nom",
        widget=forms.TextInput(attrs={
            'placeholder': 'Nom',
            'class': 'input input-bordered w-full rounded-xl',
        }),
    )
    telephone = forms.CharField(
        max_length=20,
        label="Numéro de téléphone",
        widget=forms.TextInput(attrs={
            'placeholder': 'Numéro de téléphone (ex: 70000000)',
            'class': 'input input-bordered w-full rounded-xl',
        }),
    )
    email = forms.EmailField(
        required=False,
        label="Email",
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email (Optionnel)',
            'class': 'input input-bordered w-full rounded-xl',
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Mot de passe',
            ":type":"showPassword ? 'text' : 'password'",
            "class": 'input input-bordered w-full pr-10 rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
            "required": True,
            }),
        label="Mot de passe"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirmez le mot de passe',
            ":type":"showConfirmPassword ? 'text' : 'password'",
            "class": 'input input-bordered w-full pr-10 rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
            "required": True,
        }),
        label="Confirmation du mot de passe"
    )

    class Meta:  # Configure le modèle enregistré et les champs affichés par ModelForm.
        model = Client
        fields = ["photo_profil", "ville", "quartier"]
        widgets = {
            'photo_profil': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
            'ville': forms.TextInput(attrs={
                'placeholder': 'Ville (Optionnel)',
                'class': 'input input-bordered w-full rounded-xl',
            }),
            'quartier': forms.TextInput(attrs={
                'placeholder': 'Quartier (Optionnel)',
                'class': 'input input-bordered w-full rounded-xl',
            }),
        }

    def clean_confirm_password(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return confirm_password

    def clean_telephone(self):
        telephone = self.cleaned_data['telephone']
        if User.objects.filter(telephone=telephone).exists():
            raise forms.ValidationError("Ce numéro de téléphone est déjà utilisé.")
        return telephone

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà utilisé.")
        return username

    @transaction.atomic
    def save(self, commit=True):
        client = super().save(commit=False)
        user = User(
            username=self.cleaned_data['username'],
            telephone=self.cleaned_data['telephone'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            email=self.cleaned_data.get('email', ''),
            role='client',
        )
        user.set_password(self.cleaned_data['password'])
        client.user = user

        if commit:
            user.save()
            client.save()
        return client


# ==========================================
# 2. FORMULAIRE DE CONNEXION UNIVERSEL
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
