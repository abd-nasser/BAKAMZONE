from django.db import models
from django.urls import reverse
from auth_app.models import User
from entreprise_app.models import Entreprise
from blocs_app.models import Blocs
from zones_app.models import Zone


class Livreur(models.Model):
    STATUT_VERIFICATION = [
        ('en_attente', 'En attente de vérification'),
        ('verifie', 'Vérifié'),
        ('rejete', 'Rejeté'),
    ]
    TYPE_VEHICULE = [
        ('moto', 'Moto'), 
        ('velo', 'Vélo'), 
        ('voiture', 'Voiture'), 
        ('pied', 'À pied'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='livreur_profil')

    type_vehicule = models.CharField(max_length=30, choices=TYPE_VEHICULE)
    actif = models.BooleanField(default=True)  # désactivation logique, jamais de suppression réelle si historique
    disponible = models.BooleanField(default=False)

    blocs = models.ForeignKey(Blocs, on_delete=models.SET_NULL, null=True, blank=True, related_name='livreurs_bloc')
    zone_actuelle = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, blank=True, related_name='livreurs_presents')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    note_moyenne = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    favoris_de = models.ManyToManyField('clients_app.client', related_name='livreurs_favoris', blank=True)
    nb_livraisons = models.PositiveIntegerField(default=0)

    # Vérification identité
    photo_cni_recto = models.ImageField(upload_to='livreurs/cni/%Y/%m/', null=True, blank=True)
    photo_cni_verso = models.ImageField(upload_to='livreurs/cni/%Y/%m/', null=True, blank=True)
    photo_selfie = models.ImageField(upload_to='livreurs/selfies/%Y/%m/', null=True, blank=True)
    photo_profil = models.ImageField(upload_to='livreurs/profils/%Y/%m/', null=True, blank=True)
    statut_verification = models.CharField(max_length=20, choices=STATUT_VERIFICATION, default='en_attente')
    date_verification = models.DateTimeField(null=True, blank=True)
    verifie_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='livreurs_verifies')
    commentaire_rejet = models.TextField(blank=True)

    date_creation = models.DateTimeField(auto_now_add=True)

    @property
    def peut_accepter_commandes(self):
        return self.actif and self.statut_verification == 'verifie' and self.disponible

    def __str__(self):
        return f"{self.user.get_full_name()} — {self.get_type_vehicule_display()}"

    def get_absolute_url(self):
        return reverse('livreurs_app:livreur-profil', kwargs={'pk': self.pk})
    
    @property
    def google_maps_url(self):
        """Raccourci pour le DG / Commercial afin d'ouvrir le lieu directement dans Google Maps"""
        if self.latitude and self.longitude:
            return f"https://www.google.com/maps?q={self.latitude},{self.longitude}"
        return None
    
    @property
    def moyen_de_transport(self):
        return self.get_type_vehicule_display()

    @property
    def nb_ajout_favoris(self):
        return self.favoris_de.count()
    
class PositionLivreur(models.Model):
    """Historique de position — à purger périodiquement (voir note plus bas)"""
    livreur = models.ForeignKey(Livreur, on_delete=models.CASCADE, related_name='historique_positions')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    horodatage = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-horodatage']
        indexes = [models.Index(fields=['livreur', '-horodatage'])]