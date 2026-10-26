import uuid
from django.db import models
from django.utils import timezone
from livreurs_app.models import Livreur
from zones_app.models import Zone
from clients_app.models import Client # Adapte selon le nom de ton app client

class DemandeLivraison(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente de livreur'),
        ('acceptee', 'Acceptée par le livreur'),
        ('en_cours', 'En cours de livraison'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    ]

    STATUT_DESTINATAIRE_CHOICES = [
        ('en_attente', 'En attente de réponse (Lien PWA envoyé)'),
        ('position_recue', 'Position reçue du destinataire'),
        ('alerte_assistant', 'Signalé à l’assistant (Délai 3min dépassé)'),
        ('injoignable', 'Injoignable / Échec'),
    ]

    # --- Relations principales ---
    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name='demandes_livraison',
        help_text="Le client ou l'entreprise qui initie la livraison"
    )
    livreur = models.ForeignKey(
        Livreur,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='demandes_livraison',
    )

    # --- Départ & Arrivée (Zones et GPS) ---
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
    
    # L'arrivée initiale (estimée par le client via le choix du Bloc/Quartier)
    latitude_arrivee = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude_arrivee = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # --- Infos Colis & Tarification ---
    description_colis = models.TextField(blank=True)
    prix = models.DecimalField(max_digits=10, decimal_places=0)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')

    # --- Le Workflow Intelligent du Destinataire (Smart-Drop & PWA) ---
    whatsapp_destinataire = models.CharField(max_length=20, help_text="Numéro WhatsApp pour le lien de géolocalisation")
    
    # Token unique et sécurisé pour générer l'URL PWA éphémère (ex: /colis/verify/<uuid>/)
    token_pwa_destinataire = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    position_destinataire_validee = models.BooleanField(default=False)
    latitude_destinataire_reelle = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude_destinataire_reelle = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    statut_destinataire = models.CharField(
        max_length=30,
        choices=STATUT_DESTINATAIRE_CHOICES,
        default='en_attente'
    )

    # --- Horodatage ---
    date_creation = models.DateTimeField(auto_now_add=True)
    date_acceptation = models.DateTimeField(null=True, blank=True)
    date_livraison = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['statut', 'date_creation'], name='commandes_a_statut_f79ac0_idx'),
            models.Index(fields=['token_pwa_destinataire'], name='idx_token_pwa'),
        ]

    def __str__(self):
        return f"Livraison #{self.pk} — {self.client} → Destinataire ({self.whatsapp_destinataire})"