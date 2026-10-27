from django import forms
from demande_livraison_app.models import DemandeLivraison
from demande_livraison_app.pricing import calculer_tarif_livraison
from zones_app.models import Zone


class DemandeLivraisonForm(forms.ModelForm):
    zone_depart = forms.ModelChoiceField(
        queryset=Zone.objects.select_related('bloc').all().order_by('bloc__nom', 'nom'),
        empty_label="Sélectionnez la zone de départ",
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full rounded-xl focus:border-emerald-500 focus:outline-none',
            'id': 'id_zone_depart',
        }),
        label="Zone de départ",
    )
    zone_arrivee = forms.ModelChoiceField(
        queryset=Zone.objects.select_related('bloc').all().order_by('bloc__nom', 'nom'),
        empty_label="Sélectionnez la zone d'arrivée",
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full rounded-xl focus:border-emerald-500 focus:outline-none',
            'id': 'id_zone_arrivee',
        }),
        label="Zone d'arrivée (destinataire)",
    )
    latitude_depart = forms.DecimalField(
        max_digits=9,
        decimal_places=6,
        widget=forms.HiddenInput(attrs={'id': 'id_latitude_depart'}),
        required=False,
    )
    longitude_depart = forms.DecimalField(
        max_digits=9,
        decimal_places=6,
        widget=forms.HiddenInput(attrs={'id': 'id_longitude_depart'}),
        required=False,
    )
    whatsapp_destinataire = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'placeholder': '+226 70 00 00 00',
            'class': 'input input-bordered w-full rounded-xl focus:border-emerald-500 focus:outline-none font-medium',
            'id': 'id_whatsapp_destinataire',
        }),
        label="Numéro WhatsApp du destinataire",
        help_text="Un lien de localisation instantanée PWA sera envoyé à ce numéro dès la prise en charge.",
    )
    description_colis = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Description ou instructions particulières (ex: Enveloppe urgente, paquet fragile, repas...)',
            'class': 'textarea textarea-bordered w-full rounded-xl focus:border-emerald-500 focus:outline-none text-sm',
            'id': 'id_description_colis',
        }),
        label="Description du colis (facultatif)",
    )

    class Meta:
        model = DemandeLivraison
        fields = [
            'zone_depart',
            'zone_arrivee',
            'latitude_depart',
            'longitude_depart',
            'whatsapp_destinataire',
            'description_colis',
        ]

    def clean(self):
        cleaned_data = super().clean()
        zone_depart = cleaned_data.get('zone_depart')
        zone_arrivee = cleaned_data.get('zone_arrivee')
        lat = cleaned_data.get('latitude_depart')
        lng = cleaned_data.get('longitude_depart')

        # Si les coordonnées GPS ne sont pas transmises, repli sur la position de la zone de départ
        if lat is None or lng is None:
            if zone_depart and zone_depart.latitude is not None and zone_depart.longitude is not None:
                cleaned_data['latitude_depart'] = zone_depart.latitude
                cleaned_data['longitude_depart'] = zone_depart.longitude
            else:
                self.add_error(
                    'latitude_depart',
                    "Veuillez capturer votre position GPS actuelle via le bouton de géolocalisation.",
                )

        # Validation et normalisation du numéro WhatsApp
        whatsapp = (cleaned_data.get('whatsapp_destinataire') or '').strip()
        if not whatsapp:
            self.add_error('whatsapp_destinataire', "Le numéro WhatsApp du destinataire est requis.")
        else:
            cleaned_whatsapp = ''.join(c for c in whatsapp if c.isdigit() or c == '+')
            digits_count = len([c for c in cleaned_whatsapp if c.isdigit()])
            if digits_count < 8:
                self.add_error(
                    'whatsapp_destinataire',
                    "Numéro de téléphone invalide (au moins 8 chiffres requis).",
                )
            cleaned_data['whatsapp_destinataire'] = cleaned_whatsapp

        # Calcul automatique du tarif
        if zone_depart and zone_arrivee:
            cleaned_data['prix'] = calculer_tarif_livraison(zone_depart, zone_arrivee)

        return cleaned_data

    def save(self, client, commit=True):
        instance = super().save(commit=False)
        instance.client = client
        instance.prix = self.cleaned_data['prix']

        # Si la zone d'arrivée a des coordonnées estimées, on initialise latitude_arrivee
        zone_arrivee = self.cleaned_data.get('zone_arrivee')
        if zone_arrivee:
            if instance.latitude_arrivee is None and zone_arrivee.latitude:
                instance.latitude_arrivee = zone_arrivee.latitude
            if instance.longitude_arrivee is None and zone_arrivee.longitude:
                instance.longitude_arrivee = zone_arrivee.longitude

        if commit:
            instance.save()
        return instance
