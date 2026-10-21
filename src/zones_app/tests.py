from django.test import TestCase
from django.urls import reverse

from auth_app.models import User
from blocs_app.models import Blocs
from zones_app.forms import ZoneForm
from zones_app.models import Zone


class ZoneCreationTests(TestCase):
    def setUp(self):
        self.bloc = Blocs.objects.create(nom='Bloc de test')
        self.form_data = {
            'nom': 'Secteur Nord',
            'bloc': str(self.bloc.pk),
            'latitude': '12.404200',
            'longitude': '-1.554300',
        }

    def login_superuser(self):
        admin = User.objects.create_user(
            telephone='70000888',
            password='admin-password',
            username='zone-admin',
            first_name='Admin',
            last_name='Zone',
            is_superuser=True,
            is_staff=True,
        )
        self.client.force_login(admin)

    def test_form_creates_zone_with_optional_code_and_coordinates(self):
        form = ZoneForm(data=self.form_data)

        self.assertTrue(form.is_valid(), form.errors)
        zone = form.save()

        self.assertEqual(zone.nom, 'Secteur Nord')
        self.assertEqual(zone.bloc, self.bloc)
        self.assertIsNone(zone.code)
        self.assertEqual(str(zone.latitude), '12.404200')
        self.assertEqual(str(zone.longitude), '-1.554300')

    def test_form_rejects_inactive_block(self):
        inactive_bloc = Blocs.objects.create(nom='Bloc inactif', actif=False)
        form = ZoneForm(data={
            **self.form_data,
            'bloc': str(inactive_bloc.pk),
        })

        self.assertFalse(form.is_valid())
        self.assertIn('bloc', form.errors)

    def test_form_rejects_duplicate_name_case_insensitively(self):
        Zone.objects.create(nom='Secteur Nord', bloc=self.bloc)
        form = ZoneForm(data=self.form_data)

        self.assertFalse(form.is_valid())
        self.assertIn('nom', form.errors)

    def test_get_displays_creation_form_for_superuser(self):
        self.login_superuser()
        response = self.client.get(reverse('zones_app:creer-zone'))

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], ZoneForm)
        self.assertContains(response, 'name="nom"')
        self.assertContains(response, 'name="code"')
        self.assertContains(response, 'name="bloc"')
        self.assertContains(response, 'name="latitude"')
        self.assertContains(response, 'name="longitude"')

    def test_htmx_post_creates_zone_and_returns_success_toast(self):
        self.login_superuser()
        response = self.client.post(
            reverse('zones_app:creer-zone'),
            self.form_data,
            HTTP_HX_REQUEST='true',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['HX-Trigger'], 'zoneCreated')
        self.assertContains(response, 'Secteur Nord')
        self.assertEqual(Zone.objects.get(nom='Secteur Nord').bloc, self.bloc)

    def test_regular_post_creates_zone_and_redirects_to_dashboard(self):
        self.login_superuser()
        response = self.client.post(
            reverse('zones_app:creer-zone'),
            self.form_data,
        )

        self.assertRedirects(response, reverse('superuser_app:dashboard'))
        self.assertTrue(Zone.objects.filter(nom='Secteur Nord').exists())

    def test_superuser_dashboard_links_to_zone_creation(self):
        self.login_superuser()
        response = self.client.get(reverse('superuser_app:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('zones_app:creer-zone'))

    def test_creation_requires_superuser(self):
        response = self.client.get(reverse('zones_app:creer-zone'))
        self.assertEqual(response.status_code, 302)

        user = User.objects.create_user(
            telephone='70000887',
            password='user-password',
            username='regular-user',
            first_name='Regular',
            last_name='User',
        )
        self.client.force_login(user)
        response = self.client.get(reverse('zones_app:creer-zone'))

        self.assertEqual(response.status_code, 403)
