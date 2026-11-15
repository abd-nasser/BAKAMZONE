from decimal import Decimal
from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from auth_app.models import User
from articles_app.models import Article
from blocs_app.models import Blocs
from clients_app.models import Client
from demande_livraison_app.models import DemandeLivraison
from django.utils import timezone
from entreprise_app.forms import (
    InscriptionEntrepriseForm,
    MembreAdminsEntrepriseForm,
)
from entreprise_app.models import (
    Entreprise,
    MembreAdminsEntreprise,
    RetraitEntreprise,
)
from panier_app.models import ArticlePanier, Commande, LigneCommande, Panier
from zones_app.models import Zone


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


class MembreAdminsEntrepriseFormTests(TestCase):
    def setUp(self):
        self.responsable = User.objects.create(
            telephone="70000555",
            first_name="Responsable",
            last_name="Entreprise",
            role="entreprise",
        )
        self.entreprise = Entreprise.objects.create(
            nom_entreprise="Entreprise Faso",
            address="Ouagadougou",
            user_principal=self.responsable,
        )
        self.form_data = {
            "first_name": "Admin",
            "last_name": "Employé",
            "telephone": "70000556",
            "email": "admin@entreprise.test",
        }

    def test_form_creates_employee_account_and_associates_it_to_enterprise(self):
        form = MembreAdminsEntrepriseForm(
            data=self.form_data,
            entreprise=self.entreprise,
        )

        self.assertTrue(form.is_valid(), form.errors)
        membership = form.save()

        self.assertIsInstance(membership, MembreAdminsEntreprise)
        self.assertEqual(membership.entreprise, self.entreprise)
        self.assertEqual(membership.ajoute_par, self.responsable)
        self.assertEqual(membership.membre_admin.telephone, self.form_data["telephone"])
        self.assertEqual(membership.membre_admin.role, "entreprise_admin")
        self.assertTrue(
            membership.membre_admin.check_password(form.generated_password)
        )
        self.assertEqual(membership.membre_admin.username, form.generated_username)

    def test_form_rejects_a_telephone_already_used_by_another_account(self):
        User.objects.create_user(
            telephone=self.form_data["telephone"],
            password="ExistingPassword123!",
            first_name="Existing",
            last_name="User",
        )
        form = MembreAdminsEntrepriseForm(
            data=self.form_data,
            entreprise=self.entreprise,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("telephone", form.errors)


class InscriptionEntrepriseAdminViewTests(TestCase):
    def setUp(self):
        self.responsable = User.objects.create_user(
            telephone="70000611",
            password="StrongPassword123!",
            first_name="Responsable",
            last_name="Entreprise",
            role="entreprise",
        )
        self.entreprise = Entreprise.objects.create(
            user_principal=self.responsable,
            nom_entreprise="Entreprise Faso",
            address="Ouagadougou",
            palier="pro",
        )
        self.form_data = {
            "first_name": "Admin",
            "last_name": "Employé",
            "telephone": "70000612",
            "email": "admin@entreprise.test",
        }
        self.url = reverse("entreprise_app:inscription-admin")

    def test_anonymous_user_must_log_in(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_non_enterprise_user_cannot_open_admin_registration(self):
        client_user = User.objects.create_user(
            telephone="70000613",
            password="StrongPassword123!",
            first_name="Client",
            last_name="Test",
            role="client",
        )
        self.client.force_login(client_user)

        response = self.client.get(self.url)

        self.assertRedirects(response, reverse("home_app:home"))

    def test_admin_registration_route_redirects_to_enterprise_dashboard(self):
        self.client.force_login(self.responsable)

        response = self.client.get(self.url)

        self.assertRedirects(
            response,
            reverse("entreprise_app:entreprise-detail"),
        )

    def test_enterprise_owner_can_open_dashboard(self):
        self.client.force_login(self.responsable)

        response = self.client.get(reverse("entreprise_app:entreprise-detail"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "entreprise_templates/entreprise_detail.html")
        self.assertContains(response, self.entreprise.nom_entreprise)
        self.assertContains(response, 'hx-post="/entreprises/administrateurs/inscription/"')
        self.assertContains(response, 'href="#"')
        self.assertEqual(response.context["article_count"], 0)
        self.assertEqual(response.context["admin_count"], 0)

    def test_dashboard_shows_cart_order_and_paid_quantities_per_enterprise_article(self):
        article = Article.objects.create(
            entreprise=self.entreprise,
            nom="Riz local",
            prix="1000.00",
            quantite_disponible=20,
        )
        bloc = Blocs.objects.create(nom="Bloc statistiques entreprise")
        zone = Zone.objects.create(
            nom="Zone statistiques entreprise",
            bloc=bloc,
            latitude="12.400000",
            longitude="-1.500000",
        )
        client_user = User.objects.create_user(
            telephone="70000616",
            password="StrongPassword123!",
            first_name="Client",
            last_name="Statistiques",
            role="client",
        )
        client_profile = Client.objects.create(user=client_user)
        panier_actif = Panier.objects.create(client=client_profile)
        ArticlePanier.objects.create(
            panier=panier_actif,
            article=article,
            quantite=3,
        )

        panier_paye = Panier.objects.create(
            client=client_profile,
            statut=Panier.STATUT_COMMANDE,
        )
        commande_payee = Commande.objects.create(
            panier=panier_paye,
            client=client_profile,
            zone_arrivee=zone,
            latitude_livraison=zone.latitude,
            longitude_livraison=zone.longitude,
            montant_produits="2000.00",
            total_a_payer="2000.00",
            statut_paiement=Commande.PAIEMENT_REUSSI,
        )
        LigneCommande.objects.create(
            commande=commande_payee,
            article=article,
            entreprise=self.entreprise,
            nom_article=article.nom,
            nom_entreprise=self.entreprise.nom_entreprise,
            quantite=2,
            prix_unitaire="1000.00",
        )

        panier_en_attente = Panier.objects.create(
            client=client_profile,
            statut=Panier.STATUT_COMMANDE,
        )
        commande_en_attente = Commande.objects.create(
            panier=panier_en_attente,
            client=client_profile,
            zone_arrivee=zone,
            latitude_livraison=zone.latitude,
            longitude_livraison=zone.longitude,
            montant_produits="3000.00",
            total_a_payer="3000.00",
        )
        LigneCommande.objects.create(
            commande=commande_en_attente,
            article=article,
            entreprise=self.entreprise,
            nom_article=article.nom,
            nom_entreprise=self.entreprise.nom_entreprise,
            quantite=3,
            prix_unitaire="1000.00",
        )

        self.client.force_login(self.responsable)
        response = self.client.get(reverse("entreprise_app:entreprise-detail"))

        stats = response.context["article_usage_stats"][0]
        self.assertEqual(stats["article"], article)
        self.assertEqual(stats["paniers_actifs"], 1)
        self.assertEqual(stats["quantite_panier"], 3)
        self.assertEqual(stats["paniers_commandes"], 2)
        self.assertEqual(stats["quantite_commandee"], 5)
        self.assertEqual(stats["quantite_payee"], 2)
        self.assertContains(response, "Riz local")
        self.assertContains(response, "Paniers actifs")
        self.assertContains(response, "Unités avec paiement réussi")

    def test_company_balance_uses_paid_snapshots_and_reserves_withdrawals(self):
        bloc = Blocs.objects.create(nom="Bloc solde entreprise")
        zone = Zone.objects.create(
            nom="Zone solde entreprise",
            bloc=bloc,
            latitude="12.400000",
            longitude="-1.500000",
        )
        client_user = User.objects.create_user(
            telephone="70000619",
            password="StrongPassword123!",
            first_name="Client",
            last_name="Solde",
            role="client",
        )
        client_profile = Client.objects.create(user=client_user)
        article = Article.objects.create(
            entreprise=self.entreprise,
            nom="Article vendu",
            prix="9999.00",
        )
        paid_cart = Panier.objects.create(
            client=client_profile,
            statut=Panier.STATUT_COMMANDE,
        )
        paid_order = Commande.objects.create(
            panier=paid_cart,
            client=client_profile,
            zone_arrivee=zone,
            latitude_livraison=zone.latitude,
            longitude_livraison=zone.longitude,
            montant_produits="4000.00",
            total_a_payer="4000.00",
            statut_paiement=Commande.PAIEMENT_REUSSI,
            date_paiement=timezone.now(),
        )
        LigneCommande.objects.create(
            commande=paid_order,
            article=article,
            entreprise=self.entreprise,
            nom_article="Article vendu (prix figé)",
            nom_entreprise=self.entreprise.nom_entreprise,
            quantite=2,
            prix_unitaire="2000.00",
        )

        cancelled_cart = Panier.objects.create(
            client=client_profile,
            statut=Panier.STATUT_COMMANDE,
        )
        cancelled_paid_order = Commande.objects.create(
            panier=cancelled_cart,
            client=client_profile,
            zone_arrivee=zone,
            latitude_livraison=zone.latitude,
            longitude_livraison=zone.longitude,
            montant_produits="500.00",
            total_a_payer="500.00",
            statut=Commande.STATUT_ANNULEE,
            statut_paiement=Commande.PAIEMENT_REUSSI,
            date_paiement=timezone.now(),
        )
        LigneCommande.objects.create(
            commande=cancelled_paid_order,
            article=article,
            entreprise=self.entreprise,
            nom_article="Article payé, commande annulée",
            nom_entreprise=self.entreprise.nom_entreprise,
            quantite=1,
            prix_unitaire="500.00",
        )

        unpaid_cart = Panier.objects.create(
            client=client_profile,
            statut=Panier.STATUT_COMMANDE,
        )
        unpaid_order = Commande.objects.create(
            panier=unpaid_cart,
            client=client_profile,
            zone_arrivee=zone,
            latitude_livraison=zone.latitude,
            longitude_livraison=zone.longitude,
            montant_produits="5000.00",
            total_a_payer="5000.00",
        )
        LigneCommande.objects.create(
            commande=unpaid_order,
            article=article,
            entreprise=self.entreprise,
            nom_article="Article impayé",
            nom_entreprise=self.entreprise.nom_entreprise,
            quantite=1,
            prix_unitaire="5000.00",
        )

        RetraitEntreprise.objects.create(
            entreprise=self.entreprise,
            montant="500.00",
            statut=RetraitEntreprise.STATUT_EN_ATTENTE,
        )
        RetraitEntreprise.objects.create(
            entreprise=self.entreprise,
            montant="500.00",
            statut=RetraitEntreprise.STATUT_APPROUVE,
        )
        RetraitEntreprise.objects.create(
            entreprise=self.entreprise,
            montant="500.00",
            statut=RetraitEntreprise.STATUT_PAYE,
        )

        self.client.force_login(self.responsable)
        response = self.client.get(reverse("entreprise_app:solde"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["solde"]["montant_ventes"], Decimal("4500.00"))
        self.assertEqual(
            response.context["solde"]["montant_ventes_mois"],
            Decimal("4500.00"),
        )
        self.assertEqual(
            response.context["solde"]["montant_retraits_reserves"],
            Decimal("1500.00"),
        )
        self.assertEqual(
            response.context["solde"]["montant_disponible"],
            Decimal("3000.00"),
        )
        self.assertContains(response, "Article vendu (prix figé)")
        self.assertNotContains(response, "Article impayé")

        response = self.client.post(
            reverse("entreprise_app:demander-retrait"),
            {"montant": "3000.01"},
        )
        self.assertRedirects(response, reverse("entreprise_app:solde"))
        self.assertEqual(
            RetraitEntreprise.objects.filter(
                entreprise=self.entreprise,
                statut=RetraitEntreprise.STATUT_EN_ATTENTE,
            ).count(),
            1,
        )

        response = self.client.post(
            reverse("entreprise_app:demander-retrait"),
            {"montant": "3000.00"},
        )
        self.assertRedirects(response, reverse("entreprise_app:solde"))
        self.assertTrue(
            RetraitEntreprise.objects.filter(
                entreprise=self.entreprise,
                montant=Decimal("3000.00"),
                statut=RetraitEntreprise.STATUT_EN_ATTENTE,
            ).exists()
        )

    def test_company_cannot_request_a_withdrawal_above_available_balance(self):
        self.client.force_login(self.responsable)

        response = self.client.post(
            reverse("entreprise_app:demander-retrait"),
            {"montant": "1.00"},
        )

        self.assertRedirects(response, reverse("entreprise_app:solde"))
        self.assertFalse(RetraitEntreprise.objects.exists())

    def test_admin_can_approve_pay_and_reject_withdrawal_requests(self):
        admin_user = User.objects.create_superuser(
            telephone="70000620",
            password="StrongPassword123!",
            first_name="Admin",
            last_name="Finance",
        )
        withdrawal = RetraitEntreprise.objects.create(
            entreprise=self.entreprise,
            montant="1000.00",
        )
        admin_url = reverse("admin:entreprise_app_retraitentreprise_changelist")
        self.client.force_login(admin_user)

        response = self.client.post(
            admin_url,
            {
                "action": "approuver_retraits",
                "_selected_action": [str(withdrawal.pk)],
            },
        )

        self.assertEqual(response.status_code, 302)
        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.statut, RetraitEntreprise.STATUT_APPROUVE)
        self.assertEqual(withdrawal.traite_par, admin_user)

        response = self.client.post(
            admin_url,
            {
                "action": "marquer_retraits_payes",
                "_selected_action": [str(withdrawal.pk)],
            },
        )
        self.assertEqual(response.status_code, 302)
        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.statut, RetraitEntreprise.STATUT_PAYE)

        rejected_withdrawal = RetraitEntreprise.objects.create(
            entreprise=self.entreprise,
            montant="250.00",
        )
        response = self.client.post(
            admin_url,
            {
                "action": "rejeter_retraits",
                "_selected_action": [str(rejected_withdrawal.pk)],
            },
        )
        self.assertEqual(response.status_code, 302)
        rejected_withdrawal.refresh_from_db()
        self.assertEqual(
            rejected_withdrawal.statut,
            RetraitEntreprise.STATUT_REJETE,
        )

    def test_paid_out_of_block_articles_are_isolated_and_can_create_delivery(self):
        bloc = Blocs.objects.create(nom="Bloc retrait entreprise")
        zone_depart = Zone.objects.create(
            nom="Zone retrait entreprise",
            bloc=bloc,
            latitude="12.390000",
            longitude="-1.540000",
        )
        zone_client = Zone.objects.create(
            nom="Zone client livraison",
            bloc=bloc,
            latitude="12.410000",
            longitude="-1.510000",
        )
        client_user = User.objects.create_user(
            telephone="70000617",
            password="StrongPassword123!",
            first_name="Client",
            last_name="Livraison",
            role="client",
        )
        client_profile = Client.objects.create(user=client_user)
        article = Article.objects.create(
            entreprise=self.entreprise,
            nom="Article entreprise hors bloc",
            prix="1500.00",
            quantite_disponible=10,
            en_bloc=False,
        )
        article_entreprise_2 = Article.objects.create(
            entreprise=self.entreprise,
            nom="Deuxième article entreprise hors bloc",
            prix="1200.00",
            quantite_disponible=6,
            en_bloc=False,
        )
        article_bloc = Article.objects.create(
            entreprise=self.entreprise,
            nom="Article entreprise en bloc",
            prix="2000.00",
            en_bloc=True,
        )
        other_user = User.objects.create_user(
            telephone="70000618",
            password="StrongPassword123!",
            first_name="Autre",
            last_name="Entreprise",
            role="entreprise",
        )
        autre_entreprise = Entreprise.objects.create(
            user_principal=other_user,
            nom_entreprise="Autre entreprise",
            address="Bobo-Dioulasso",
        )
        article_autre_entreprise = Article.objects.create(
            entreprise=autre_entreprise,
            nom="Article confidentiel autre entreprise",
            prix="900.00",
            quantite_disponible=8,
            en_bloc=False,
        )

        panier_paye = Panier.objects.create(
            client=client_profile,
            statut=Panier.STATUT_COMMANDE,
        )
        commande_payee = Commande.objects.create(
            panier=panier_paye,
            client=client_profile,
            zone_arrivee=zone_client,
            latitude_livraison="12.412345",
            longitude_livraison="-1.512345",
            montant_produits="4400.00",
            total_a_payer="4400.00",
            statut_paiement=Commande.PAIEMENT_REUSSI,
        )
        ligne_entreprise = LigneCommande.objects.create(
            commande=commande_payee,
            article=article,
            entreprise=self.entreprise,
            nom_article=article.nom,
            nom_entreprise=self.entreprise.nom_entreprise,
            quantite=2,
            prix_unitaire="1500.00",
        )
        ligne_entreprise_2 = LigneCommande.objects.create(
            commande=commande_payee,
            article=article_entreprise_2,
            entreprise=self.entreprise,
            nom_article=article_entreprise_2.nom,
            nom_entreprise=self.entreprise.nom_entreprise,
            quantite=1,
            prix_unitaire="1200.00",
        )
        ligne_autre_entreprise = LigneCommande.objects.create(
            commande=commande_payee,
            article=article_autre_entreprise,
            entreprise=autre_entreprise,
            nom_article=article_autre_entreprise.nom,
            nom_entreprise=autre_entreprise.nom_entreprise,
            quantite=1,
            prix_unitaire="900.00",
        )
        LigneCommande.objects.create(
            commande=commande_payee,
            article=article_bloc,
            entreprise=self.entreprise,
            nom_article=article_bloc.nom,
            nom_entreprise=self.entreprise.nom_entreprise,
            quantite=1,
            prix_unitaire="2000.00",
        )

        panier_non_paye = Panier.objects.create(
            client=client_profile,
            statut=Panier.STATUT_COMMANDE,
        )
        commande_non_payee = Commande.objects.create(
            panier=panier_non_paye,
            client=client_profile,
            zone_arrivee=zone_client,
            latitude_livraison=zone_client.latitude,
            longitude_livraison=zone_client.longitude,
            montant_produits="1500.00",
            total_a_payer="1500.00",
        )
        LigneCommande.objects.create(
            commande=commande_non_payee,
            article=article,
            entreprise=self.entreprise,
            nom_article="Article impayé",
            nom_entreprise=self.entreprise.nom_entreprise,
            quantite=1,
            prix_unitaire="1500.00",
        )

        self.client.force_login(self.responsable)
        url = reverse("entreprise_app:livraisons-articles")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.context["commandes_entreprise"]),
            1,
        )
        self.assertEqual(
            [
                ligne.pk
                for ligne in response.context["commandes_entreprise"][0]["lignes"]
            ],
            [ligne_entreprise.pk, ligne_entreprise_2.pk],
        )
        self.assertContains(response, article.nom)
        self.assertContains(response, article_entreprise_2.nom)
        self.assertNotContains(response, article_autre_entreprise.nom)
        self.assertNotContains(response, article_bloc.nom)
        self.assertNotContains(response, "Article impayé")
        self.assertContains(response, "Capturer ma position de collecte")
        self.assertContains(response, 'x-model="latitude"')
        self.assertContains(response, 'x-model="longitude"')

        creation_url = reverse(
            "entreprise_app:creer-livraison-commande",
            args=[commande_payee.pk],
        )
        response = self.client.post(
            creation_url,
            {"zone_depart": zone_depart.pk},
        )
        self.assertRedirects(response, url)
        self.assertFalse(DemandeLivraison.objects.exists())

        response = self.client.post(
            creation_url,
            {
                "zone_depart": zone_depart.pk,
                "latitude_depart": "91",
                "longitude_depart": "-1.234567",
            },
        )
        self.assertRedirects(response, url)
        self.assertFalse(DemandeLivraison.objects.exists())

        response = self.client.post(
            creation_url,
            {
                "zone_depart": zone_depart.pk,
                "latitude_depart": "12.345678",
                "longitude_depart": "-1.234567",
            },
        )

        self.assertRedirects(response, url)
        demande = DemandeLivraison.objects.get(ligne_commande=ligne_entreprise)
        self.assertQuerySetEqual(
            demande.lignes_commande.order_by("pk"),
            [ligne_entreprise, ligne_entreprise_2],
        )
        commande_payee.refresh_from_db()
        self.assertEqual(demande.client, client_profile)
        self.assertEqual(demande.zone_depart, zone_depart)
        self.assertEqual(demande.zone_arrivee, zone_client)
        self.assertEqual(demande.latitude_depart, Decimal("12.345678"))
        self.assertEqual(demande.longitude_depart, Decimal("-1.234567"))
        self.assertEqual(
            demande.latitude_arrivee,
            commande_payee.latitude_livraison,
        )
        self.assertEqual(
            demande.longitude_arrivee,
            commande_payee.longitude_livraison,
        )
        self.assertTrue(demande.position_destinataire_validee)
        self.assertEqual(demande.statut_destinataire, "position_recue")
        self.assertEqual(
            demande.latitude_destinataire_reelle,
            commande_payee.latitude_livraison,
        )
        self.assertEqual(
            demande.longitude_destinataire_reelle,
            commande_payee.longitude_livraison,
        )
        self.assertEqual(
            demande.whatsapp_destinataire,
            client_user.telephone,
        )
        self.assertIn(article.nom, demande.description_colis)
        self.assertIn(article_entreprise_2.nom, demande.description_colis)
        self.assertEqual(demande.statut, "en_attente")

        response = self.client.post(
            reverse(
                "entreprise_app:creer-livraison-commande",
                args=[commande_payee.pk],
            ),
            {
                "zone_depart": zone_depart.pk,
                "latitude_depart": "12.345678",
                "longitude_depart": "-1.234567",
            },
        )
        self.assertRedirects(response, url)
        self.assertEqual(
            DemandeLivraison.objects.filter(
                ligne_commande=ligne_entreprise,
            ).count(),
            1,
        )

        response = self.client.post(
            reverse(
                "entreprise_app:creer-livraison-commande",
                args=[commande_payee.pk],
            ),
            {
                "zone_depart": zone_depart.pk,
                "latitude_depart": "12.345678",
                "longitude_depart": "-1.234567",
            },
        )
        self.assertRedirects(response, url)
        self.assertEqual(
            DemandeLivraison.objects.filter(
                ligne_commande=ligne_entreprise,
            ).count(),
            1,
        )

        self.client.force_login(other_user)
        response = self.client.get(url)
        self.assertEqual(
            [
                ligne.pk
                for ligne in response.context["commandes_entreprise"][0]["lignes"]
            ],
            [ligne_autre_entreprise.pk],
        )
        self.assertNotContains(response, article.nom)

        response = self.client.post(
            reverse(
                "entreprise_app:creer-livraison-commande",
                args=[commande_payee.pk],
            ),
            {
                "zone_depart": zone_depart.pk,
                "latitude_depart": "12.345678",
                "longitude_depart": "-1.234567",
            },
        )
        self.assertRedirects(response, url)
        demande_autre = DemandeLivraison.objects.get(
            ligne_commande=ligne_autre_entreprise,
        )
        self.assertQuerySetEqual(
            demande_autre.lignes_commande.all(),
            [ligne_autre_entreprise],
        )
        self.assertEqual(demande_autre.client, client_profile)
        self.assertEqual(
            demande_autre.latitude_arrivee,
            commande_payee.latitude_livraison,
        )

    def test_other_user_cannot_open_enterprise_dashboard(self):
        client_user = User.objects.create_user(
            telephone="70000615",
            password="StrongPassword123!",
            first_name="Client",
            last_name="Test",
            role="client",
        )
        self.client.force_login(client_user)

        response = self.client.get(reverse("entreprise_app:entreprise-detail"))

        self.assertEqual(response.status_code, 404)

    def test_owner_can_create_admin_and_receives_generated_credentials(self):
        self.client.force_login(self.responsable)

        response = self.client.post(
            self.url,
            self.form_data,
            HTTP_HX_REQUEST="true",
        )

        membership = MembreAdminsEntreprise.objects.get(
            membre_admin__telephone=self.form_data["telephone"]
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["HX-Trigger"],
            "entreprise-admin-register-success",
        )
        self.assertContains(response, membership.membre_admin.username)
        self.assertEqual(membership.entreprise, self.entreprise)
        self.assertEqual(membership.ajoute_par, self.responsable)
        self.assertEqual(membership.membre_admin.role, "entreprise_admin")
        self.assertContains(response, 'id="enterprise-admin-list" hx-swap-oob="outerHTML"')

    def test_admin_quota_is_enforced(self):
        self.entreprise.palier = "standard"
        self.entreprise.save(update_fields=["palier"])
        existing_admin = User.objects.create_user(
            telephone="70000614",
            password="StrongPassword123!",
            first_name="Premier",
            last_name="Admin",
            role="entreprise_admin",
        )
        MembreAdminsEntreprise.objects.create(
            entreprise=self.entreprise,
            membre_admin=existing_admin,
            ajoute_par=self.responsable,
        )
        self.client.force_login(self.responsable)

        response = self.client.post(
            self.url,
            self.form_data,
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "quota de 1 administrateur")
        self.assertFalse(User.objects.filter(telephone=self.form_data["telephone"]).exists())
