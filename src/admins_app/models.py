from django.db import models
from django.conf import settings
from blocs_app.models import Blocs


class AdminBloc(models.Model):
    """
    Profil Administrateur de Bloc (membre de l'équipe de gestion locale d'un Bloc BAKAMZONE).
    Chaque administrateur est un utilisateur avec role='bloc_admin', affecté à un Bloc précis.
    """
    POSTE_CHOICES = [
        ('responsable', 'Responsable de Bloc (Chef d’équipe)'),
        ('gestionnaire_stock', 'Gestionnaire des Stocks & Réceptions'),
        ('superviseur_flotte', 'Superviseur de Flotte & Livreurs'),
        ('assistant', 'Assistant Opérationnel'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admin_bloc_profil',
        verbose_name="Compte utilisateur"
    )
    bloc = models.ForeignKey(
        Blocs,
        on_delete=models.CASCADE,
        related_name='admins_bloc',
        verbose_name="Bloc affecté"
    )
    poste = models.CharField(
        max_length=50,
        choices=POSTE_CHOICES,
        default='responsable',
        verbose_name="Rôle dans l'équipe"
    )
    telephone_secondaire = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Téléphone secondaire / d'urgence"
    )
    actif = models.BooleanField(
        default=True,
        verbose_name="Actif dans ce bloc"
    )
    date_assignation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date d'assignation"
    )
    date_modification = models.DateTimeField(
        auto_now=True,
        verbose_name="Dernière modification"
    )

    class Meta:
        verbose_name = "Administrateur de Bloc"
        verbose_name_plural = "Administrateurs de Blocs"
        ordering = ['bloc', 'poste', '-date_assignation']

    def __str__(self):
        nom_complet = self.user.get_full_name() or self.user.telephone
        return f"{nom_complet} — {self.get_poste_display()} ({self.bloc.nom})"
