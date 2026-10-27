from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from blocs_app.models import Blocs
from clients_app.models import Client
from demande_livraison_app.forms import DemandeLivraisonForm
from demande_livraison_app.models import DemandeLivraison
from demande_livraison_app.pricing import calculer_tarif_livraison
from zones_app.models import Zone

User = get_user_model()


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
        self.url = reverse(
            "destinataire-geo",
            kwargs={"token_pwa_destinataire": self.demande.token_pwa_destinataire},
        )

    def test_recipient_can_submit_valid_coordinates(self):
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
        self.assertEqual(self.demande.statut_destinataire, "position_recue")

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
