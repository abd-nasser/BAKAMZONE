from django.db import models
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
    
    # Image principale de l'article
    image = models.ImageField(upload_to='articles/images/', null=True, blank=True)
    
    # Disponibilité globale de l'article
    disponible = models.BooleanField(default=True)
    
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

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