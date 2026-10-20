from django import forms
from blocs_app.models import Blocs


class BlocForm(forms.ModelForm):
    """
    Formulaire de création et de modification d'un Bloc BAKAMZONE par le Superuser.
    Stylé nativement avec Tailwind CSS & DaisyUI.
    """

    class Meta:
        model = Blocs
        fields = [
            'nom',
            'code',
            'ville',
            'quartier',
            'adresse',
            'telephone',
            'latitude',
            'longitude',
            'rayon_couverture_km',
            'capacite_stockage',
            'capacite_motos',
            'actif',
        ]
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
                'placeholder': 'Ex: Bloc Tampouy Centre',
                'required': True,
            }),
            'code': forms.TextInput(attrs={
                'class': 'input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
                'placeholder': 'Optionnel (ex: BLK-TAMPOUY)',
            }),
            'ville': forms.Select(attrs={
                'class': 'select select-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
            }),
            'quartier': forms.Select(attrs={
                'class': 'select select-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
            }),
            'adresse': forms.TextInput(attrs={
                'class': 'input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
                'placeholder': 'Ex: Face pharmacie Tampouy, rue 22.15',
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
                'placeholder': 'Ex: +226 70 00 00 00',
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
            'rayon_couverture_km': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
                'placeholder': 'Rayon en km (ex: 5.0)',
                'step': '0.1',
                'min': '0.5',
            }),
            'capacite_stockage': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
                'placeholder': 'Ex: 100',
                'min': '0',
            }),
            'capacite_motos': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full rounded-xl focus:border-[#059669] focus:outline-none transition-colors',
                'placeholder': 'Ex: 10',
                'min': '0',
            }),
            'actif': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-success rounded-lg',
            }),
        }
        labels = {
            'nom': 'Nom du Bloc',
            'code': 'Code identifiant (auto si vide)',
            'ville': 'Ville',
            'quartier': 'Quartier d’implantation',
            'adresse': 'Adresse / Repère géographique',
            'telephone': 'Téléphone du Bloc',
            'latitude': 'Latitude GPS',
            'longitude': 'Longitude GPS',
            'rayon_couverture_km': 'Rayon de couverture (km)',
            'capacite_stockage': 'Capacité max stockage (articles)',
            'capacite_motos': 'Capacité flotte motos',
            'actif': 'Bloc actif et opérationnel',
        }

    def clean_nom(self):
        nom = self.cleaned_data.get('nom', '').strip()
        if not nom:
            raise forms.ValidationError("Le nom du bloc est obligatoire.")
        qs = Blocs.objects.filter(nom__iexact=nom)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Un bloc portant ce nom existe déjà.")
        return nom
