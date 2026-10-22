from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from auth_app.models import User
from entreprise_app.forms import InscriptionEntrepriseForm
from entreprise_app.models import Entreprise


class InscriptionEntrepriseViewTests(TestCase):
    def setUp(self):
        self.form_data = {
            "nom_entreprise": "Livraison Faso",
            "rc_number": "BF-123456",
            "address": "Ouagadougou, Burkina Faso",
            "first_name": "Aminata",
            "last_name": "Diallo",
            "telephone": "70000222",
            "email": "aminata@livraison-faso.test",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        }

    def test_registration_page_renders_fields_without_palier(self):
        response = self.client.get(reverse("entreprise_app:inscription"))

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context["form"], InscriptionEntrepriseForm)
        for field_name in (
            "nom_entreprise",
            "logo",
            "rc_number",
            "address",
            "first_name",
            "last_name",
            "telephone",
            "email",
            "password",
            "password_confirm",
        ):
            self.assertContains(response, f'name="{field_name}"')
        self.assertNotContains(response, 'name="palier"')
        self.assertContains(response, "showPasswordConfirm")
        self.assertContains(response, "logoPreview")
        self.assertContains(response, 'hx-indicator="#entreprise-register-spinner"')

    def test_registration_creates_enterprise_account_without_assigning_tier(self):
        response = self.client.post(
            reverse("entreprise_app:inscription"),
            self.form_data,
        )

        self.assertRedirects(response, reverse("home_app:home"))
        user = User.objects.get(telephone=self.form_data["telephone"])
        entreprise = Entreprise.objects.get(user_principal=user)
        self.assertEqual(user.role, "entreprise")
        self.assertEqual(user.first_name, "Aminata")
        self.assertTrue(user.check_password(self.form_data["password"]))
        self.assertEqual(entreprise.palier, "pas_defini")
        self.assertFalse(entreprise.subscription_active)

    def test_mismatched_passwords_do_not_create_an_account(self):
        response = self.client.post(
            reverse("entreprise_app:inscription"),
            {**self.form_data, "password_confirm": "OtherPassword123!"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Les mots de passe ne correspondent pas.")
        self.assertFalse(User.objects.filter(telephone=self.form_data["telephone"]).exists())

    def test_existing_telephone_is_reported_on_telephone_field(self):
        User.objects.create_user(
            telephone=self.form_data["telephone"],
            password="ExistingPassword123!",
            first_name="Existing",
            last_name="User",
        )

        response = self.client.post(
            reverse("entreprise_app:inscription"),
            self.form_data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("telephone", response.context["form"].errors)
        self.assertContains(response, "Ce numéro de téléphone est déjà utilisé.")
        self.assertEqual(User.objects.filter(telephone=self.form_data["telephone"]).count(), 1)

    def test_integrity_error_for_duplicate_telephone_returns_form_error(self):
        def create_competing_user(*args, **kwargs):
            User.objects.create_user(
                telephone=self.form_data["telephone"],
                password="ExistingPassword123!",
                first_name="Existing",
                last_name="User",
            )
            raise IntegrityError("duplicate telephone")

        with patch(
            "entreprise_app.forms.InscriptionEntrepriseForm.save",
            side_effect=create_competing_user,
        ):
            response = self.client.post(
                reverse("entreprise_app:inscription"),
                self.form_data,
                HTTP_HX_REQUEST="true",
            )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "partials/result/entreprise_error.html",
        )
        self.assertContains(response, "Veuillez en choisir un autre.")

    def test_htmx_registration_returns_success_partial(self):
        response = self.client.post(
            reverse("entreprise_app:inscription"),
            self.form_data,
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["HX-Trigger"],
            "entreprise-register-success",
        )
        self.assertTemplateUsed(
            response,
            "partials/result/entreprise_success.html",
        )

    def test_htmx_duplicate_telephone_returns_error_partial(self):
        User.objects.create_user(
            telephone=self.form_data["telephone"],
            password="ExistingPassword123!",
            first_name="Existing",
            last_name="User",
        )

        response = self.client.post(
            reverse("entreprise_app:inscription"),
            self.form_data,
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "partials/result/entreprise_error.html",
        )
        self.assertContains(response, "Ce numéro de téléphone est déjà utilisé.")


class ChoixPalierEntrepriseViewTests(TestCase):
    def setUp(self):
        self.user = User(
            telephone="70000333",
            first_name="Issa",
            last_name="Traoré",
            role="entreprise",
        )
        self.user.set_password("StrongPassword123!")
        self.user.save()
        self.entreprise = Entreprise.objects.create(
            user_principal=self.user,
            nom_entreprise="Entreprise Faso",
            address="Ouagadougou",
        )

    def test_anonymous_user_is_redirected_from_tier_selection(self):
        response = self.client.get(reverse("entreprise_app:choix-palier"))

        self.assertRedirects(response, reverse("home_app:home"))

    def test_enterprise_user_can_choose_tier_without_activating_subscription(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("entreprise_app:choix-palier"),
            {"palier": "pro"},
        )

        self.assertRedirects(response, reverse("home_app:home"))
        self.entreprise.refresh_from_db()
        self.assertEqual(self.entreprise.palier, "pro")
        self.assertFalse(self.entreprise.subscription_active)

    def test_unrelated_user_cannot_change_enterprise_tier(self):
        unrelated_user = User(
            telephone="70000444",
            first_name="Mariam",
            last_name="Sawadogo",
            role="client",
        )
        unrelated_user.set_password("StrongPassword123!")
        unrelated_user.save()
        self.client.force_login(unrelated_user)

        response = self.client.post(
            reverse("entreprise_app:choix-palier"),
            {"palier": "premium"},
        )

        self.assertRedirects(response, reverse("home_app:home"))
        self.entreprise.refresh_from_db()
        self.assertEqual(self.entreprise.palier, "pas_defini")

    def test_undefined_tier_is_rejected(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("entreprise_app:choix-palier"),
            {"palier": "pas_defini"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sélectionnez un choix valide")
        self.entreprise.refresh_from_db()
        self.assertEqual(self.entreprise.palier, "pas_defini")
