from django.test import TestCase
from django.urls import reverse

from auth_app.models import User
from clients_app.forms import InscriptionClientForm
from clients_app.models import Client


class InscriptionClientViewTests(TestCase):
    def setUp(self):
        self.form_data = {
            'username': 'aminata_d',
            'first_name': 'Aminata',
            'last_name': 'Diallo',
            'telephone': '70000123',
            'email': 'aminata@example.com',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'ville': 'Ouagadougou',
            'quartier': 'Tampouy',
        }

    def test_registration_page_renders_form_fields(self):
        response = self.client.get(reverse('clients_app:inscription-client'))

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], InscriptionClientForm)
        for field_name in (
            'username',
            'first_name',
            'last_name',
            'telephone',
            'email',
            'password',
            'confirm_password',
            'photo_profil',
            'ville',
            'quartier',
        ):
            self.assertContains(response, f'name="{field_name}"')
        self.assertContains(response, 'showPassword = !showPassword')
        self.assertContains(response, 'showConfirmPassword = !showConfirmPassword')
        self.assertContains(response, 'file-input-primary')
        self.assertContains(response, 'Aperçu de la photo de profil')

    def test_registration_creates_client_and_redirects_home(self):
        response = self.client.post(
            reverse('clients_app:inscription-client'),
            self.form_data,
        )

        self.assertRedirects(response, reverse('home_app:home'))
        user = User.objects.get(telephone=self.form_data['telephone'])
        client = Client.objects.get(user=user)
        self.assertEqual(user.role, 'client')
        self.assertEqual(user.username, self.form_data['username'])
        self.assertTrue(user.check_password(self.form_data['password']))
        self.assertEqual(client.ville, 'Ouagadougou')
        self.assertEqual(client.quartier, 'Tampouy')

    def test_mismatched_passwords_show_form_error_without_creating_user(self):
        response = self.client.post(
            reverse('clients_app:inscription-client'),
            {
                **self.form_data,
                'confirm_password': 'DifferentPassword456!',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Les mots de passe ne correspondent pas.')
        self.assertFalse(User.objects.filter(telephone=self.form_data['telephone']).exists())

    def test_homepage_has_client_registration_link_for_visitors(self):
        response = self.client.get(reverse('home_app:home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse('clients_app:inscription-client'),
        )
        self.assertContains(response, 'aria-label="Navigation principale"')
        self.assertContains(response, 'Créer un compte client')

    def test_client_registration_page_has_shared_navigation(self):
        response = self.client.get(reverse('clients_app:inscription-client'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Navigation principale"')
        self.assertContains(response, 'BAKAMZONE')

# Create your tests here.
