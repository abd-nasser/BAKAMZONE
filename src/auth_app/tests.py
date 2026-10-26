from django.test import TestCase
from django.urls import reverse

from auth_app.forms import ChangeCredentialForm
from auth_app.models import User
from admins_app.models import AdminBloc
from blocs_app.models import Blocs


class ChangeCredentialFormTests(TestCase):
    def setUp(self):
        self.user = User(
            username="existing-user",
            telephone="70000111",
            first_name="Aminata",
            last_name="Diallo",
        )
        self.user.set_password("CurrentPassword123!")
        self.user.save()
        self.form_data = {
            "username": "updated-user",
            "telephone": "70000112",
            "old_password": "CurrentPassword123!",
            "new_password": "",
            "new_password_confirm": "",
        }

    def test_changes_username_and_telephone(self):
        form = ChangeCredentialForm(data=self.form_data, user=self.user)

        self.assertTrue(form.is_valid(), form.errors)
        updated_user = form.save()

        self.assertEqual(updated_user.username, "updated-user")
        self.assertEqual(updated_user.telephone, "70000112")
        self.assertTrue(updated_user.check_password("CurrentPassword123!"))

    def test_changes_password_when_confirmation_matches(self):
        form = ChangeCredentialForm(
            data={
                **self.form_data,
                "username": "existing-user",
                "telephone": "70000111",
                "new_password": "NewPassword456!",
                "new_password_confirm": "NewPassword456!",
            },
            user=self.user,
        )

        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword456!"))

    def test_rejects_incorrect_current_password(self):
        form = ChangeCredentialForm(
            data={**self.form_data, "old_password": "incorrect"},
            user=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("old_password", form.errors)

    def test_rejects_telephone_used_by_another_user(self):
        User.objects.create(
            username="other-user",
            telephone="70000112",
            first_name="Other",
            last_name="User",
        )
        form = ChangeCredentialForm(data=self.form_data, user=self.user)

        self.assertFalse(form.is_valid())
        self.assertIn("telephone", form.errors)


class BlockAdminLoginRedirectTests(TestCase):
    def setUp(self):
        self.bloc = Blocs.objects.create(
            nom="Bloc Karpala",
            ville="ouagadougou",
            quartier="karpala",
        )
        self.user = User.objects.create(
            telephone="70000121",
            first_name="Aminata",
            last_name="Diallo",
            role="bloc_admin",
        )
        self.user.set_password("StrongPassword123!")
        self.user.save()
        self.admin_bloc = AdminBloc.objects.create(
            user=self.user,
            bloc=self.bloc,
            poste="responsable",
        )

    def test_login_redirects_to_dashboard_for_each_active_post(self):
        dashboard_names = {
            "responsable": "tableau-de-bord-responsable",
            "gestionnaire_stock": "tableau-de-bord-stock",
            "superviseur_flotte": "tableau-de-bord-flotte",
            "assistant": "tableau-de-bord-assistant",
        }

        for poste, route_name in dashboard_names.items():
            with self.subTest(poste=poste):
                self.admin_bloc.poste = poste
                self.admin_bloc.save(update_fields=["poste"])
                response = self.client.post(
                    reverse("auth_app:connexion_htmx"),
                    {
                        "identifiant": self.user.telephone,
                        "password": "StrongPassword123!",
                    },
                    HTTP_HX_REQUEST="true",
                )

                expected_url = reverse(f"admins_app:{route_name}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["HX-Redirect"], expected_url)


class ClientLoginRedirectTests(TestCase):
    def test_client_login_redirects_to_client_dashboard(self):
        user = User.objects.create(
            telephone="70000807",
            first_name="Awa",
            last_name="Traore",
            role="client",
        )
        user.set_password("StrongPassword123!")
        user.save()

        response = self.client.post(
            reverse("auth_app:connexion_htmx"),
            {
                "identifiant": user.telephone,
                "password": "StrongPassword123!",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["HX-Redirect"],
            reverse("clients_app:tableau-de-bord"),
        )
