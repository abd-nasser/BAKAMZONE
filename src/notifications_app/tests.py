import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from admins_app.models import AdminBloc
from blocs_app.models import Blocs
from clients_app.models import Client, SupportConversation, SupportMessage
from demande_livraison_app.models import DemandeLivraison
from livreurs_app.models import Livreur
from notifications_app.models import WebPushSubscription
from notifications_app.tasks import (
    envoyer_notification_webpush_task,
    notifier_acceptation_demande_livraison_task,
    notifier_nouveau_message_support_task,
)
from zones_app.models import Zone

User = get_user_model()


class WebPushSubscriptionModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="client_test",
            telephone="+22670000001",
            password="password123",
            role="client",
        )

    def test_create_subscription(self):
        sub = WebPushSubscription.objects.create(
            user=self.user,
            endpoint="https://fcm.googleapis.com/fcm/send/test-endpoint-1",
            p256dh="BNcRdreALRFdj...key",
            auth="tBHItTestAuthSecret",
        )
        self.assertEqual(sub.user, self.user)
        self.assertTrue(sub.actif)
        self.assertIn("client_test", str(sub))


class WebPushViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="pwa_user",
            telephone="+22670000002",
            password="password123",
            role="client",
        )
        self.client.login(username="pwa_user", password="password123")

    def authenticate(self):
        self.client.force_login(self.user)

    @override_settings(VAPID_PUBLIC_KEY="public-vapid-key")
    def test_vapid_public_key_view(self):
        self.authenticate()
        url = reverse("notifications_app:vapid-key")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["public_key"], "public-vapid-key")

    def test_vapid_public_key_view_reports_missing_configuration(self):
        response = self.client.get(reverse("notifications_app:vapid-key"))
        self.assertEqual(response.status_code, 503)
        self.assertIn("error", response.json())

    def test_service_worker_is_available_at_site_root(self):
        response = self.client.get(reverse("service-worker"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Service-Worker-Allowed"], "/")
        content = b"".join(response.streaming_content).decode()
        self.assertIn("notificationclick", content)

    def test_authenticated_page_offers_push_activation(self):
        self.authenticate()
        response = self.client.get(reverse("home_app:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'rel="manifest"')
        self.assertContains(response, 'href="/static/manifest.json"')
        self.assertContains(response, 'id="pwa-push-button"')

    def test_subscribe_json_view(self):
        self.authenticate()
        url = reverse("notifications_app:subscribe")
        payload = {
            "endpoint": "https://push.apple.com/send/ios-device-token-123",
            "keys": {
                "p256dh": "dummy-p256dh-key",
                "auth": "dummy-auth-secret",
            },
        }
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertTrue(data.get("created"))
        self.assertTrue(
            WebPushSubscription.objects.filter(
                user=self.user,
                endpoint="https://push.apple.com/send/ios-device-token-123",
            ).exists()
        )

    def test_subscribe_rejects_non_object_json(self):
        self.authenticate()
        response = self.client.post(
            reverse("notifications_app:subscribe"),
            data=json.dumps(["not", "an", "object"]),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_subscribe_update_existing(self):
        self.authenticate()
        url = reverse("notifications_app:subscribe")
        payload = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/device-repeat",
            "keys": {"p256dh": "key1", "auth": "auth1"},
        }
        self.client.post(url, data=json.dumps(payload), content_type="application/json")

        payload["keys"]["auth"] = "auth2_updated"
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json().get("created"))
        sub = WebPushSubscription.objects.get(endpoint="https://fcm.googleapis.com/fcm/send/device-repeat")
        self.assertEqual(sub.auth, "auth2_updated")

    def test_unsubscribe_view(self):
        self.authenticate()
        WebPushSubscription.objects.create(
            user=self.user,
            endpoint="https://fcm.googleapis.com/fcm/send/to-delete",
            p256dh="key",
            auth="auth",
        )
        url = reverse("notifications_app:unsubscribe")
        response = self.client.post(
            url,
            data=json.dumps({"endpoint": "https://fcm.googleapis.com/fcm/send/to-delete"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            WebPushSubscription.objects.filter(
                endpoint="https://fcm.googleapis.com/fcm/send/to-delete"
            ).exists()
        )


class WebPushTasksTests(TestCase):
    def setUp(self):
        self.bloc = Blocs.objects.create(nom="Bloc Push Test", actif=True)
        self.client_user = User.objects.create_user(
            username="client_chat",
            telephone="+22670000003",
            password="password123",
            role="client",
        )
        self.client_profile = Client.objects.create(user=self.client_user)

        self.assistant_user = User.objects.create_user(
            username="assistant_chat",
            telephone="+22670000004",
            password="password123",
            role="bloc_admin",
        )
        self.admin_bloc = AdminBloc.objects.create(
            user=self.assistant_user,
            bloc=self.bloc,
            poste="assistant",
            actif=True,
        )

        self.conversation = SupportConversation.objects.create(
            client=self.client_profile,
            bloc=self.bloc,
        )

    def test_envoyer_notification_webpush_task_no_subscription(self):
        res = envoyer_notification_webpush_task(
            user_id=self.client_user.pk,
            title="Test",
            body="Bonjour",
        )
        self.assertEqual(res["status"], "no_subscription")
        self.assertEqual(res["sent"], 0)

    def test_envoyer_notification_webpush_task_does_not_fake_send_without_key(self):
        subscription = WebPushSubscription.objects.create(
            user=self.client_user,
            endpoint="https://fcm.googleapis.com/fcm/send/user-phone",
            p256dh="key",
            auth="auth",
        )
        res = envoyer_notification_webpush_task(
            user_id=self.client_user.pk,
            title="Alerte",
            body="Votre commande arrive",
        )
        self.assertEqual(res["sent"], 0)
        self.assertEqual(res["status"], "configuration_error")
        self.assertTrue(WebPushSubscription.objects.filter(pk=subscription.pk).exists())

    @override_settings(VAPID_PRIVATE_KEY="test-private-key")
    def test_envoyer_notification_webpush_task_sends_with_configured_key(self):
        WebPushSubscription.objects.create(
            user=self.client_user,
            endpoint="https://fcm.googleapis.com/fcm/send/user-phone",
            p256dh="key",
            auth="auth",
        )
        mock_webpush = Mock()
        pywebpush_module = SimpleNamespace(
            webpush=mock_webpush,
            WebPushException=Exception,
        )

        with patch.dict("sys.modules", {"pywebpush": pywebpush_module}):
            result = envoyer_notification_webpush_task(
                user_id=self.client_user.pk,
                title="Alerte",
                body="Votre commande arrive",
            )

        self.assertEqual(result["sent"], 1)
        self.assertEqual(result["mode"], "real")
        mock_webpush.assert_called_once()

    @override_settings(VAPID_PRIVATE_KEY="test-private-key")
    def test_envoyer_notification_webpush_task_removes_expired_subscription(self):
        subscription = WebPushSubscription.objects.create(
            user=self.client_user,
            endpoint="https://fcm.googleapis.com/fcm/send/expired",
            p256dh="key",
            auth="auth",
        )

        class GoneError(Exception):
            response = SimpleNamespace(status_code=410)

        pywebpush_module = SimpleNamespace(
            webpush=Mock(side_effect=GoneError),
            WebPushException=GoneError,
        )
        with patch.dict("sys.modules", {"pywebpush": pywebpush_module}):
            result = envoyer_notification_webpush_task(
                user_id=self.client_user.pk,
                title="Alerte",
                body="Votre commande arrive",
            )

        self.assertEqual(result["removed"], 1)
        self.assertFalse(WebPushSubscription.objects.filter(pk=subscription.pk).exists())

    @patch("notifications_app.tasks.envoyer_notification_webpush_task.delay")
    def test_notifier_nouveau_message_support_from_client(self, mock_push_delay):
        message = SupportMessage.objects.create(
            conversation=self.conversation,
            sender=self.client_user,
            content="Bonjour assistant, avez-vous des motos disponibles ?",
        )
        res = notifier_nouveau_message_support_task(message.pk)
        self.assertEqual(res, "notified_1_assistants")
        mock_push_delay.assert_called_once()
        call_kwargs = mock_push_delay.call_args.kwargs
        self.assertEqual(call_kwargs["user_id"], self.assistant_user.pk)
        self.assertIn("Bonjour assistant", call_kwargs["body"])

    @patch("notifications_app.tasks.envoyer_notification_webpush_task.delay")
    def test_notifier_nouveau_message_support_from_assistant(self, mock_push_delay):
        message = SupportMessage.objects.create(
            conversation=self.conversation,
            sender=self.assistant_user,
            content="Oui nous sommes prêts à Tampouy.",
        )
        res = notifier_nouveau_message_support_task(message.pk)
        self.assertEqual(res, "notified_client")
        mock_push_delay.assert_called_once()
        call_kwargs = mock_push_delay.call_args.kwargs
        self.assertEqual(call_kwargs["user_id"], self.client_user.pk)
        self.assertIn("Oui nous sommes prêts", call_kwargs["body"])

    @patch("notifications_app.tasks.envoyer_notification_webpush_task.delay")
    def test_notifier_acceptation_demande_livraison(self, mock_push_delay):
        zone = Zone.objects.create(
            nom="Zone de livraison",
            code="ZONE-PUSH",
            bloc=self.bloc,
        )
        livreur_user = User.objects.create_user(
            username="livreur_push",
            telephone="+22670000005",
            password="test-password",
            first_name="Moussa",
            last_name="Ouédraogo",
            role="livreur",
        )
        livreur = Livreur.objects.create(
            user=livreur_user,
            type_vehicule="moto",
            blocs=self.bloc,
        )
        demande = DemandeLivraison.objects.create(
            client=self.client_profile,
            livreur=livreur,
            zone_depart=zone,
            zone_arrivee=zone,
            latitude_depart="12.345678",
            longitude_depart="-1.234567",
            prix=1000,
            whatsapp_destinataire="+22670000006",
            statut="acceptee",
        )

        result = notifier_acceptation_demande_livraison_task(demande.pk)

        self.assertEqual(result, "notified_client")
        mock_push_delay.assert_called_once_with(
            user_id=self.client_user.pk,
            title="Votre demande de livraison a été acceptée",
            body=f"Moussa Ouédraogo a accepté votre demande de livraison #{demande.pk}.",
            target_url=reverse("clients_app:tableau-de-bord"),
        )
