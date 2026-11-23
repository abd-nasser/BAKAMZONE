
import uuid
from decimal import Decimal
from django.db import models


class PaiementLigdiCash(models.Model):
    # Statuts de transaction LigdiCash
    STATUT_EN_ATTENTE = "en_attente"
    STATUT_REUSSI = "reussi"
    STATUT_ECHOUE = "echoue"
    STATUT_ANNULE = "annule"

    STATUT_CHOICES = [
        (STATUT_EN_ATTENTE, "En attente"),
        (STATUT_REUSSI, "Réussi"),
        (STATUT_ECHOUE, "Échoué"),
        (STATUT_ANNULE, "Annulé"),
    ]

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Lien direct avec la commande BAKAMZONE
    commande = models.OneToOneField(
        "panier_app.Commande",
        on_delete=models.PROTECT,
        related_name="paiement_ligdicash",
    )
    
    # Informations de la transaction
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    numero_client = models.CharField(max_length=20) # ex: 22670XXXXXXX
    operateur = models.CharField(max_length=50) # ex: ORANGE, MOOV, etc.
    
    # Tokens LigdiCash (Attention : stocker le token de création pour l'endpoint confirm)
    token_creation = models.CharField(max_length=255, unique=True, blank=True, null=True)
    token_callback = models.CharField(max_length=255, blank=True, null=True)
    
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=STATUT_EN_ATTENTE,
    )
    
    # Réponses brutes ou messages d'erreur utiles pour le debugging
    reponse_API = models.JSONField(default=dict, blank=True)
    message_erreur = models.TextField(blank=True, null=True)
    
    date_creation = models.DateTimeField(auto_now_add=True)
    date_mise_a_jour = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_creation"]
        verbose_name = "Paiement LigdiCash"
        verbose_name_plural = "Paiements LigdiCash"
        indexes = [
            models.Index(fields=["token_creation"]),
            models.Index(fields=["statut"]),
        ]

    def __str__(self):
        return f"Paiement {self.reference} — Commande {self.commande.reference} ({self.get_statut_display()})"