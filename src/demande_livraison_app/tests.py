from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch
# Adaptateur pour piloter les coroutines Channels depuis les tests Django synchrones.
from asgiref.sync import async_to_sync
# Exécute une modification ORM dans un test async sans bloquer la boucle d'événements.
from channels.db import database_sync_to_async
# Permet de publier un événement dans le groupe pendant le test de révocation.
from channels.layers import get_channel_layer
# Monte uniquement les routes WebSocket pour tester le consumer sans tout le serveur ASGI.
from channels.routing import URLRouter
# Client de test qui simule une connexion WebSocket et son utilisateur de session.
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from kombu.exceptions import OperationalError as CeleryOperationalError

# Modèles utilisés pour construire les profils et les demandes des scénarios d'autorisation.
from admins_app.models import AdminBloc
from blocs_app.models import Blocs
from clients_app.models import Client
from demande_livraison_app.forms import DemandeLivraisonForm
from demande_livraison_app.models import DemandeLivraison
from livreurs_app.models import Livreur, PositionLivreur
from demande_livraison_app.pricing import calculer_tarif_livraison
from zones_app.models import Zone
# Routes réelles du projet, réutilisées pour éviter un chemin de test artificiel.
from bakam_zone.routing import websocket_urlpatterns

# Utilise le modèle utilisateur configurable de Django dans les fixtures de test.
User = get_user_model()


