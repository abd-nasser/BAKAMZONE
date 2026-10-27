from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from kombu.exceptions import OperationalError as CeleryOperationalError

from auth_app.models import User
from blocs_app.models import Blocs
from clients_app.models import Client
from demande_livraison_app.models import DemandeLivraison
from livreurs_app.forms import InscriptionLivreurForm
from livreurs_app.models import Livreur
from zones_app.models import Zone


class InscriptionLivreurFormTests(TestCase):
    def setUp(self):
        self.bloc = Blocs.objects.create(nom='Bloc de test')
        self.zone = Zone.objects.create(
            nom='Zone de test',
            code='Z-TEST',
            bloc=self.bloc,
        )
        self.form_data = {
            'first_name': 'Aminata',
            'last_name': 'Diallo',
            'telephone': '70000001',
            'email': 'aminata@example.com',
            'type_vehicule': 'moto',
            'blocs': str(self.bloc.pk),
            'zone_actuelle': str(self.zone.pk),
        }

    def login_superuser(self):
        admin = User.objects.create_user(
            telephone='70000999',
            password='admin-password',
            username='test-admin',
            first_name='Admin',
            last_name='Test',
            is_superuser=True,
            is_staff=True,
        )
        self.client.force_login(admin)
        return admin

    def test_creates_livreur_with_uuid_credentials(self):
        form = InscriptionLivreurForm(data=self.form_data)

        self.assertTrue(form.is_valid(), form.errors)
        livreur = form.save()
        user = livreur.user

        self.assertEqual(user.role, 'livreur')
        self.assertEqual(user.telephone, self.form_data['telephone'])
        self.assertEqual(user.username, form.generated_username)
        self.assertEqual(len(user.username), 30)
        self.assertRegex(user.username, r'^[0-9a-f]{30}$')
        self.assertEqual(len(form.generated_password), 32)
        self.assertRegex(form.generated_password, r'^[0-9a-f]{32}$')
        self.assertTrue(user.check_password(form.generated_password))
        self.assertEqual(livreur.type_vehicule, 'moto')
        self.assertEqual(livreur.blocs, self.bloc)
        self.assertEqual(livreur.zone_actuelle, self.zone)

    def test_rejects_an_existing_telephone(self):
        User.objects.create_user(
            telephone=self.form_data['telephone'],
            password='existing-password',
            username='existing-user',
            first_name='Existing',
            last_name='User',
        )
        form = InscriptionLivreurForm(data=self.form_data)

        self.assertFalse(form.is_valid())
        self.assertIn('telephone', form.errors)

    def test_registration_page_displays_the_form(self):
        self.login_superuser()
        response = self.client.get(reverse('livreurs_app:inscription-livreur'))

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], InscriptionLivreurForm)
        self.assertContains(response, 'name="first_name"')
        self.assertContains(response, 'name="last_name"')
        self.assertContains(response, 'name="telephone"')
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="type_vehicule"')
        self.assertContains(response, 'name="blocs"')
        self.assertContains(response, 'name="zone_actuelle"')
        for field_name in (
            'photo_profil',
            'photo_cni_recto',
            'photo_cni_verso',
            'photo_selfie',
        ):
            self.assertContains(response, f'name="{field_name}"')
        self.assertNotContains(response, 'name="username"')
        self.assertNotContains(response, 'name="password"')
        self.assertNotContains(response, 'name="confirm_password"')

    def test_htmx_registration_returns_generated_credentials(self):
        self.login_superuser()
        response = self.client.post(
            reverse('livreurs_app:inscription-livreur'),
            self.form_data,
            HTTP_HX_REQUEST='true',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['HX-Trigger'], 'livreur-register-success')
        user = User.objects.get(telephone=self.form_data['telephone'])
        self.assertContains(response, user.username)
        self.assertTrue(user.check_password(response.context['password']))
        livreur = user.livreur_profil
        self.assertEqual(livreur.blocs, self.bloc)
        self.assertEqual(livreur.zone_actuelle, self.zone)

    def test_regular_registration_displays_credentials_once(self):
        self.login_superuser()
        response = self.client.post(
            reverse('livreurs_app:inscription-livreur'),
            self.form_data,
        )

        self.assertEqual(response.status_code, 200)
        user = User.objects.get(telephone=self.form_data['telephone'])
        self.assertContains(response, user.username)
        self.assertTrue(
            user.check_password(response.context['registration_success']['password'])
        )
        self.assertContains(response, user.get_full_name())
        self.assertContains(response, self.bloc.nom)
        self.assertContains(response, 'Admin Test')
        self.assertNotContains(response, 'name="telephone"')

    def test_htmx_registration_returns_form_errors(self):
        self.login_superuser()
        User.objects.create_user(
            telephone=self.form_data['telephone'],
            password='existing-password',
            username='existing-user',
            first_name='Existing',
            last_name='User',
        )

        response = self.client.post(
            reverse('livreurs_app:inscription-livreur'),
            self.form_data,
            HTTP_HX_REQUEST='true',
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ce numéro de téléphone est déjà utilisé.')

    def test_registration_requires_superuser(self):
        response = self.client.get(reverse('livreurs_app:inscription-livreur'))
        self.assertEqual(response.status_code, 302)

        regular_user = User.objects.create_user(
            telephone='70000998',
            password='user-password',
            username='regular-user',
            first_name='Regular',
            last_name='User',
        )
        self.client.force_login(regular_user)
        response = self.client.get(reverse('livreurs_app:inscription-livreur'))

        self.assertEqual(response.status_code, 403)

    def test_rejects_inactive_assignment_block(self):
        inactive_bloc = Blocs.objects.create(nom='Bloc inactif', actif=False)
        form_data = {
            **self.form_data,
            'telephone': '70000002',
            'blocs': str(inactive_bloc.pk),
        }
        form = InscriptionLivreurForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn('blocs', form.errors)

    def test_rejects_zone_from_different_block(self):
        another_bloc = Blocs.objects.create(nom='Autre bloc')
        another_zone = Zone.objects.create(
            nom='Autre zone',
            bloc=another_bloc,
        )
        form = InscriptionLivreurForm(data={
            **self.form_data,
            'zone_actuelle': str(another_zone.pk),
        })

        self.assertFalse(form.is_valid())
        self.assertIn('zone_actuelle', form.errors)

    def test_zone_actuelle_is_optional(self):
        form = InscriptionLivreurForm(data={
            **self.form_data,
            'zone_actuelle': '',
        })

        self.assertTrue(form.is_valid(), form.errors)

    def test_zone_queryset_contains_zones_not_blocs(self):
        form = InscriptionLivreurForm()

        self.assertIn(self.zone, form.fields['zone_actuelle'].queryset)
        self.assertNotIn(self.bloc, form.fields['zone_actuelle'].queryset)


class LivreurDeliveryWorkflowTests(TestCase):
    def setUp(self):
        self.bloc = Blocs.objects.create(nom='Bloc de livraison')
        self.zone = Zone.objects.create(nom='Zone de livraison', bloc=self.bloc)
        client_user = User.objects.create_user(
            telephone='70000101',
            password='client-password',
            username='client-test',
            first_name='Client',
            last_name='Test',
            role='client',
        )
        self.client_profile = Client.objects.create(user=client_user)
        livreur_user = User.objects.create_user(
            telephone='70000102',
            password='livreur-password',
            username='livreur-test',
            first_name='Livreur',
            last_name='Test',
            role='livreur',
        )
        self.livreur = Livreur.objects.create(
            user=livreur_user,
            type_vehicule='moto',
            blocs=self.bloc,
        )
        self.client.force_login(livreur_user)
        self.demande = DemandeLivraison.objects.create(
            client=self.client_profile,
            zone_depart=self.zone,
            zone_arrivee=self.zone,
            latitude_depart=Decimal('12.345678'),
            longitude_depart=Decimal('-1.234567'),
            prix=Decimal('1000'),
            whatsapp_destinataire='+22670000000',
        )

    def test_dashboard_shows_same_block_requests_and_actions(self):
        response = self.client.get(reverse('livreurs_app:tableau-de-bord'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Course #{self.demande.pk}')
        self.assertContains(
            response,
            reverse('livreurs_app:accepter-demande', args=[self.demande.pk]),
        )

    @patch('livreurs_app.views.envoyer_notification_smartdrop_destinataire_task.delay')
    def test_accepting_same_block_request_sends_smartdrop_task(self, send_notification):
        response = self.client.post(
            reverse('livreurs_app:accepter-demande', args=[self.demande.pk]),
        )

        self.assertRedirects(response, reverse('livreurs_app:tableau-de-bord'))
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.livreur, self.livreur)
        self.assertEqual(self.demande.statut, 'acceptee')
        self.assertIsNotNone(self.demande.date_acceptation)
        send_notification.assert_called_once_with(
            self.demande.pk,
            base_url='http://testserver',
        )

    @patch('livreurs_app.views.envoyer_notification_smartdrop_destinataire_task.delay')
    def test_cannot_accept_request_from_another_block(self, send_notification):
        other_block = Blocs.objects.create(nom='Autre bloc')
        other_zone = Zone.objects.create(nom='Autre zone', bloc=other_block)
        self.demande.zone_depart = other_zone
        self.demande.save(update_fields=['zone_depart'])

        response = self.client.post(
            reverse('livreurs_app:accepter-demande', args=[self.demande.pk]),
        )

        self.assertRedirects(response, reverse('livreurs_app:tableau-de-bord'))
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut, 'en_attente')
        self.assertIsNone(self.demande.livreur)
        send_notification.assert_not_called()

    @patch(
        'livreurs_app.views.envoyer_notification_smartdrop_destinataire_task.delay',
        side_effect=CeleryOperationalError('broker unavailable'),
    )
    def test_reports_when_smartdrop_notification_cannot_be_queued(self, send_notification):
        response = self.client.post(
            reverse('livreurs_app:accepter-demande', args=[self.demande.pk]),
            follow=True,
        )

        self.assertContains(response, "notification WhatsApp")
        self.assertContains(response, "assistance")
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.livreur, self.livreur)
        self.assertEqual(self.demande.statut, 'acceptee')
        send_notification.assert_called_once()

    def test_refusing_direct_request_releases_it_to_the_block(self):
        self.demande.livreur = self.livreur
        self.demande.save(update_fields=['livreur'])

        response = self.client.post(
            reverse('livreurs_app:refuser-demande', args=[self.demande.pk]),
        )

        self.assertRedirects(response, reverse('livreurs_app:tableau-de-bord'))
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut, 'en_attente')
        self.assertIsNone(self.demande.livreur)
