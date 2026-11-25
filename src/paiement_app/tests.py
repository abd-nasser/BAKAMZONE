from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from blocs_app.models import Blocs
from clients_app.models import Client
from demande_livraison_app.models import DemandeLivraison
from zones_app.models import Zone
from .models import PaiementLivraisonLigdiCash
from .services_livraison import confirmer_paiement_ligdicash_livraison

User = get_user_model()


@override_settings(
    LIGDICASH_API_KEY="test-key",
    LIGDICASH_AUTH_TOKEN="test-token",
    LIGDICASH_PLATFORM="test",
    LIGDICASH_CALLBACK_URL_LIVRAISON="https://bakamzone.example/paiement/callback/livraison/",
)
class PaiementLivraisonLigdiCashTests(TestCase):
    def setUp(self):
        self.bloc = Blocs.objects.create(nom="Bloc Paiement Livraison")
        self.zone_depart = Zone.objects.create(
            nom="Zone Depart",
            code="ZD-PAY",
            bloc=self.bloc,
        )
        self.zone_arrivee = Zone.objects.create(
            nom="Zone Arrivee",
            code="ZA-PAY",
            bloc=self.bloc,
        )
        self.client_user = User.objects.create_user(
            username="client_pay_liv",
            telephone="+22670001001",
            password="password123",
            first_name="Awa",
            last_name="Kone",
            role="client",
        )
        self.client_profile = Client.objects.create(user=self.client_user)

        self.autre_user = User.objects.create_user(
            username="autre_client_pay_liv",
            telephone="+22670001002",
            password="password123",
            role="client",
        )
        Client.objects.create(user=self.autre_user)

        self.demande = DemandeLivraison.objects.create(
            client=self.client_profile,
            zone_depart=self.zone_depart,
            zone_arrivee=self.zone_arrivee,
            latitude_depart=Decimal("12.345678"),
            longitude_depart=Decimal("-1.234567"),
            prix=Decimal("1500"),
            whatsapp_destinataire="+22670009999",
            statut="acceptee",
            position_destinataire_validee=True,
            latitude_destinataire_reelle=Decimal("12.350000"),
            longitude_destinataire_reelle=Decimal("-1.240000"),
            statut_position_destinataire="position_recue",
        )
        self.initier_url = reverse(
            "paiement_app:initier_livraison",
            kwargs={"reference": self.demande.reference},
        )
        self.statut_url = reverse(
            "paiement_app:statut_livraison",
            kwargs={"reference": self.demande.reference},
        )
        self.callback_url = reverse("paiement_app:callback_livraison")

    def test_demande_livraison_has_unique_uuid_reference(self):
        autre_demande = DemandeLivraison.objects.create(
            client=self.client_profile,
            zone_depart=self.zone_depart,
            zone_arrivee=self.zone_arrivee,
            latitude_depart=Decimal("12.345678"),
            longitude_depart=Decimal("-1.234567"),
            prix=Decimal("1000"),
            whatsapp_destinataire="+22670008888",
        )
        self.assertIsNotNone(self.demande.reference)
        self.assertNotEqual(self.demande.reference, autre_demande.reference)

    def test_initier_get_requires_validated_recipient_position(self):
        self.demande.position_destinataire_validee = False
        self.demande.save(update_fields=["position_destinataire_validee"])

        self.client.force_login(self.client_user)
        response = self.client.get(self.initier_url)
        self.assertRedirects(response, reverse("clients_app:tableau-de-bord"))

    def test_initier_get_denies_other_client(self):
        self.client.force_login(self.autre_user)
        response = self.client.get(self.initier_url)
        self.assertEqual(response.status_code, 404)

    @patch("paiement_app.services_livraison.ligdicash.Invoice")
    def test_initier_post_success_creates_payment_and_returns_hx_trigger(self, mock_invoice_cls):
        mock_invoice = MagicMock()
        mock_invoice.pay_without_redirection.return_value = SimpleNamespace(
            response_code="00",
            token="tok_create_123",
            response_text="Transaction initiée",
        )
        mock_invoice_cls.return_value = mock_invoice

        self.client.force_login(self.client_user)
        response = self.client.post(
            self.initier_url,
            {
                "operateur": "ORANGE",
                "numero_client": "+226 70 00 10 01",
                "otp": "123456",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Trigger"], "close_and_reload")

        paiement = PaiementLivraisonLigdiCash.objects.get(demande_livraison=self.demande)
        self.assertEqual(paiement.numero_client, "22670001001")
        self.assertEqual(paiement.operateur, "ORANGE")
        self.assertEqual(paiement.montant, Decimal("1500.00"))
        self.assertEqual(paiement.token_creation, "tok_create_123")
        self.assertEqual(paiement.statut, PaiementLivraisonLigdiCash.STATUT_EN_ATTENTE)

        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut_paiement, DemandeLivraison.PAIEMENT_EN_ATTENTE)

        mock_invoice.add_item.assert_called_once()
        self.assertEqual(mock_invoice.external_id, "")
        call_kwargs = mock_invoice.pay_without_redirection.call_args.kwargs
        self.assertEqual(call_kwargs["otp"], "123456")
        self.assertEqual(call_kwargs["customer"], "22670001001")
        self.assertEqual(
            call_kwargs["callback_url"],
            "https://bakamzone.example/paiement/callback/livraison/",
        )
        self.assertEqual(
            call_kwargs["custom_data"]["demande_livraison_reference"],
            str(self.demande.reference),
        )

    @patch("paiement_app.services_livraison.ligdicash.Invoice")
    def test_initier_post_operator_refusal_returns_error_without_reload(self, mock_invoice_cls):
        mock_invoice = MagicMock()
        mock_invoice.pay_without_redirection.return_value = SimpleNamespace(
            response_code="01",
            token="",
            response_text="Solde insuffisant",
        )
        mock_invoice_cls.return_value = mock_invoice

        self.client.force_login(self.client_user)
        response = self.client.post(
            self.initier_url,
            {"operateur": "ORANGE", "numero_client": "22670001001"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("HX-Trigger", response)
        self.assertContains(response, "Solde insuffisant")

        paiement = PaiementLivraisonLigdiCash.objects.get(demande_livraison=self.demande)
        self.assertEqual(paiement.statut, PaiementLivraisonLigdiCash.STATUT_ECHOUE)
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut_paiement, DemandeLivraison.PAIEMENT_ECHOUE)

    @patch("paiement_app.services_livraison.ligdicash.get_transaction")
    def test_confirmer_paiement_completed_is_idempotent(self, mock_get_tx):
        paiement = PaiementLivraisonLigdiCash.objects.create(
            demande_livraison=self.demande,
            montant=Decimal("1500.00"),
            numero_client="22670001001",
            operateur="ORANGE",
            token_creation="tok_create_ok",
        )
        mock_get_tx.return_value = SimpleNamespace(status="completed")

        res1 = confirmer_paiement_ligdicash_livraison(
            paiement.id,
            token_callback="tok_cb_1",
            payload_cb={"status": "completed"},
        )
        self.assertEqual(res1.statut, PaiementLivraisonLigdiCash.STATUT_REUSSI)
        self.assertIsNotNone(res1.date_paiement)
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut_paiement, DemandeLivraison.PAIEMENT_REUSSI)
        self.assertEqual(self.demande.date_paiement, res1.date_paiement)

        # Second callback does not re-query LigdiCash or mutate date_paiement
        mock_get_tx.reset_mock()
        res2 = confirmer_paiement_ligdicash_livraison(
            paiement.id,
            token_callback="tok_cb_2",
            payload_cb={"status": "completed", "replay": True},
        )
        mock_get_tx.assert_not_called()
        self.assertEqual(res2.statut, PaiementLivraisonLigdiCash.STATUT_REUSSI)
        self.assertEqual(res2.token_callback, "tok_cb_2")

    @patch("paiement_app.services_livraison.ligdicash.get_transaction")
    def test_confirmer_paiement_failed_does_not_mark_demande_paid(self, mock_get_tx):
        paiement = PaiementLivraisonLigdiCash.objects.create(
            demande_livraison=self.demande,
            montant=Decimal("1500.00"),
            numero_client="22670001001",
            operateur="ORANGE",
            token_creation="tok_create_fail",
        )
        mock_get_tx.return_value = SimpleNamespace(status="failed")

        res = confirmer_paiement_ligdicash_livraison(paiement.id, token_callback="tok_cb_fail")
        self.assertEqual(res.statut, PaiementLivraisonLigdiCash.STATUT_ECHOUE)
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut_paiement, DemandeLivraison.PAIEMENT_ECHOUE)
        self.assertIsNone(self.demande.date_paiement)

    @patch("paiement_app.services_livraison.ligdicash.get_transaction")
    def test_callback_view_verifies_via_token_creation_and_returns_200(self, mock_get_tx):
        paiement = PaiementLivraisonLigdiCash.objects.create(
            demande_livraison=self.demande,
            montant=Decimal("1500.00"),
            numero_client="22670001001",
            operateur="ORANGE",
            token_creation="tok_create_cb",
        )
        mock_get_tx.return_value = SimpleNamespace(status="paid")

        response = self.client.post(
            self.callback_url,
            data={
                "token": "tok_webhook_different",
                "custom_data": {
                    "type": "livraison",
                    "paiement_livraison_ref": str(paiement.reference),
                },
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["statut_paiement"], "reussi")
        mock_get_tx.assert_called_once_with(token="tok_create_cb")

    def test_callback_view_empty_or_unknown_returns_error_status(self):
        res_empty = self.client.post(self.callback_url, data={}, content_type="application/json")
        self.assertEqual(res_empty.status_code, 400)

        res_unknown = self.client.post(
            self.callback_url,
            data={"token": "inexistant"},
            content_type="application/json",
        )
        self.assertEqual(res_unknown.status_code, 404)

    @patch("paiement_app.services_livraison.ligdicash.get_transaction")
    def test_statut_view_renders_for_owner_and_denies_other_user(self, mock_get_tx):
        PaiementLivraisonLigdiCash.objects.create(
            demande_livraison=self.demande,
            montant=Decimal("1500.00"),
            numero_client="22670001001",
            operateur="ORANGE",
            token_creation="tok_statut_1",
        )
        mock_get_tx.return_value = SimpleNamespace(status="completed")

        self.client.force_login(self.autre_user)
        forbidden_resp = self.client.get(self.statut_url)
        self.assertEqual(forbidden_resp.status_code, 404)

        self.client.force_login(self.client_user)
        resp = self.client.get(self.statut_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Paiement confirmé")

        json_resp = self.client.get(f"{self.statut_url}?format=json")
        self.assertEqual(json_resp.status_code, 200)
        self.assertTrue(json_resp.json()["est_payee"])