# Redis n'est pas nécessaire pour les tests fonctionnels du consumer ; la couche mémoire suffit.
@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    },
)
class SuiviLivraisonConsumerAuthorizationTests(TransactionTestCase):
    """Vérifie les règles d'accès du suivi WebSocket dans différents contextes métier."""

    def setUp(self):
        """Prépare deux blocs, plusieurs profils et une livraison suivable."""
        self.bloc = Blocs.objects.create(nom="Bloc Suivi")
        self.autre_bloc = Blocs.objects.create(nom="Bloc Autre Suivi")
        self.zone = Zone.objects.create(nom="Zone Suivi", bloc=self.bloc)

        self.client_user = self.create_user("70000101", "client")
        self.client_profile = Client.objects.create(user=self.client_user)
        self.autre_client = self.create_user("70000102", "client")

        self.livreur_user = self.create_user("70000103", "livreur")
        self.livreur = Livreur.objects.create(
            user=self.livreur_user,
            type_vehicule="moto",
            blocs=self.bloc,
        )
        self.autre_livreur = Livreur.objects.create(
            user=self.create_user("70000104", "livreur"),
            type_vehicule="moto",
            blocs=self.bloc,
        )

        self.superviseur = self.create_user("70000105", "bloc_admin")
        self.superviseur_profile = AdminBloc.objects.create(
            user=self.superviseur,
            bloc=self.bloc,
            poste="superviseur_flotte",
        )
        self.superviseur_autre_bloc = self.create_user("70000106", "bloc_admin")
        AdminBloc.objects.create(
            user=self.superviseur_autre_bloc,
            bloc=self.autre_bloc,
            poste="superviseur_flotte",
        )
        self.autre_poste = self.create_user("70000107", "bloc_admin")
        AdminBloc.objects.create(
            user=self.autre_poste,
            bloc=self.bloc,
            poste="assistant",
        )

        self.demande = self.create_demande()
        self.path = f"/ws/livraisons/{self.demande.pk}/suivi/"
        self.application = URLRouter(websocket_urlpatterns)

    def create_user(self, telephone, role):
        """Crée un utilisateur actif avec le rôle demandé pour le scénario."""
        return User.objects.create_user(
            telephone=telephone,
            password="test-password",
            first_name="Test",
            last_name="User",
            role=role,
        )

    def create_demande(self, **overrides):
        """Crée une demande active et géolocalisée, personnalisable par test."""
        values = {
            "client": self.client_profile,
            "livreur": self.livreur,
            "zone_depart": self.zone,
            "zone_arrivee": self.zone,
            "latitude_depart": Decimal("12.345678"),
            "longitude_depart": Decimal("-1.234567"),
            "prix": Decimal("1000"),
            "whatsapp_destinataire": "+22670000000",
            "statut": "en_cours",
            "position_destinataire_validee": True,
            "latitude_destinataire_reelle": Decimal("12.345678"),
            "longitude_destinataire_reelle": Decimal("-1.234567"),
        }
        values.update(overrides)
        return DemandeLivraison.objects.create(**values)

    def can_connect(self, user, path=None):
        """Tente une connexion avec l'utilisateur fourni et ferme toute connexion acceptée."""
        communicator = WebsocketCommunicator(
            self.application,
            path or self.path,
        )
        communicator.scope["user"] = user

        async def connect_and_disconnect():
            """Attend la négociation WebSocket puis nettoie la connexion si elle réussit."""
            connected, _ = await communicator.connect()
            if connected:
                await communicator.disconnect()
            return connected

        return async_to_sync(connect_and_disconnect)()

    def test_delivery_owner_can_connect(self):
        """Le propriétaire de la demande doit pouvoir consulter son suivi."""
        self.assertTrue(self.can_connect(self.client_user))

    def test_other_client_cannot_connect(self):
        """Un autre client ne doit jamais pouvoir consulter cette demande."""
        self.assertFalse(self.can_connect(self.autre_client))

    def test_assigned_courier_can_connect_but_another_courier_cannot(self):
        """Seul le livreur auquel la demande est assignée peut rejoindre son suivi."""
        self.assertTrue(self.can_connect(self.livreur_user))
        self.assertFalse(self.can_connect(self.autre_livreur.user))

    def test_active_fleet_supervisor_can_connect_only_for_own_block(self):
        """Le superviseur doit être actif, du bon bloc et au poste de supervision de flotte."""
        self.assertTrue(self.can_connect(self.superviseur))
        self.assertFalse(self.can_connect(self.superviseur_autre_bloc))
        self.assertFalse(self.can_connect(self.autre_poste))

    def test_terminal_or_unvalidated_deliveries_cannot_be_tracked(self):
        """Une demande terminée ou sans coordonnées destinataire validées n'est pas suivable."""
        terminal = self.create_demande(statut="livree")
        not_ready = self.create_demande(position_destinataire_validee=False)

        self.assertFalse(
            self.can_connect(
                self.client_user,
                f"/ws/livraisons/{terminal.pk}/suivi/",
            )
        )
        self.assertFalse(
            self.can_connect(
                self.client_user,
                f"/ws/livraisons/{not_ready.pk}/suivi/",
            )
        )

    def test_revoked_supervisor_is_closed_before_receiving_a_position(self):
        """Un superviseur désactivé après connexion est refusé à la diffusion suivante."""
        communicator = WebsocketCommunicator(self.application, self.path)
        communicator.scope["user"] = self.superviseur

        async def connect_revoke_and_publish():
            """Connecte le superviseur, révoque son profil puis publie une fausse position."""
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            await database_sync_to_async(
                AdminBloc.objects.filter(pk=self.superviseur_profile.pk).update
            )(actif=False)
            await get_channel_layer().group_send(
                f"livraison_suivi_{self.demande.pk}",
                {
                    "type": "position_livreur",
                    "data": {"type": "position", "latitude": 12.3},
                },
            )
            return await communicator.receive_output(timeout=1)

        output = async_to_sync(connect_revoke_and_publish)()

        self.assertEqual(output["type"], "websocket.close")
        self.assertEqual(output["code"], 4403)

    def test_assigned_courier_can_publish_position_to_tracking_group(self):
        """Le livreur assigné met à jour sa position et la reçoit via le groupe privé."""
        communicator = WebsocketCommunicator(self.application, self.path)
        communicator.scope["user"] = self.livreur_user

        async def connect_publish_and_receive():
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.send_json_to(
                {
                    "type": "position",
                    "latitude": 12.345678,
                    "longitude": -1.234567,
                }
            )
            event = await communicator.receive_json_from()
            await communicator.disconnect()
            return event

        event = async_to_sync(connect_publish_and_receive)()

        self.livreur.refresh_from_db()
        self.assertEqual(event["type"], "position")
        self.assertEqual(event["latitude"], "12.345678")
        self.assertEqual(self.livreur.latitude, Decimal("12.345678"))
        self.assertIsNotNone(self.livreur.position_suivi_mise_a_jour)
        self.assertEqual(PositionLivreur.objects.filter(livreur=self.livreur).count(), 1)

    def test_position_updates_are_throttled_to_one_per_15_seconds(self):
        """Un message GPS trop rapproché ne remplace ni ne rediffuse la position."""
        communicator = WebsocketCommunicator(self.application, self.path)
        communicator.scope["user"] = self.livreur_user

        async def publish_twice():
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.send_json_to(
                {
                    "type": "position",
                    "latitude": 12.345678,
                    "longitude": -1.234567,
                }
            )
            await communicator.receive_json_from()
            await communicator.send_json_to(
                {
                    "type": "position",
                    "latitude": 12.4,
                    "longitude": -1.2,
                }
            )
            await communicator.disconnect()

        async_to_sync(publish_twice)()

        self.livreur.refresh_from_db()
        self.assertEqual(self.livreur.latitude, Decimal("12.345678"))
        self.assertEqual(PositionLivreur.objects.filter(livreur=self.livreur).count(), 1)

    def test_position_history_is_written_no_more_than_once_per_minute(self):
        """La position courante peut évoluer sans enregistrer chaque point en historique."""
        async def publish_position(latitude):
            communicator = WebsocketCommunicator(self.application, self.path)
            communicator.scope["user"] = self.livreur_user
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.send_json_to(
                {
                    "type": "position",
                    "latitude": latitude,
                    "longitude": -1.234567,
                }
            )
            await communicator.receive_json_from()
            await communicator.disconnect()

        async_to_sync(publish_position)(12.345678)
        Livreur.objects.filter(pk=self.livreur.pk).update(
            position_suivi_mise_a_jour=timezone.now() - timedelta(seconds=16),
        )
        async_to_sync(publish_position)(12.4)
        self.assertEqual(PositionLivreur.objects.filter(livreur=self.livreur).count(), 1)

        PositionLivreur.objects.filter(livreur=self.livreur).update(
            horodatage=timezone.now() - timedelta(seconds=61),
        )
        Livreur.objects.filter(pk=self.livreur.pk).update(
            position_suivi_mise_a_jour=timezone.now() - timedelta(seconds=16),
        )
        async_to_sync(publish_position)(12.5)
        self.assertEqual(PositionLivreur.objects.filter(livreur=self.livreur).count(), 2)

    def test_invalid_coordinates_close_the_socket_without_saving(self):
        """Les coordonnées hors limites sont rejetées avant d'atteindre les modèles."""
        communicator = WebsocketCommunicator(self.application, self.path)
        communicator.scope["user"] = self.livreur_user

        async def send_invalid_position():
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.send_json_to(
                {
                    "type": "position",
                    "latitude": 91,
                    "longitude": -1.234567,
                }
            )
            return await communicator.receive_output()

        output = async_to_sync(send_invalid_position)()

        self.assertEqual(output["type"], "websocket.close")
        self.assertEqual(output["code"], 4400)
        self.livreur.refresh_from_db()
        self.assertIsNone(self.livreur.position_suivi_mise_a_jour)
        self.assertFalse(PositionLivreur.objects.filter(livreur=self.livreur).exists())

    def test_tracking_reader_cannot_publish_position(self):
        """Le client peut lire les positions mais seul le livreur assigné peut émettre."""
        communicator = WebsocketCommunicator(self.application, self.path)
        communicator.scope["user"] = self.client_user

        async def send_as_client():
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.send_json_to(
                {
                    "type": "position",
                    "latitude": 12.345678,
                    "longitude": -1.234567,
                }
            )
            return await communicator.receive_output()

        output = async_to_sync(send_as_client)()

        self.assertEqual(output["type"], "websocket.close")
        self.assertEqual(output["code"], 4403)
        self.assertFalse(PositionLivreur.objects.filter(livreur=self.livreur).exists())


