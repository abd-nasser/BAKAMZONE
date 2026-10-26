from django.db import models


class AvisLivreur(models.Model):
    demande_livraison = models.OneToOneField(
        'demande_livraison_app.DemandeLivraison',
        on_delete=models.CASCADE,
        related_name='avis',
        db_column='commande_id',
    )
    client = models.ForeignKey("clients_app.client", on_delete=models.CASCADE, related_name='avis_donnes')
    livreur = models.ForeignKey("livreurs_app.livreur", on_delete=models.CASCADE, related_name='avis')
    note = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    commentaire = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.note}/5 — {self.livreur}"