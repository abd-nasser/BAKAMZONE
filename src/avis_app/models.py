from django.db import models

# Create your models here.
from django.db import models
from auth_app.models import User
from commandes_app.models import Commande
from livreurs_app.models import Livreur


class AvisLivreur(models.Model):
    commande = models.OneToOneField('commandes_app.commande', on_delete=models.CASCADE, related_name='avis')  # un seul avis par commande
    client = models.ForeignKey("clients_app.client", on_delete=models.CASCADE, related_name='avis_donnes')
    livreur = models.ForeignKey("livreurs_app.livreur", on_delete=models.CASCADE, related_name='avis')
    note = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    commentaire = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.note}/5 — {self.livreur}"