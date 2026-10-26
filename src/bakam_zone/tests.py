from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from bakam_zone.tasks import send_email_task, send_whatsapp_notification_task


class SendEmailTaskTests(SimpleTestCase):
    @patch("bakam_zone.tasks.django_send_mail", return_value=1)
    @override_settings(DEFAULT_FROM_EMAIL="noreply@example.com")
    def test_sends_email_using_default_sender(self, send_mail):
        sent_count = send_email_task.run(
            subject="Sujet",
            plain_message="Message texte",
            recipient_list=["client@example.com"],
            html_message="<p>Message HTML</p>",
        )

        self.assertEqual(sent_count, 1)
        send_mail.assert_called_once_with(
            subject="Sujet",
            message="Message texte",
            from_email="noreply@example.com",
            recipient_list=["client@example.com"],
            html_message="<p>Message HTML</p>",
            fail_silently=False,
        )

    def test_rejects_empty_recipient_list(self):
        with self.assertRaisesMessage(ValueError, "Au moins un destinataire"):
            send_email_task.run(
                subject="Sujet",
                plain_message="Message",
                recipient_list=[],
            )

    @override_settings(DEFAULT_FROM_EMAIL="")
    def test_requires_a_configured_sender(self):
        with self.assertRaisesMessage(ValueError, "Configurez DEFAULT_FROM_EMAIL"):
            send_email_task.run(
                subject="Sujet",
                plain_message="Message",
                recipient_list=["client@example.com"],
            )


class SendWhatsAppNotificationTaskTests(SimpleTestCase):
    @override_settings(
        WHATSAPP_PHONE_NUMBER_ID="phone-id",
        WHATSAPP_ACCESS_TOKEN="access-token",
        WHATSAPP_API_VERSION="v22.0",
        WHATSAPP_API_TIMEOUT=10,
    )
    @patch("bakam_zone.tasks.requests.post")
    def test_sends_text_message_and_returns_meta_message_id(self, post):
        post.return_value.status_code = 200
        post.return_value.json.return_value = {
            "messages": [{"id": "wamid.example"}]
        }

        message_id = send_whatsapp_notification_task.run(
            recipient_phone="+22670000000",
            message="Bonjour",
        )

        self.assertEqual(message_id, "wamid.example")
        post.assert_called_once_with(
            "https://graph.facebook.com/v22.0/phone-id/messages",
            headers={"Authorization": "Bearer access-token"},
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": "+22670000000",
                "type": "text",
                "text": {"body": "Bonjour"},
            },
            timeout=10,
        )

    @override_settings(WHATSAPP_PHONE_NUMBER_ID="", WHATSAPP_ACCESS_TOKEN="")
    @patch("bakam_zone.tasks.requests.post")
    def test_requires_api_credentials(self, post):
        with self.assertRaisesMessage(ImproperlyConfigured, "WHATSAPP_PHONE_NUMBER_ID"):
            send_whatsapp_notification_task.run(
                recipient_phone="+22670000000",
                message="Bonjour",
            )

        post.assert_not_called()

    @override_settings(
        WHATSAPP_PHONE_NUMBER_ID="phone-id",
        WHATSAPP_ACCESS_TOKEN="access-token",
    )
    @patch("bakam_zone.tasks.requests.post")
    def test_rejects_empty_message(self, post):
        with self.assertRaisesMessage(ValueError, "ne peut pas être vide"):
            send_whatsapp_notification_task.run(
                recipient_phone="+22670000000",
                message=" ",
            )

        post.assert_not_called()
