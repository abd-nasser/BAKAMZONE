from django.conf import settings
from django.db import models


class WebPushSubscription(models.Model):
    """
    Abonnement d'un terminal (mobile PWA ou navigateur desktop) aux notifications Web Push.
    Un même utilisateur peut posséder plusieurs abonnements (plusieurs appareils).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="webpush_subscriptions",
        verbose_name="Utilisateur",
    )
    endpoint = models.URLField(
        max_length=500,
        unique=True,
        verbose_name="Endpoint WebPush",
    )
    p256dh = models.CharField(
        max_length=255,
        verbose_name="Clé publique p256dh",
    )
    auth = models.CharField(
        max_length=255,
        verbose_name="Clé auth",
    )
    user_agent = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="User Agent",
    )
    actif = models.BooleanField(
        default=True,
        verbose_name="Actif",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de souscription",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Dernière mise à jour",
    )

    class Meta:
        verbose_name = "Abonnement Web Push"
        verbose_name_plural = "Abonnements Web Push"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "actif"]),
        ]

    def __str__(self):
        username = getattr(self.user, "username", str(self.user_id))
        return f"Push {username} [{self.endpoint[:30]}...]"