class DemandeLivraisonPricingTestCase(TestCase):
    def setUp(self):
        self.bloc_a = Blocs.objects.create(
            nom="Bloc Tampouy",
            code="BLK-TAMP",
            ville="ouagadougou",
            quartier="tampouy",
        )
        self.bloc_b = Blocs.objects.create(
            nom="Bloc Gounghin",
            code="BLK-GOUNG",
            ville="ouagadougou",
            quartier="gounghin",
        )
        self.zone_a1 = Zone.objects.create(
            nom="Tampouy Nord",
            code="ZN-TN",
            bloc=self.bloc_a,
            latitude=Decimal("12.390000"),
            longitude=Decimal("-1.540000"),
        )
        self.zone_a2 = Zone.objects.create(
            nom="Tampouy Sud",
            code="ZN-TS",
            bloc=self.bloc_a,
            latitude=Decimal("12.380000"),
            longitude=Decimal("-1.530000"),
        )
        self.zone_b1 = Zone.objects.create(
            nom="Gounghin Centre",
            code="ZN-GC",
            bloc=self.bloc_b,
            latitude=Decimal("12.350000"),
            longitude=Decimal("-1.550000"),
        )

    def test_tarif_intra_bloc(self):
        tarif = calculer_tarif_livraison(self.zone_a1, self.zone_a2)
        self.assertEqual(tarif, Decimal("1000"))

    def test_tarif_inter_blocs(self):
        tarif = calculer_tarif_livraison(self.zone_a1, self.zone_b1)
        self.assertEqual(tarif, Decimal("1500"))


