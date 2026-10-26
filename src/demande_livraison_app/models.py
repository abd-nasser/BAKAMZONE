from django.db import models
from livreurs_app.models import Livreur
from zones_app.models import Zone


class DemandeLivraison(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente de livreur'),
        ('acceptee', 'Acceptée'),
        ('en_cours', 'En cours de livraison'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    ]

    client = models.ForeignKey(
        'clients_app.client',
        on_delete=models.PROTECT,
        related_name='demandes_livraison',
    )
    livreur = models.ForeignKey(
        Livreur,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='demandes_livraison',
    )

    zone_depart = models.ForeignKey(
        Zone,
        on_delete=models.PROTECT,
        related_name='demandes_livraison_depart',
    )
    zone_arrivee = models.ForeignKey(
        Zone,
        on_delete=models.PROTECT,
        related_name='demandes_livraison_arrivee',
    )
    latitude_depart = models.DecimalField(max_digits=9, decimal_places=6)
    longitude_depart = models.DecimalField(max_digits=9, decimal_places=6)
    latitude_arrivee = models.DecimalField(max_digits=9, decimal_places=6)
    longitude_arrivee = models.DecimalField(max_digits=9, decimal_places=6)

    description_colis = models.TextField(blank=True)
    prix = models.DecimalField(max_digits=10, decimal_places=0)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')

    date_creation = models.DateTimeField(auto_now_add=True)
    date_livraison = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date_creation']
        indexes = [models.Index(fields=['statut', 'date_creation'], name='commandes_a_statut_f79ac0_idx')]

    def __str__(self):
        return f"Demande de livraison #{self.pk} — {self.client} → {self.zone_arrivee}"
