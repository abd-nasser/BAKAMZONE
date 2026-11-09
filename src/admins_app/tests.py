from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from auth_app.models import User
from articles_app.models import Article
from blocs_app.models import Blocs
from clients_app.models import Client
from demande_livraison_app.models import DemandeLivraison
from entreprise_app.models import Entreprise
from livreurs_app.models import Livreur
from zones_app.models import Zone

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
            "admins_templates/superviseur_flotte_dashboard.html",
        )
        self.assertEqual(response.context["livreurs_count"], 1)
        self.assertContains(
            response,
            reverse("admins_app:tableau-de-bord-flotte-livreurs"),
        )
        self.assertContains(
            response,
            reverse("admins_app:tableau-de-bord-flotte-demandes-livraison"),
        )

    def test_fleet_map_includes_only_trackable_deliveries_from_its_block(self):
        self.admin_bloc.poste = "superviseur_flotte"
        self.admin_bloc.save(update_fields=["poste"])
        client_user = User.objects.create(
            telephone="70000919",
            first_name="Mariam",
            last_name="Client",
            role="client",
        )
        client_profile = Client.objects.create(user=client_user)
        other_bloc = Blocs.objects.create(
            nom="Bloc autre flotte",
            ville="ouagadougou",
            quartier="pattedoie",
        )
        local_zone = Zone.objects.create(nom="Zone locale", bloc=self.bloc)
        remote_zone = Zone.objects.create(nom="Zone distante", bloc=other_bloc)
        local_courier_user = User.objects.create(
            telephone="70000920",
            first_name="Issa",
            last_name="Kaboré",
            role="livreur",
        )
        local_courier = Livreur.objects.create(
            user=local_courier_user,
            type_vehicule="moto",
            blocs=self.bloc,
            actif=True,
        )
        remote_courier_user = User.objects.create(
            telephone="70000921",
            first_name="Awa",
            last_name="Traore",
            role="livreur",
        )
        remote_courier = Livreur.objects.create(
            user=remote_courier_user,
            type_vehicule="velo",
            blocs=other_bloc,
            actif=True,
        )

        def create_delivery(courier):
            return DemandeLivraison.objects.create(
                client=client_profile,
                livreur=courier,
                zone_depart=local_zone,
                zone_arrivee=remote_zone,
                latitude_depart=Decimal("12.345678"),
                longitude_depart=Decimal("-1.234567"),
                prix=Decimal("1500"),
                whatsapp_destinataire="+22670000003",
                statut="en_cours",
                position_destinataire_validee=True,
                latitude_destinataire_reelle=Decimal("12.350000"),
                longitude_destinataire_reelle=Decimal("-1.230000"),
            )

        local_delivery = create_delivery(local_courier)
        create_delivery(remote_courier)

        response = self.client.get(reverse("admins_app:tableau-de-bord-flotte"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.context["tracking_config"]["deliveries"]],
            [local_delivery.pk],
        )
        self.assertContains(response, f"Livraison #{local_delivery.pk}")

    def test_livreur_list_displays_only_livreurs_from_supervisor_block(self):
        self.admin_bloc.poste = "superviseur_flotte"
        self.admin_bloc.save(update_fields=["poste"])
        local_user = User.objects.create(
            telephone="70000914",
            first_name="Issa",
            last_name="Kaboré",
            role="livreur",
        )
        local_livreur = Livreur.objects.create(
            user=local_user,
            type_vehicule="moto",
            blocs=self.bloc,
        )
        other_user = User.objects.create(
            telephone="70000915",
            first_name="Aminata",
            last_name="Diallo",
            role="livreur",
        )
        other_livreur = Livreur.objects.create(
            user=other_user,
            type_vehicule="velo",
            blocs=self.bloc,
        )
        response = self.client.get(
            reverse("admins_app:tableau-de-bord-flotte-livreurs")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "admins_templates/superviseur_livreurs.html",
        )
        self.assertEqual(
            list(response.context["livreurs"]),
            [other_livreur, local_livreur],
        )
        self.assertContains(response, "Issa Kaboré")
        self.assertContains(response, "Aminata Diallo")

    def test_htmx_livreur_list_filters_by_name_and_phone(self):
        self.admin_bloc.poste = "superviseur_flotte"
        self.admin_bloc.save(update_fields=["poste"])
        matching_user = User.objects.create(
            telephone="70000916",
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
            telephone="70000917",
            first_name="Aminata",
            last_name="Diallo",
            role="livreur",
        )
        Livreur.objects.create(user=other_user, type_vehicule="velo", blocs=self.bloc)
        response = self.client.get(
            reverse("admins_app:tableau-de-bord-flotte-livreurs"),
            {"q": "70000916"},
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

    def test_delivery_list_contains_requests_involving_supervisor_block(self):
        self.admin_bloc.poste = "superviseur_flotte"
        self.admin_bloc.save(update_fields=["poste"])
        client_user = User.objects.create(
            telephone="70000918",
            first_name="Mariam",
            last_name="Ouedraogo",
            role="client",
        )
        client_profile = Client.objects.create(user=client_user)
        local_zone = Zone.objects.create(nom="Zone supervision", bloc=self.bloc)
        other_bloc = Blocs.objects.create(
            nom="Bloc Zogona",
            ville="ouagadougou",
            quartier="zogona",
        )
        other_zone = Zone.objects.create(nom="Zone éloignée", bloc=other_bloc)
        local_demand = DemandeLivraison.objects.create(
            client=client_profile,
            zone_depart=local_zone,
            zone_arrivee=other_zone,
            latitude_depart="12.345678",
            longitude_depart="-1.234567",
            latitude_arrivee="12.456789",
            longitude_arrivee="-1.345678",
            prix="1500",
        )
        DemandeLivraison.objects.create(
            client=client_profile,
            zone_depart=other_zone,
            zone_arrivee=other_zone,
            latitude_depart="12.345678",
            longitude_depart="-1.234567",
            latitude_arrivee="12.456789",
            longitude_arrivee="-1.345678",
            prix="1500",
        )

        response = self.client.get(
            reverse("admins_app:tableau-de-bord-flotte-demandes-livraison")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "admins_templates/superviseur_demandes_livraison.html",
        )
        self.assertEqual(
            list(response.context["demandes_livraison"]),
            [local_demand],
        )
        self.assertContains(response, "Mariam Ouedraogo")


class AssistantOperationnelDashboardTests(TestCase):
    def setUp(self):
        self.bloc = Blocs.objects.create(
            nom="Bloc Assistant",
            ville="ouagadougou",
            quartier="tampouy",
        )
        self.other_bloc = Blocs.objects.create(
            nom="Bloc Eloigné",
            ville="ouagadougou",
            quartier="pissy",
        )
        self.user = User.objects.create(
            telephone="70000701",
            first_name="Aminata",
            last_name="Assistant",
            role="bloc_admin",
        )
        self.admin_bloc = AdminBloc.objects.create(
            user=self.user,
            bloc=self.bloc,
            poste="assistant",
            actif=True,
        )
        client_user = User.objects.create(
            telephone="70000702",
            first_name="Mariam",
            last_name="Client",
            role="client",
        )
        self.client_profile = Client.objects.create(user=client_user)
        self.local_zone = Zone.objects.create(
            nom="Zone locale assistant",
            bloc=self.bloc,
        )
        self.remote_zone = Zone.objects.create(
            nom="Zone distante",
            bloc=self.other_bloc,
        )
        self.alert = self.create_delivery(
            statut="en_cours",
            statut_position_destinataire="alerte_assistant",
        )
        self.url = reverse("admins_app:tableau-de-bord-assistant")
        self.client.force_login(self.user)

    def create_delivery(
        self,
        *,
        statut,
        statut_position_destinataire="en_attente",
        zone=None,
    ):
        return DemandeLivraison.objects.create(
            client=self.client_profile,
            zone_depart=zone or self.local_zone,
            zone_arrivee=self.remote_zone,
            latitude_depart=Decimal("12.345678"),
            longitude_depart=Decimal("-1.234567"),
            prix=Decimal("1500"),
            whatsapp_destinataire="+22670000003",
            statut=statut,
            statut_position_destinataire=statut_position_destinataire,
        )

    def test_dashboard_shows_regional_deliveries_alerts_and_call_action(self):
        other_delivery = self.create_delivery(
            statut="acceptee",
            zone=self.local_zone,
        )
        outside_delivery = self.create_delivery(
            statut="acceptee",
            zone=self.remote_zone,
        )
        non_active = self.create_delivery(statut="livree")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "admins_templates/assistant_operationnel_dashboard.html",
        )
        self.assertEqual(list(response.context["alertes_destinataire"]), [self.alert])
        self.assertEqual(
            set(response.context["livraisons_actives"]),
            {self.alert, other_delivery},
        )
        self.assertNotContains(response, f"Demande #{outside_delivery.pk}")
        self.assertNotContains(response, f"Demande #{non_active.pk}")
        self.assertContains(response, "tel:+22670000003")
        self.assertContains(response, "Enregistrer la position")
        self.assertContains(response, "hx-trigger=\"every 30s\"")

    def test_htmx_poll_returns_only_the_live_panel(self):
        response = self.client.get(self.url, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "partials/admins/assistant_operationnel_livraisons.html",
        )
        self.assertContains(response, 'id="assistant-operationnel-panel"')

    def test_assistant_can_record_a_valid_position(self):
        response = self.client.post(self.url, {
            "demande_id": self.alert.pk,
            "action": "enregistrer_position",
            "latitude": "12.123456",
            "longitude": "-1.123456",
        })

        self.assertRedirects(response, self.url)
        self.alert.refresh_from_db()
        self.assertTrue(self.alert.position_destinataire_validee)
        self.assertEqual(self.alert.statut_position_destinataire, "position_recue")
        self.assertEqual(
            self.alert.latitude_destinataire_reelle,
            Decimal("12.123456"),
        )
        self.assertEqual(
            self.alert.longitude_destinataire_reelle,
            Decimal("-1.123456"),
        )

    @patch(
        "admins_app.views.programmer_notification_position_destinataire",
        return_value=True,
    )
    def test_manual_position_notifies_client_only_on_first_validation(
        self,
        notify_client,
    ):
        """La saisie manuelle suit la même règle de notification unique que la PWA."""
        courier_user = User.objects.create(
            telephone="70000704",
            first_name="Moussa",
            last_name="Livreur",
            role="livreur",
        )
        courier = Livreur.objects.create(
            user=courier_user,
            type_vehicule="moto",
            blocs=self.bloc,
        )
        self.alert.livreur = courier
        self.alert.save(update_fields=["livreur"])
        payload = {
            "demande_id": self.alert.pk,
            "action": "enregistrer_position",
            "latitude": "12.123456",
            "longitude": "-1.123456",
        }

        self.client.post(self.url, payload)
        self.client.post(self.url, payload)

        notify_client.assert_called_once()
        self.alert.refresh_from_db()
        self.assertTrue(self.alert.position_destinataire_validee)

    def test_assistant_can_flag_alert_as_unreachable(self):
        response = self.client.post(self.url, {
            "demande_id": self.alert.pk,
            "action": "marquer_injoignable",
        })

        self.assertRedirects(response, self.url)
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.statut_position_destinataire, "injoignable")

    def test_rejects_invalid_manual_coordinates(self):
        response = self.client.post(self.url, {
            "demande_id": self.alert.pk,
            "action": "enregistrer_position",
            "latitude": "91",
            "longitude": "-1.123456",
        }, follow=True)

        self.assertContains(response, "Coordonnées invalides")
        self.alert.refresh_from_db()
        self.assertFalse(self.alert.position_destinataire_validee)
        self.assertEqual(self.alert.statut_position_destinataire, "alerte_assistant")

    def test_cannot_mark_non_alert_delivery_unreachable(self):
        self.alert.statut_position_destinataire = "en_attente"
        self.alert.save(update_fields=["statut_position_destinataire"])

        response = self.client.post(self.url, {
            "demande_id": self.alert.pk,
            "action": "marquer_injoignable",
        }, follow=True)

        self.assertContains(response, "Seules les demandes en alerte")
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.statut_position_destinataire, "en_attente")

    def test_assistant_cannot_update_delivery_outside_its_block(self):
        remote_delivery = self.create_delivery(
            statut="en_cours",
            statut_position_destinataire="alerte_assistant",
            zone=self.remote_zone,
        )

        response = self.client.post(self.url, {
            "demande_id": remote_delivery.pk,
            "action": "marquer_injoignable",
        })

        self.assertEqual(response.status_code, 404)
        remote_delivery.refresh_from_db()
        self.assertEqual(
            remote_delivery.statut_position_destinataire,
            "alerte_assistant",
        )

    def test_dashboard_remains_limited_to_active_assistant_of_block(self):
        self.admin_bloc.actif = False
        self.admin_bloc.save(update_fields=["actif"])

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)


