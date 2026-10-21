from django import forms

from blocs_app.models import Blocs
from zones_app.models import Zone


class ZoneForm(forms.ModelForm):
    """Formulaire de création d'une zone opérationnelle."""

    class Meta:
        model = Zone
        fields = [
            'nom',
            'code',
            'bloc',
            'latitude',
            'longitude',
        ]
        labels = {
            'nom': 'Nom de la zone',
            'code': 'Code identifiant (optionnel)',
            'bloc': 'Bloc associé',
            'latitude': 'Latitude GPS (optionnelle)',
            'longitude': 'Longitude GPS (optionnelle)',
        }
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
                'placeholder': 'Ex: Secteur Tampouy Nord',
                'required': True,
            }),
            'code': forms.TextInput(attrs={
                'class': 'input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
                'placeholder': 'Ex: Z-TAMPOUY-NORD',
            }),
            'bloc': forms.Select(attrs={
                'class': 'select select-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
                'placeholder': 'Ex: 12.4042',
                'step': 'any',
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
                'placeholder': 'Ex: -1.5543',
                'step': 'any',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bloc'].queryset = Blocs.objects.filter(actif=True)
        self.fields['bloc'].empty_label = 'Sélectionnez un bloc actif'

    def clean_nom(self):
        nom = self.cleaned_data['nom'].strip()
        if Zone.objects.filter(nom__iexact=nom).exists():
            raise forms.ValidationError("Une zone portant ce nom existe déjà.")
        return nom