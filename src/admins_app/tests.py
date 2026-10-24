from django.test import TestCase
from django.urls import reverse

from auth_app.models import User
from articles_app.models import Article
from blocs_app.models import Blocs
from entreprise_app.models import Entreprise
from livreurs_app.models import Livreur

from .forms import AdminBlocForms
from .models import AdminBloc


class GestionnaireStockDashboardViewTests(TestCase):
    def setUp(self):
        self.bloc = Blocs.objects.create(
            nom="Bloc Tampouy",
            ville="ouagadougou",
            quartier="tampouy",
        )
        self.user = User.objects.create(
            telephone="70000901",
            first_name="Oumar",
            last_name="Kone",
            role="bloc_admin",
        )
        self.admin_bloc = AdminBloc.objects.create(
            user=self.user,
            bloc=self.bloc,
            poste="gestionnaire_stock",
        )
        self.entreprise = Entreprise.objects.create(
            user_principal=User.objects.create(
                telephone="70000902",
                first_name="Awa",
                last_name="Traore",
                role="entreprise",
            ),
            nom_entreprise="Entreprise Faso",
            address="Ouagadougou",
        )
        self.autre_entreprise = Entreprise.objects.create(
            user_principal=User.objects.create(
                telephone="70000903",
                first_name="Mariam",
                last_name="Sawadogo",
                role="entreprise",
            ),
            nom_entreprise="Commerce Bobo",
            address="Bobo-Dioulasso",
        )
        self.url = reverse("admins_app:tableau-de-bord-stock")
        self.client.force_login(self.user)

    def test_dashboard_provides_all_enterprises_and_admin_block_context(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "admins_templates/gestionnaire_stock_dashboard.html",
        )
        self.assertEqual(
            set(response.context["entreprises"]),
            {self.entreprise, self.autre_entreprise},
        )
        self.assertEqual(response.context["admin_bloc"], self.admin_bloc)
        self.assertEqual(response.context["bloc"], self.bloc)
        self.assertContains(response, 'hx-get="' + self.url + '"')

    def test_htmx_request_filters_enterprises_by_name_and_returns_partial(self):
        response = self.client.get(
            self.url,
            {"q": "Bobo"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "partials/admins/gestionnaire_stock_entreprises.html",
        )
        self.assertEqual(list(response.context["entreprises"]), [self.autre_entreprise])
        self.assertContains(response, "Commerce Bobo")
        self.assertNotContains(response, "Entreprise Faso")

    def test_htmx_request_filters_enterprises_by_address(self):
        response = self.client.get(
            self.url,
            {"q": "Ouagadougou"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["entreprises"]), [self.entreprise])

    def test_other_block_admin_postes_cannot_access_dashboard(self):
        self.admin_bloc.poste = "assistant"
        self.admin_bloc.save(update_fields=["poste"])

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_inactive_block_admin_cannot_access_dashboard(self):
        self.admin_bloc.actif = False
        self.admin_bloc.save(update_fields=["actif"])

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_non_block_admin_user_cannot_access_dashboard(self):
        self.user.role = "client"
        self.user.save(update_fields=["role"])

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)


class GestionnaireStockEntrepriseDetailViewTests(TestCase):
    def setUp(self):
        self.bloc = Blocs.objects.create(
            nom="Bloc Tampouy",
            ville="ouagadougou",
            quartier="tampouy",
        )
        self.user = User.objects.create(
            telephone="70000891",
            role="bloc_admin",
        )
        AdminBloc.objects.create(
            user=self.user,
            bloc=self.bloc,
            poste="gestionnaire_stock",
            actif=True,
        )
        self.entreprise = Entreprise.objects.create(
            user_principal=User.objects.create(
                telephone="70000892",
                role="entreprise",
            ),
            nom_entreprise="Entreprise Faso",
            address="Ouagadougou",
        )
        self.url = reverse(
            "admins_app:entreprise-detail-stock",
            args=[self.entreprise.pk],
        )

    def test_stock_manager_can_open_enterprise_detail(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "admins_templates/gestionnaire_stock_entreprise_detail.html",
        )
        self.assertEqual(response.context["entreprise"], self.entreprise)
        self.assertEqual(response.context["bloc"], self.bloc)
        self.assertContains(response, "Ajouter un article")
        self.assertNotIn(
            "entreprise",
            response.context["create_article_form"].fields,
        )
        self.assertContains(
            response,
            f'id="create-article-modal"',
        )

    def test_detail_includes_edit_and_delete_modals_for_each_article(self):
        article = Article.objects.create(
            entreprise=self.entreprise,
            nom="Riz local",
            prix="2500.00",
        )
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            "entreprise",
            response.context["articles"][0].admin_form.fields,
        )
        self.assertContains(response, f'id="edit-article-modal-{article.pk}"')
        self.assertContains(response, f'id="delete-article-modal-{article.pk}"')

    def test_non_stock_manager_cannot_open_enterprise_detail(self):
        AdminBloc.objects.filter(user=self.user).update(poste="assistant")
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_inactive_stock_manager_cannot_open_enterprise_detail(self):
        AdminBloc.objects.filter(user=self.user).update(actif=False)
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)


