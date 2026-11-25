
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
    



class PaiementLivraisonLigdiCash(models.Model):
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
    
    
    reference = models.UUIDField(
        default=uuid.uuid4, 
        unique=True, 
        editable=False,
        verbose_name="Référence du paiement livraison",
        )
    
    demande_livraison = models.OneToOneField(
        "demande_livraison_app.DemandeLivraison", 
        on_delete=models.PROTECT, 
        related_name="paiement_livraison_ligdicash"
        )
    
    montant = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name="Montant du paiement livraison"
        )
    
    numero_client = models.CharField(
        max_length=20,
        verbose_name="Numéro Mobile money",
        )
    operateur = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Opérateur Mobile money",
        )
    
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=STATUT_EN_ATTENTE,
        verbose_name="Statut du paiement livraison",
        )
    token_creation = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Token de création du paiement livraison",
        )
    token_callback = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Token de callback du paiement livraison",
        )
    
    reponse_API = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Réponse de l'API",
    )
    
    message_erreur = models.TextField(
        blank=True,
        null=True,
        verbose_name="Message d'erreur",
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_mise_a_jour = models.DateTimeField(auto_now=True, verbose_name="Date de mise à jour")
    date_paiement = models.DateTimeField(blank=True, null=True, verbose_name="Date de paiement")
    
    class Meta:
        ordering = ["-date_creation"]
        verbose_name = "Paiement livraison LigdiCash"
        verbose_name_plural = "Paiements livraison LigdiCash"
        indexes = [
            models.Index(fields=["token_creation"]),
            models.Index(fields=["statut"]),
        ]
        
        
    def __str__(self):
        return f"Paiement livraison {self.reference} — Demande {self.demande_livraison.reference} ({self.get_statut_display()})"