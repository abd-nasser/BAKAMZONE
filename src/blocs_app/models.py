from django.db import models
from django.utils.text import slugify


class Blocs(models.Model):
    """
    Représente un Bloc de quartier (hub logistique de proximité BAKAMZONE).
    Chaque bloc dispose de son équipe d'admins, de sa flotte de livreurs et de son stock local.
    """

    VILLE_CHOICES = [
        ('ouagadougou', 'Ouagadougou'),
        ('bobo_dioulasso', 'Bobo-Dioulasso'),
        ('koudougou', 'Koudougou'),
        ('ouahigouya', 'Ouahigouya'),
        ('fada_ngourma', 'Fada N’Gourma'),
        ('banfora', 'Banfora'),
        ('koupela', 'Koupéla'),
        ('kaya', 'Kaya'),
    ]
    VILLE_CHOISE = VILLE_CHOICES  # Alias pour compatibilité

    QUARTIER_CHOICES = [
        ('tampouy', 'Tampouy'),
        ('ouaga_2000', 'Ouaga 2000'),
        ('kalgondin', 'Kalgondin'),
        ('patte_d_oie', 'Patte d’Oie'),
        ('dassasgho', 'Dassasgho'),
        ('wayalghin', 'Wayalghin'),
        ('pissy', 'Pissy'),
        ('gounghin', 'Gounghin'),
        ('karpala', 'Karpala'),
        ('rayongo', 'Rayongo'),
        ('somgande', 'Somgandé'),
        ('tanghin', 'Tanghin'),
        ('saaba', 'Saaba'),
        ('cissin', 'Cissin'),
        ('samandin', 'Samandin'),
        ('larlle', 'Larlé'),
        ('zone_du_bois', 'Zone du Bois'),
        ('kamboinsin', 'Kamboinsin'),
        ('baskuy', 'Baskuy'),
        ('bogodogo', 'Bogodogo'),
        ('boulmiougou', 'Boulmiougou'),
        ('nongremassom', 'Nongr-Massom'),
        ('sig_noghin', 'Sig-Noghin'),
        ('autre', 'Autre quartier'),
    ]
    QUARTIER_CHOICE = QUARTIER_CHOICES  # Alias pour compatibilité

    nom = models.CharField(max_length=150, unique=True, verbose_name="Nom du bloc")
    code = models.CharField(max_length=30, unique=True, blank=True, null=True, verbose_name="Code unique")

    ville = models.CharField(
        max_length=50,
        choices=VILLE_CHOICES,
        default='ouagadougou',
        verbose_name="Ville"
    )
    quartier = models.CharField(
        max_length=50,
        choices=QUARTIER_CHOICES,
        default='tampouy',
        verbose_name="Quartier"
    )

    adresse = models.CharField(max_length=255, blank=True, verbose_name="Adresse / Repère")
    telephone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Téléphone de contact")

    # Coordonnées géographiques pour l'attribution intelligente et la proximité
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Latitude")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Longitude")
    rayon_couverture_km = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=5.00,
        verbose_name="Rayon de couverture (km)"
    )

    # Capacités opérationnelles du bloc
    capacite_stockage = models.PositiveIntegerField(default=100, verbose_name="Capacité de stockage (articles)")
    capacite_motos = models.PositiveIntegerField(default=10, verbose_name="Capacité de motos électriques")

    actif = models.BooleanField(default=True, verbose_name="Bloc actif")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")

    class Meta:
        verbose_name = "Bloc"
        verbose_name_plural = "Blocs"
        ordering = ['nom']

    def __str__(self):
        return f"{self.nom} — {self.get_quartier_display()} ({self.get_ville_display()})"

    @property
    def name(self):
        """Alias pour rétro-compatibilité avec d'éventuels appels self.bloc.name"""
        return self.nom

    @property
    def google_maps_url(self):
        """Lien direct Google Maps vers l'emplacement physique du bloc"""
        if self.latitude and self.longitude:
            return f"https://www.google.com/maps?q={self.latitude},{self.longitude}"
        return None

    def save(self, *args, **kwargs):
        # Génération automatique d'un code si non renseigné (ex: BLK-TAMPOUY)
        if not self.code and self.nom:
            base_code = slugify(self.nom).upper()[:15]
            self.code = f"BLK-{base_code}"
        super().save(*args, **kwargs)
