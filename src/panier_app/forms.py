from django import forms

from zones_app.models import Zone


class ValidationCommandeForm(forms.Form):
    zone_arrivee = forms.ModelChoiceField(
        queryset=Zone.objects.filter(
            bloc__actif=True,
        ).select_related(
            "bloc",
        ).order_by(
            "bloc__nom",
            "nom",
        ),
        empty_label="Choisissez votre zone de livraison",
        label="Zone de livraison",
        widget=forms.Select(attrs={
            "class": "select select-bordered w-full rounded-xl",
        }),
    )
    latitude = forms.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=-90,
        max_value=90,
        required=False,
        widget=forms.HiddenInput(attrs={"x-model": "latitude"}),
    )
    longitude = forms.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=-180,
        max_value=180,
        required=False,
        widget=forms.HiddenInput(attrs={"x-model": "longitude"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        zone = cleaned_data.get("zone_arrivee")
        latitude = cleaned_data.get("latitude")
        longitude = cleaned_data.get("longitude")

        if latitude is None or longitude is None:
            if (
                zone is None
                or zone.latitude is None
                or zone.longitude is None
            ):
                self.add_error(
                    "zone_arrivee",
                    "La zone sélectionnée n'a pas de coordonnées GPS. "
                    "Capturez votre position ou choisissez une autre zone.",
                )
            elif zone is not None:
                cleaned_data["latitude"] = zone.latitude
                cleaned_data["longitude"] = zone.longitude

        return cleaned_data