class AdminBlocPostDashboardViewTests(TestCase):
    def setUp(self):
        self.bloc = Blocs.objects.create(
            nom="Bloc Karpala",
            ville="ouagadougou",
            quartier="karpala",
        )
        self.user = User.objects.create(
            telephone="70000911",
            first_name="Aminata",
            last_name="Diallo",
            role="bloc_admin",
        )
        self.admin_bloc = AdminBloc.objects.create(
            user=self.user,
            bloc=self.bloc,
            poste="responsable",
            actif=True,
        )
        self.client.force_login(self.user)

    def test_each_post_opens_its_own_dashboard(self):
        dashboards = {
            "responsable": ("tableau-de-bord-responsable", "Espace Responsable de Bloc"),
            "superviseur_flotte": (
                "tableau-de-bord-flotte",
                "Espace Superviseur de Flotte",
            ),
            "assistant": (
                "tableau-de-bord-assistant",
                "Espace Assistant Opérationnel",
            ),
        }

        for poste, (route_name, title) in dashboards.items():
            with self.subTest(poste=poste):
                self.admin_bloc.poste = poste
                self.admin_bloc.save(update_fields=["poste"])
                response = self.client.get(reverse(f"admins_app:{route_name}"))

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, title)
                self.assertEqual(response.context["admin_bloc"], self.admin_bloc)

    def test_post_dashboard_rejects_a_different_post(self):
        response = self.client.get(
            reverse("admins_app:tableau-de-bord-assistant")
        )

        self.assertEqual(response.status_code, 403)

    def test_home_page_links_to_dashboard_for_admin_post(self):
        response = self.client.get(reverse("home_app:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("admins_app:tableau-de-bord-responsable"),
        )
        self.assertContains(response, self.admin_bloc.get_poste_display())

    def test_fleet_dashboard_lists_only_livreurs_from_supervisor_block(self):
        self.admin_bloc.poste = "superviseur_flotte"
        self.admin_bloc.save(update_fields=["poste"])
        livreur_user = User.objects.create(
            telephone="70000912",
            first_name="Moussa",
            last_name="Zongo",
            role="livreur",
        )
        livreur = Livreur.objects.create(
            user=livreur_user,
            type_vehicule="moto",
            blocs=self.bloc,
        )
        other_bloc = Blocs.objects.create(
            nom="Bloc Patte d'Oie",
            ville="ouagadougou",
            quartier="pattedoie",
        )
        other_user = User.objects.create(
            telephone="70000913",
            first_name="Awa",
            last_name="Traore",
            role="livreur",
        )
        Livreur.objects.create(
            user=other_user,
            type_vehicule="velo",
            blocs=other_bloc,
        )

        response = self.client.get(reverse("admins_app:tableau-de-bord-flotte"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "admins_templates/superviseur_livreurs.html",
        )
        self.assertEqual(list(response.context["livreurs"]), [livreur])
        self.assertContains(response, "Moussa Zongo")
        self.assertNotContains(response, "Awa Traore")

    def test_htmx_fleet_dashboard_filters_livreurs_by_name_and_phone(self):
        self.admin_bloc.poste = "superviseur_flotte"
        self.admin_bloc.save(update_fields=["poste"])
        matching_user = User.objects.create(
            telephone="70000914",
            first_name="Issa",
            last_name="Kaboré",
            role="livreur",
        )
        matching_livreur = Livreur.objects.create(
            user=matching_user,
            type_vehicule="moto",
            blocs=self.bloc,
        )
        other_user = User.objects.create(
            telephone="70000915",
            first_name="Aminata",
            last_name="Diallo",
            role="livreur",
        )
        Livreur.objects.create(
            user=other_user,
            type_vehicule="velo",
            blocs=self.bloc,
        )

        response = self.client.get(
            reverse("admins_app:tableau-de-bord-flotte"),
            {"q": "70000914"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "partials/admins/superviseur_flotte_livreurs.html",
        )
        self.assertEqual(list(response.context["livreurs"]), [matching_livreur])
        self.assertContains(response, "Issa Kaboré")
        self.assertNotContains(response, "Aminata Diallo")


class AdminBlocCreationFormTests(TestCase):
    def test_created_admin_account_uses_dashboard_supported_role(self):
        bloc = Blocs.objects.create(
            nom="Bloc Pissy",
            ville="ouagadougou",
            quartier="pissy",
        )
        form = AdminBlocForms(data={
            "first_name": "Issa",
            "last_name": "Ouedraogo",
            "telephone": "70000921",
            "email": "issa@example.test",
            "bloc": bloc.pk,
            "poste": "gestionnaire_stock",
            "actif": "on",
        })

        self.assertTrue(form.is_valid(), form.errors)
        admin_bloc = form.save()

        self.assertEqual(admin_bloc.user.role, "bloc_admin")
