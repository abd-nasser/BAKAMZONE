from django.db import models
from django.utils import timezone
from entreprise_app.models import Entreprise  # Adapte selon le nom de ton app d'entreprise
from blocs_app.models import Blocs         # Adapte selon le nom de ton app de bloc/accounts

class Article(models.Model):
    """
    Représente un article proposé par une entreprise partenaire,
    stocké et géré par bloc de quartier.
    """
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='articles')
    
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    prix = models.DecimalField(max_digits=10, decimal_places=2) 
    prix_promo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    en_bloc = models.BooleanField(default=True)  # Indique si l'article est disponible dans le bloc
    # Image principale de l'article
    image = models.ImageField(upload_to='articles/images/', null=True, blank=True)
    
    # Disponibilité globale de l'article
    disponible = models.BooleanField(default=True)
    date_expiration = models.DateTimeField(null=True, blank=True)  # Date d'expiration de l'article, si applicable
    
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    
    
    @property
    def est_expire(self):
        """
        Vérifie si l'article est expiré en fonction de la date d'expiration.
        """
        if self.date_expiration:
            return self.date_expiration < timezone.now()
        return False
    
    @property
    def est_en_promotion(self):
        """
        Vérifie si l'article est actuellement en promotion.
        """
        return self.prix_promo is not None and self.prix_promo < self.prix

    @property
    def prix_actuel(self):
        """
        Retourne le prix actuel de l'article, en tenant compte de la promotion si elle est définie.
        """
        if self.prix_promo is not None and self.prix_promo < self.prix:
            return self.prix_promo
        return self.prix
    
    def __str__(self):
        return f"{self.nom} ({self.entreprise.nom_entreprise})"


class StockBloc(models.Model):
    """
    Gère le stock physique d'un Article dans un Bloc spécifique.
    C'est ici qu'on suit les quantités par quartier pour la rapidité de livraison.
    """
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='stocks_blocs')
    bloc = models.ForeignKey('blocs_app.blocs', on_delete=models.CASCADE, related_name='stocks_articles')
    
    quantite = models.PositiveIntegerField(default=0)
    
    # Seuil d'alerte pour prévenir l'entreprise ou l'admin de bloc que le stock s'épuise
    seuil_alerte = models.PositiveIntegerField(default=5)
    
    derniere_mise_a_jour = models.DateTimeField(auto_now=True)

    class Meta:
        # Un article n'a qu'une seule ligne de stock par bloc
        unique_together = ('article', 'bloc')

    def __str__(self):
        return f"Stock de {self.article.nom} dans le Bloc {self.bloc.name} : {self.quantite} unités"