class DemandeLivraisonFormTestCase(TestCase):
    def setUp(self):
        self.bloc = Blocs.objects.create(
            nom="Bloc Tampouy",
            code="BLK-TAMP",
            ville="ouagadougou",
            quartier="tampouy",
        )
        self.bloc_autre = Blocs.objects.create(
            nom="Bloc Somgande",
            code="BLK-SOM",
            ville="ouagadougou",
            quartier="somgande",
        )
        self.zone_depart = Zone.objects.create(
            nom="Tampouy Est",
            code="ZN-TE",
            bloc=self.bloc,
            latitude=Decimal("12.395000"),
            longitude=Decimal("-1.535000"),
        )
        self.zone_arrivee_meme_bloc = Zone.objects.create(
            nom="Tampouy Ouest",
            code="ZN-TO",
            bloc=self.bloc,
            latitude=Decimal("12.396000"),
            longitude=Decimal("-1.545000"),
        )
        self.zone_arrivee_autre_bloc = Zone.objects.create(
            nom="Somgande Gare",
            code="ZN-SG",
            bloc=self.bloc_autre,
            latitude=Decimal("12.410000"),
            longitude=Decimal("-1.490000"),
        )
        self.user = User.objects.create_user(
            telephone="+22670112233",
            username="client_test",
            password="password123",
            role="client",
        )
        self.client_profil = Client.objects.create(user=self.user)

    def test_form_valide_avec_gps_intra_bloc(self):
        form_data = {
            'zone_depart': self.zone_depart.pk,
            'zone_arrivee': self.zone_arrivee_meme_bloc.pk,
            'latitude_depart': '12.391234',
            'longitude_depart': '-1.531234',
            'whatsapp_destinataire': '+226 76 54 32 10',
            'description_colis': 'Paquet de café',
        }
        form = DemandeLivraisonForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        demande = form.save(client=self.client_profil)
        self.assertEqual(demande.client, self.client_profil)
        self.assertEqual(demande.prix, Decimal("1000"))
        self.assertEqual(demande.whatsapp_destinataire, "+22676543210")
        self.assertEqual(demande.statut, "en_attente")
        self.assertIsNotNone(demande.token_pwa_destinataire)

    def test_form_valide_inter_blocs(self):
        form_data = {
            'zone_depart': self.zone_depart.pk,
            'zone_arrivee': self.zone_arrivee_autre_bloc.pk,
            'latitude_depart': '12.391234',
            'longitude_depart': '-1.531234',
            'whatsapp_destinataire': '70123456',
        }
        form = DemandeLivraisonForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        demande = form.save(client=self.client_profil)
        self.assertEqual(demande.prix, Decimal("1500"))
        self.assertEqual(demande.latitude_arrivee, self.zone_arrivee_autre_bloc.latitude)
        self.assertEqual(demande.longitude_arrivee, self.zone_arrivee_autre_bloc.longitude)

    def test_form_repli_gps_sur_zone_depart(self):
        form_data = {
            'zone_depart': self.zone_depart.pk,
            'zone_arrivee': self.zone_arrivee_meme_bloc.pk,
            'whatsapp_destinataire': '+22670000000',
        }
        form = DemandeLivraisonForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        demande = form.save(client=self.client_profil)
        self.assertEqual(demande.latitude_depart, self.zone_depart.latitude)
        self.assertEqual(demande.longitude_depart, self.zone_depart.longitude)

    def test_form_whatsapp_invalide(self):
        form_data = {
            'zone_depart': self.zone_depart.pk,
            'zone_arrivee': self.zone_arrivee_meme_bloc.pk,
            'latitude_depart': '12.390000',
            'longitude_depart': '-1.530000',
            'whatsapp_destinataire': '123',
        }
        form = DemandeLivraisonForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('whatsapp_destinataire', form.errors)


