from uuid import uuid4

from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction

from blocs_app.models import Blocs
from livreurs_app.models import Livreur
from zones_app.models import Zone

User = get_user_model()


class InscriptionLivreurForm(forms.ModelForm):
    """Crée le compte utilisateur et son profil de livreur."""

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
        model = Livreur
        fields = [
            'type_vehicule',
            'blocs',
            'zone_actuelle',
            'photo_cni_recto',
            'photo_cni_verso',
            'photo_selfie',
            'photo_profil',
        ]
        labels = {
            'type_vehicule': 'Type de véhicule',
            'blocs': 'Bloc de rattachement',
            'zone_actuelle': 'Zone actuelle',
            'photo_cni_recto': 'Photo du recto de la pièce d’identité',
            'photo_cni_verso': 'Photo du verso de la pièce d’identité',
            'photo_selfie': 'Selfie de vérification',
            'photo_profil': 'Photo de profil',
        }
        widgets = {
            'type_vehicule': forms.Select(attrs={
                'class': 'select select-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
            }),
            'blocs': forms.Select(attrs={
                'class': 'select select-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
            }),
            'zone_actuelle': forms.Select(attrs={
                'class': 'select select-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
            }),
            'photo_cni_recto': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
            'photo_cni_verso': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
            'photo_selfie': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
            'photo_profil': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        blocs_actifs = Blocs.objects.filter(actif=True)
        self.fields['blocs'].queryset = blocs_actifs
        self.fields['blocs'].required = True
        self.fields['zone_actuelle'].queryset = Zone.objects.filter(
            bloc__actif=True,
        ).select_related('bloc')
        self.fields['zone_actuelle'].required = False

    def clean(self):
        cleaned_data = super().clean()
        bloc = cleaned_data.get('blocs')
        zone = cleaned_data.get('zone_actuelle')
        if bloc and zone and zone.bloc_id != bloc.pk:
            self.add_error(
                'zone_actuelle',
                forms.ValidationError(
                    "La zone actuelle doit appartenir au bloc sélectionné."
                ),
            )
        return cleaned_data

    def clean_telephone(self):
        telephone = self.cleaned_data['telephone'].strip()
        if User.objects.filter(telephone=telephone).exists():
            raise forms.ValidationError("Ce numéro de téléphone est déjà utilisé.")
        return telephone

    def _generate_username(self):
        while True:
            username = uuid4().hex[:30]
            if not User.objects.filter(username__iexact=username).exists():
                return username

    def save(self, commit=True):
        livreur = super().save(commit=False)
        if not hasattr(self, 'generated_password'):
            self.generated_username = self._generate_username()
            self.generated_password = uuid4().hex

        user = User(
            username=self.generated_username,
            telephone=self.cleaned_data['telephone'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            email=self.cleaned_data.get('email') or '',
            role='livreur',
        )
        user.set_password(self.generated_password)
        livreur.user = user

        if commit:
            with transaction.atomic():
                user.save()
                livreur.save()
                self.save_m2m()

        return livreur