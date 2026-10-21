from uuid import uuid4

from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.text import slugify

from admins_app.models import AdminBloc

User = get_user_model()


class AdminBlocForms(forms.ModelForm):
    """Crée le compte utilisateur et son profil d'administrateur de bloc."""

    first_name = forms.CharField(
        max_length=30,
        label="Prénom",
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
            'placeholder': 'Prénom',
            'autocomplete': 'given-name',
        }),
    )
    last_name = forms.CharField(
        max_length=30,
        label="Nom",
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
            'placeholder': 'Nom',
            'autocomplete': 'family-name',
        }),
    )
    telephone = forms.CharField(
        max_length=20,
        label="Numéro de téléphone",
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
            'placeholder': 'Numéro de téléphone',
            'autocomplete': 'tel',
        }),
    )
    email = forms.EmailField(
        required=False,
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
            'placeholder': 'Email (optionnel)',
            'autocomplete': 'email',
        }),
    )
    class Meta:
        model = AdminBloc
        fields = [
            'bloc',
            'poste',
            'telephone_secondaire',
            'actif',
        ]
        widgets = {
            'bloc': forms.Select(attrs={
                'class': 'select select-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
            }),
            'poste': forms.Select(attrs={
                'class': 'select select-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
            }),
            'telephone_secondaire': forms.TextInput(attrs={
                'class': 'input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
                'placeholder': 'Téléphone secondaire / d’urgence (optionnel)',
            }),
            'actif': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-success rounded-lg',
            }),
        }

    def clean_telephone(self):
        telephone = self.cleaned_data['telephone'].strip()
        if User.objects.filter(telephone=telephone).exists():
            raise forms.ValidationError("Ce numéro de téléphone est déjà utilisé.")
        return telephone

    def _generate_username(self):
        base_username = slugify(
            f"{self.cleaned_data['first_name']}.{self.cleaned_data['last_name']}"
        ).replace('-', '_') or 'admin'
        while True:
            username = f"{base_username[:21]}_{uuid4().hex[:8]}"
            if not User.objects.filter(username__iexact=username).exists():
                return username

    def save(self, commit=True):
        profile = super().save(commit=False)
        if not hasattr(self, 'generated_password'):
            self.generated_username = self._generate_username()
            self.generated_password = uuid4().hex

        user = User(
            username=self.generated_username,
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            telephone=self.cleaned_data['telephone'],
            email=self.cleaned_data.get('email') or '',
            role='administrateur',
        )
        print(f"Generated username: {self.generated_username}, password: {self.generated_password}")
        user.set_password(self.generated_password)
        profile.user = user

        if commit:
            with transaction.atomic():
                user.save()
                profile.save()
                self.save_m2m()

        return profile