class CreerDemandeLivraisonViewTestCase(TestCase):
    def setUp(self):
        self.bloc = Blocs.objects.create(
            nom="Bloc Tampouy",
            code="BLK-TAMP",
            ville="ouagadougou",
            quartier="tampouy",
        )
        self.zone_depart = Zone.objects.create(
            nom="Tampouy Nord",
            code="ZN-TN",
            bloc=self.bloc,
            latitude=Decimal("12.390000"),
            longitude=Decimal("-1.540000"),
        )
        self.zone_arrivee = Zone.objects.create(
            nom="Tampouy Sud",
            code="ZN-TS",
            bloc=self.bloc,
            latitude=Decimal("12.380000"),
            longitude=Decimal("-1.530000"),
        )
        self.client_user = User.objects.create_user(
            telephone="+22670998877",
            username="client_user",
            password="testpassword",
            role="client",
            first_name="Issa",
        )
        self.client_profil = Client.objects.create(user=self.client_user)

        self.autre_user = User.objects.create_user(
            telephone="+22670111111",
            username="livreur_user",
            password="testpassword",
            role="livreur",
        )

    def test_acces_non_authentifie_redirige(self):
        url = reverse('demande_livraison_app:creer-demande')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_acces_non_client_refuse(self):
        self.client.force_login(self.autre_user)
        url = reverse('demande_livraison_app:creer-demande')
        response = self.client.get(url)
        self.assertIn(response.status_code, [302, 403])

    def test_acces_client_autorise(self):
        self.client.force_login(self.client_user)
        url = reverse('demande_livraison_app:creer-demande')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Demander une livraison")
        self.assertContains(response, "Tampouy Nord")

    def test_creation_demande_post_reussie(self):
        self.client.force_login(self.client_user)
        url = reverse('demande_livraison_app:creer-demande')
        response = self.client.post(url, {
            'zone_depart': self.zone_depart.pk,
            'zone_arrivee': self.zone_arrivee.pk,
            'latitude_depart': '12.390000',
            'longitude_depart': '-1.540000',
            'whatsapp_destinataire': '+22678001122',
            'description_colis': 'Documents confidentiels',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('clients_app:tableau-de-bord'))

        demande = DemandeLivraison.objects.first()
        self.assertIsNotNone(demande)
        self.assertEqual(demande.client, self.client_profil)
        self.assertEqual(demande.prix, Decimal("1000"))
        self.assertEqual(demande.whatsapp_destinataire, "+22678001122")
        self.assertEqual(demande.description_colis, "Documents confidentiels")

    def test_calculer_tarif_api(self):
        url = reverse('demande_livraison_app:calculer-tarif')
        response = self.client.get(url, {
            'zone_depart': self.zone_depart.pk,
            'zone_arrivee': self.zone_arrivee.pk,
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['prix'], 1000)
        self.assertTrue(data['est_intra'])


class DestinataireGeoViewTestCase(TestCase):
    def setUp(self):
        bloc = Blocs.objects.create(nom="Bloc Smart-Drop", code="BLK-SD")
        zone = Zone.objects.create(nom="Zone Smart-Drop", bloc=bloc)
        user = User.objects.create_user(
            telephone="+22670000001",
            username="smartdrop_client",
            password="test-password",
            role="client",
        )
        client_profil = Client.objects.create(user=user)
        self.demande = DemandeLivraison.objects.create(
            client=client_profil,
            zone_depart=zone,
            zone_arrivee=zone,
            latitude_depart=Decimal("12.390000"),
            longitude_depart=Decimal("-1.540000"),
            prix=Decimal("1000"),
            whatsapp_destinataire="+22670000002",
        )
        livreur_user = User.objects.create_user(
            telephone="+22670000003",
            username="smartdrop_livreur",
            password="livreur-password",
            first_name="Livreur",
            last_name="Test",
            role="livreur",
        )
        self.livreur = Livreur.objects.create(
            user=livreur_user,
            type_vehicule="moto",
            blocs=bloc,
        )
        self.demande.livreur = self.livreur
        self.demande.statut = "acceptee"
        self.demande.save(update_fields=["livreur", "statut"])
        self.url = reverse(
            "destinataire-geo",
            kwargs={"token_pwa_destinataire": self.demande.token_pwa_destinataire},
        )

    @patch("notifications_app.tasks.envoyer_notification_webpush_task.delay")
    def test_recipient_can_submit_valid_coordinates(self, send_push_notification):
        response = self.client.post(
            self.url,
            {"latitude": "12.345678", "longitude": "-1.234567"},
        )

        self.assertEqual(response.status_code, 200)
        self.demande.refresh_from_db()
        self.assertTrue(self.demande.position_destinataire_validee)
        self.assertEqual(
            self.demande.latitude_destinataire_reelle,
            Decimal("12.345678"),
        )
        self.assertEqual(self.demande.statut_position_destinataire, "position_recue")
        send_push_notification.assert_called_once_with(
            user_id=self.demande.client.user_id,
            title="Position du destinataire disponible",
            body=(
                f"Le destinataire de votre course #{self.demande.pk} a partagé "
                "sa position. Le suivi GPS peut démarrer."
            ),
            target_url=reverse("clients_app:tableau-de-bord"),
        )

    @patch("notifications_app.tasks.envoyer_notification_webpush_task.delay")
    def test_revalidating_location_does_not_send_another_push(self, send_push_notification):
        coordinates = {"latitude": "12.345678", "longitude": "-1.234567"}

        self.client.post(self.url, coordinates)
        self.client.post(self.url, {"latitude": "12.4", "longitude": "-1.2"})

        send_push_notification.assert_called_once()

    @patch("notifications_app.tasks.envoyer_notification_webpush_task.delay")
    def test_location_without_active_assigned_courier_does_not_notify_client(
        self,
        send_push_notification,
    ):
        self.demande.livreur = None
        self.demande.statut = "en_attente"
        self.demande.save(update_fields=["livreur", "statut"])

        response = self.client.post(
            self.url,
            {"latitude": "12.345678", "longitude": "-1.234567"},
        )

        self.assertEqual(response.status_code, 200)
        send_push_notification.assert_not_called()

    @patch(
        "notifications_app.tasks.envoyer_notification_webpush_task.delay",
        side_effect=CeleryOperationalError("broker unavailable"),
    )
    def test_push_queue_failure_is_reported_without_losing_recipient_location(
        self,
        send_push_notification,
    ):
        with self.assertLogs("notifications_app.services", level="ERROR"):
            response = self.client.post(
                self.url,
                {"latitude": "12.345678", "longitude": "-1.234567"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("notification du client", response.context["notification_warning"])
        self.demande.refresh_from_db()
        self.assertTrue(self.demande.position_destinataire_validee)
        send_push_notification.assert_called_once()

    def test_rejects_malformed_or_out_of_range_coordinates(self):
        for latitude in ("invalid", "91", "NaN"):
            with self.subTest(latitude=latitude):
                response = self.client.post(
                    self.url,
                    {"latitude": latitude, "longitude": "-1.234567"},
                )

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Coordonnées GPS reçues invalides.")
                self.demande.refresh_from_db()
                self.assertFalse(self.demande.position_destinataire_validee)
