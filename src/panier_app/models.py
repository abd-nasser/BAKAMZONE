import uuid
from decimal import Decimal

from django.db import models


class Panier(models.Model):
    """Panier courant ou historique d'un client."""

    STATUT_ACTIF = "actif"
    STATUT_COMMANDE = "commande"
    STATUT_ABANDONNE = "abandonne"
    STATUT_CHOICES = [
        (STATUT_ACTIF, "Actif"),
        (STATUT_COMMANDE, "Commandé"),
        (STATUT_ABANDONNE, "Abandonné"),
    ]

    client = models.ForeignKey(
        "clients_app.Client",
        on_delete=models.PROTECT,
        related_name="paniers",
    )
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=STATUT_ACTIF,
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_modification"]
        verbose_name = "Panier"
        verbose_name_plural = "Paniers"
        constraints = [
            models.UniqueConstraint(
                fields=["client"],
                condition=models.Q(statut="actif"),
                name="unique_panier_actif_par_client",
            ),
        ]

    def total_panier(self):
        """Calcule le total courant en tenant compte des promotions applicables."""
        return sum(
            (
                ligne.article.prix_actuel * ligne.quantite
                for ligne in self.lignes.select_related("article")
            ),
            Decimal("0.00"),
        )

    def __str__(self):
        return f"Panier de {self.client} ({self.get_statut_display()})"


class ArticlePanier(models.Model):
    """Article et quantité souhaitée dans un panier avant le checkout."""

    panier = models.ForeignKey(
        Panier,
        on_delete=models.CASCADE,
        related_name="lignes",
    )
    article = models.ForeignKey(
        "articles_app.Article",
        on_delete=models.PROTECT,
        related_name="lignes_paniers",
    )
    quantite = models.PositiveIntegerField(default=1)
    date_ajout = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date_ajout"]
        verbose_name = "Article du panier"
        verbose_name_plural = "Articles du panier"
        constraints = [
            models.UniqueConstraint(
                fields=["panier", "article"],
                name="unique_article_par_panier",
            ),
            models.CheckConstraint(
                condition=models.Q(quantite__gte=1),
                name="quantite_article_panier_positive",
            ),
        ]

    @property
    def sous_total(self):
        """Retourne le sous-total indicatif au prix actuel de l'article."""
        return self.article.prix_actuel * self.quantite

    def __str__(self):
        return f"{self.quantite} × {self.article.nom}"


class Commande(models.Model):
    """Commande créée depuis un panier et destinée au paiement en ligne."""

    STATUT_EN_ATTENTE_PAIEMENT = "en_attente_paiement"
    STATUT_CONFIRMEE = "confirmee"
    STATUT_EN_PREPARATION = "en_preparation"
    STATUT_EN_LIVRAISON = "en_livraison"
    STATUT_LIVREE = "livree"
    STATUT_ANNULEE = "annulee"
    STATUT_CHOICES = [
        (STATUT_EN_ATTENTE_PAIEMENT, "En attente de paiement"),
        (STATUT_CONFIRMEE, "Confirmée"),
        (STATUT_EN_PREPARATION, "En préparation"),
        (STATUT_EN_LIVRAISON, "En livraison"),
        (STATUT_LIVREE, "Livrée"),
        (STATUT_ANNULEE, "Annulée"),
    ]

    PAIEMENT_NON_INITIE = "non_initie"
    PAIEMENT_EN_ATTENTE = "en_attente"
    PAIEMENT_REUSSI = "reussi"
    PAIEMENT_ECHOUE = "echoue"
    PAIEMENT_ANNULE = "annule"
    PAIEMENT_CHOICES = [
        (PAIEMENT_NON_INITIE, "Non initié"),
        (PAIEMENT_EN_ATTENTE, "En attente"),
        (PAIEMENT_REUSSI, "Réussi"),
        (PAIEMENT_ECHOUE, "Échoué"),
        (PAIEMENT_ANNULE, "Annulé"),
    ]

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    panier = models.OneToOneField(
        Panier,
        on_delete=models.PROTECT,
        related_name="commande",
    )
    client = models.ForeignKey(
        "clients_app.Client",
        on_delete=models.PROTECT,
        related_name="commandes",
    )
    bloc = models.ForeignKey(
        "blocs_app.Blocs",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="commandes",
    )
    zone_arrivee = models.ForeignKey(
        "zones_app.Zone",
        on_delete=models.PROTECT,
        related_name="commandes",
    )
    latitude_livraison = models.DecimalField(max_digits=9, decimal_places=6)
    longitude_livraison = models.DecimalField(max_digits=9, decimal_places=6)
    montant_produits = models.DecimalField(max_digits=12, decimal_places=2)
    frais_livraison = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    total_a_payer = models.DecimalField(max_digits=12, decimal_places=2)
    statut = models.CharField(
        max_length=30,
        choices=STATUT_CHOICES,
        default=STATUT_EN_ATTENTE_PAIEMENT,
    )
    statut_paiement = models.CharField(
        max_length=20,
        choices=PAIEMENT_CHOICES,
        default=PAIEMENT_NON_INITIE,
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_paiement = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date_creation"]
        verbose_name = "Commande"
        verbose_name_plural = "Commandes"
        indexes = [
            models.Index(fields=["client", "date_creation"]),
            models.Index(fields=["statut", "statut_paiement"]),
        ]

    def __str__(self):
        return f"Commande {self.reference} — {self.client}"


class LigneCommande(models.Model):
    """Instantané immuable des articles et prix au moment de la commande."""

    commande = models.ForeignKey(
        Commande,
        on_delete=models.CASCADE,
        related_name="lignes",
    )
    article = models.ForeignKey(
        "articles_app.Article",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lignes_commandes",
    )
    entreprise = models.ForeignKey(
        "entreprise_app.Entreprise",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lignes_commandes",
    )
    nom_article = models.CharField(max_length=200)
    nom_entreprise = models.CharField(max_length=150)
    quantite = models.PositiveIntegerField()
    prix_unitaire = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["id"]
        verbose_name = "Ligne de commande"
        verbose_name_plural = "Lignes de commande"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantite__gte=1),
                name="quantite_ligne_commande_positive",
            ),
        ]

    @property
    def sous_total(self):
        """Calcule le montant historique de la ligne à partir du prix figé."""
        return self.prix_unitaire * self.quantite

    def __str__(self):
        return f"{self.quantite} × {self.nom_article}"
