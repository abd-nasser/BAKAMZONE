from decimal import Decimal, InvalidOperation

# Exécute les accès ORM synchrones dans un thread, sans bloquer la boucle async.
from channels.db import database_sync_to_async
# Consumer Channels qui reçoit et émet des messages JSON sur un WebSocket.
from channels.generic.websocket import AsyncJsonWebsocketConsumer
# Récupère le modèle utilisateur configuré par le projet plutôt que de le coder en dur.
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

# Profil de bloc nécessaire pour vérifier le rôle et le périmètre du superviseur.
from admins_app.models import AdminBloc
# Demande liée au suivi et source des règles métier d'accès.
from demande_livraison_app.models import DemandeLivraison
from livreurs_app.models import Livreur, PositionLivreur


class SuiviLivraisonConsumer(AsyncJsonWebsocketConsumer):
    """Gère l'autorisation de suivi, l'émission GPS du livreur et sa diffusion."""

    # Une demande n'est suivable qu'avant sa clôture ; les statuts terminaux sont exclus.
    TRACKABLE_STATUSES = ("acceptee", "en_cours")
    POSITION_INTERVAL_SECONDS = 15
    HISTORY_INTERVAL_SECONDS = 60

    async def connect(self):
        """Authentifie et autorise l'utilisateur avant de l'abonner au groupe de course."""
        self.demande_id = self.scope["url_route"]["kwargs"]["demande_id"]
        user = self.scope.get("user")

        # Refuse les sessions absentes ou désactivées avant tout accès aux données.
        if user is None or not user.is_authenticated or not user.is_active:
            await self.close(code=4401)
            return

        # Le groupe est privé à la course ; seul un utilisateur autorisé peut le rejoindre.
        if await self._get_access_role(self.demande_id, user.pk) is None:
            await self.close(code=4403)
            return

        # Le même groupe permet de diffuser les positions sans les envoyer à tous les clients.
        self.group_name = f"livraison_suivi_{self.demande_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        """Retire le canal du groupe pour ne plus recevoir les positions après déconnexion."""
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )

    async def receive_json(self, content, **kwargs):
        """Valide et enregistre une position envoyée uniquement par le livreur assigné."""
        coordinates = self._parse_coordinates(content)
        if coordinates is None:
            await self.close(code=4400)
            return

        result = await self._save_position(
            self.demande_id,
            self.scope["user"].pk,
            *coordinates,
        )
        if result is None:
            await self.close(code=4403)
            return
        if result == "throttled":
            return

        # Le groupe est privé à la course ; chaque destinataire revérifie ses droits
        # au moment où il reçoit l'événement.
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "position_livreur", "data": result},
        )

    async def position_livreur(self, event):
        """Transmet une position du groupe après avoir revérifié les droits actuels."""
        user = self.scope["user"]
        # Les rôles ou affectations peuvent changer pendant une connexion persistante.
        if await self._get_access_role(self.demande_id, user.pk) is None:
            await self.close(code=4403)
            return

        await self.send_json(event["data"])

    @staticmethod
    def _parse_coordinates(content):
        """Convertit les coordonnées JSON et refuse les valeurs hors du domaine GPS."""
        if (
            not isinstance(content, dict)
            or set(content) != {"type", "latitude", "longitude"}
            or content["type"] != "position"
        ):
            return None

        coordinates = []
        for value, lower_bound, upper_bound in (
            (content["latitude"], Decimal("-90"), Decimal("90")),
            (content["longitude"], Decimal("-180"), Decimal("180")),
        ):
            if isinstance(value, bool) or len(str(value)) > 32:
                return None
            try:
                coordinate = Decimal(str(value))
                if not coordinate.is_finite() or not lower_bound <= coordinate <= upper_bound:
                    return None
                coordinates.append(coordinate.quantize(Decimal("0.000001")))
            except (InvalidOperation, TypeError, ValueError):
                return None

        return tuple(coordinates)

    @database_sync_to_async
    def _save_position(self, demande_id, user_id, latitude, longitude):
        """Enregistre la position du livreur actif et limite les écritures concurrentes."""
        with transaction.atomic():
            demande = (
                DemandeLivraison.objects.select_for_update(of=("self",))
                .filter(
                    pk=demande_id,
                    statut__in=self.TRACKABLE_STATUSES,
                    livreur__actif=True,
                    livreur__user_id=user_id,
                    position_destinataire_validee=True,
                    latitude_destinataire_reelle__isnull=False,
                    longitude_destinataire_reelle__isnull=False,
                )
                .first()
            )
            if demande is None:
                return None

            user_is_active_courier = get_user_model().objects.filter(
                pk=user_id,
                is_active=True,
                role="livreur",
            ).exists()
            if not user_is_active_courier:
                return None

            livreur = Livreur.objects.select_for_update().get(pk=demande.livreur_id)
            received_at = timezone.now()
            last_position_at = livreur.position_suivi_mise_a_jour
            if (
                last_position_at is not None
                and (received_at - last_position_at).total_seconds()
                < self.POSITION_INTERVAL_SECONDS
            ):
                return "throttled"

            livreur.latitude = latitude
            livreur.longitude = longitude
            livreur.position_suivi_mise_a_jour = received_at
            livreur.save(
                update_fields=[
                    "latitude",
                    "longitude",
                    "position_suivi_mise_a_jour",
                ],
            )

            last_history_at = (
                PositionLivreur.objects.filter(livreur=livreur)
                .order_by("-horodatage")
                .values_list("horodatage", flat=True)
                .first()
            )
            if (
                last_history_at is None
                or (received_at - last_history_at).total_seconds()
                >= self.HISTORY_INTERVAL_SECONDS
            ):
                PositionLivreur.objects.create(
                    livreur=livreur,
                    latitude=latitude,
                    longitude=longitude,
                )

            return {
                "type": "position",
                "latitude": str(latitude),
                "longitude": str(longitude),
                "timestamp": received_at.isoformat(),
            }

    @database_sync_to_async
    def _get_access_role(self, demande_id, user_id):
        """Retourne le profil autorisé, ou None si l'accès à la course doit être refusé."""
        # Recharger le rôle en base évite de faire confiance à une session devenue obsolète.
        user_role = (
            get_user_model()
            .objects.filter(pk=user_id, is_active=True)
            .values_list("role", flat=True)
            .first()
        )
        if user_role is None:
            return None

        # Vérifier aussi l'état du suivi évite l'accès aux courses clôturées ou non activées.
        demande = (
            DemandeLivraison.objects.select_related("client", "livreur")
            .filter(
                pk=demande_id,
                statut__in=self.TRACKABLE_STATUSES,
                livreur__actif=True,
                position_destinataire_validee=True,
                latitude_destinataire_reelle__isnull=False,
                longitude_destinataire_reelle__isnull=False,
            )
            .first()
        )
        if demande is None or demande.livreur is None:
            return None

        # Le client ne peut suivre que sa propre demande.
        if user_role == "client" and demande.client.user_id == user_id:
            return "client"

        # Le livreur ne peut accéder qu'à une course qui lui est assignée.
        if user_role == "livreur" and demande.livreur.user_id == user_id:
            return "livreur"

        # Le profil actif et le bloc doivent correspondre à la flotte suivie.
        if user_role == "bloc_admin" and AdminBloc.objects.filter(
            user_id=user_id,
            bloc_id=demande.livreur.blocs_id,
            poste="superviseur_flotte",
            actif=True,
        ).exists():
            return "superviseur_flotte"

        return None
