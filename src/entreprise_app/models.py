from django.db import models
from django.db.models import Q

from auth_app.models import User

class Entreprise(models.Model):
    """
    Profil pour l'Entreprise partenaire (qui stocke ses produits dans les blocs).
    """
    PALIER_CHOICES = [
        ('pas_defini', 'Pas defini'),
        ('standard', 'Standard'),
        ('pro', 'Pro'),
        ('premium', "Premium")
    ]
    user_principal = models.OneToOneField(User, on_delete=models.CASCADE, related_name='enterprise_profile')
    logo = models.ImageField(upload_to='entreprises/logos', null=True, blank=True)
    nom_entreprise = models.CharField(max_length=150)
    rc_number = models.CharField(max_length=100, blank=True, null=True, help_text="Numéro de registre de commerce")
    address = models.TextField()
    
    palier = models.CharField(max_length=20, choices=PALIER_CHOICES, default='pas_defini')
    # Gestion des abonnements mentionnée dans le cahier des charges
    subscription_active = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    QUOTAS_ARTICLES = {
        'standard': 15,
        'pro': 50,
        'premium': 100
    }
    
    QUOTAS_ADMINS = {
        'standard': 1,
        'pro': 5,     
        'premium': 10,
       
    }
    
    @property
    def quota_articles(self):
        return self.QUOTAS_ARTICLES.get(self.palier, 0)
    
    @property
    def quota_admins(self):
        return self.QUOTAS_ADMINS.get(self.palier, 0)
    
    @property
    def nb_articles_actuels(self):
        return self.articles.filter(disponible=True).count()
    
    @property 
    def nb_admins_actuels(self):
        return self.membres_admin.count()

    def __str__(self):
        return f"Entreprise: {self.nom_entreprise}"
    
    
class MembreAdminsEntreprise(models.Model):
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='membres_admin')
    membre_admin = models.OneToOneField(User, on_delete=models.CASCADE, related_name='membre_admin_profil')
    date_ajout = models.DateTimeField(auto_now_add=True)
    ajoute_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='admins_ajoutes')
    def __str__(self):
        return f"{self.membre_admin.get_full_name()} — admin {self.entreprise.nom_entreprise}"


class RetraitEntreprise(models.Model):
    STATUT_EN_ATTENTE = "en_attente"
    STATUT_APPROUVE = "approuve"
    STATUT_PAYE = "paye"
    STATUT_REJETE = "rejete"
    STATUT_CHOICES = [
        (STATUT_EN_ATTENTE, "En attente de validation"),
        (STATUT_APPROUVE, "Approuvé, paiement à effectuer"),
        (STATUT_PAYE, "Payé"),
        (STATUT_REJETE, "Rejeté"),
    ]

    entreprise = models.ForeignKey(
        Entreprise,
        on_delete=models.PROTECT,
        related_name="retraits",
    )
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=STATUT_EN_ATTENTE,
    )
    date_demande = models.DateTimeField(auto_now_add=True)
    date_traitement = models.DateTimeField(null=True, blank=True)
    traite_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="retraits_entreprise_traites",
    )

    class Meta:
        ordering = ["-date_demande"]
        constraints = [
            models.CheckConstraint(
                condition=Q(montant__gt=0),
                name="retrait_entreprise_montant_positif",
            ),
        ]
        indexes = [
            models.Index(fields=["entreprise", "statut"]),
            models.Index(fields=["statut", "date_demande"]),
        ]

    def __str__(self):
        return f"Retrait {self.montant} FCFA — {self.entreprise.nom_entreprise}"