class AdminBlocCreationFormTests(TestCase):
    def setUp(self):
        self.bloc = Blocs.objects.create(
            nom="Bloc Koulouba",
            ville="ouagadougou",
            quartier="koulouba",
        )
        self.superuser = User.objects.create(
            telephone="70000920",
            first_name="Super",
            last_name="Admin",
            role="client",
            is_superuser=True,
        )
        self.client.force_login(self.superuser)
        self.url = reverse("admins_app:creer-admin-bloc")

    def test_valid_post_creates_admin_and_returns_success_partial(self):
        response = self.client.post(self.url, {
            "first_name": "Issa",
            "last_name": "Ouedraogo",
            "telephone": "70000922",
            "email": "issa@example.test",
            "bloc": self.bloc.pk,
            "poste": "gestionnaire_stock",
            "actif": "on",
        }, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(AdminBloc.objects.count(), 1)
        self.assertEqual(
            AdminBloc.objects.get().user.telephone,
            "70000922",
        )
        self.assertContains(response, "Administrateur créé")

    def test_invalid_post_does_not_create_admin_and_returns_visible_errors(self):
        response = self.client.post(self.url, {
            "last_name": "Ouedraogo",
            "telephone": "70000923",
            "bloc": self.bloc.pk,
            "poste": "gestionnaire_stock",
            "actif": "on",
        }, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(AdminBloc.objects.count(), 0)
        self.assertContains(response, "n’a pas pu être créé")
        self.assertContains(response, "Ce champ est obligatoire.")

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
