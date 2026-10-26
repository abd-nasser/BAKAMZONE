from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from articles_app.models import Article, StockBloc
from blocs_app.models import Blocs
from auth_app.models import User
from clients_app.forms import InscriptionClientForm
from clients_app.models import Client
from clients_app.views import LivreurProfilViewByClient
from entreprise_app.models import Entreprise
from livreurs_app.models import Livreur


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


class ClientDashboardViewTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create(
            telephone="70000801",
            first_name="Awa",
            last_name="Traore",
            role="client",
        )
        self.client_profile = Client.objects.create(user=self.client_user)
        self.client.force_login(self.client_user)

        self.bloc = Blocs.objects.create(
            nom="Bloc Tampouy",
            quartier="tampouy",
            actif=True,
        )
        self.entreprise_user = User.objects.create(
            telephone="70000802",
            first_name="Sali",
            last_name="Commercante",
            role="entreprise",
        )
        self.entreprise = Entreprise.objects.create(
            user_principal=self.entreprise_user,
            nom_entreprise="Marché Faso",
            address="Ouagadougou",
        )
        self.article = self.create_article(
            "Riz local",
            prix="2500.00",
            prix_promo="2200.00",
        )
        self.create_livreur(
            telephone="70000803",
            first_name="Moussa",
            last_name="Ouedraogo",
            type_vehicule="moto",
        )

    def create_article(self, nom, prix="1000.00", prix_promo=None, **article_fields):
        article = Article.objects.create(
            entreprise=self.entreprise,
            nom=nom,
            prix=Decimal(prix),
            prix_promo=Decimal(prix_promo) if prix_promo else None,
            disponible=True,
            en_bloc=True,
            **article_fields,
        )
        StockBloc.objects.create(article=article, bloc=self.bloc, quantite=4)
        return article

    def create_livreur(self, telephone, first_name, last_name, **livreur_fields):
        user = User.objects.create(
            telephone=telephone,
            first_name=first_name,
            last_name=last_name,
            role="livreur",
        )
        defaults = {
            "actif": True,
            "disponible": True,
            "statut_verification": "verifie",
            **livreur_fields,
        }
        return Livreur.objects.create(
            user=user,
            blocs=self.bloc,
            **defaults,
        )

    def test_dashboard_shows_active_drivers_and_in_stock_articles(self):
        self.create_livreur(
            telephone="70000804",
            first_name="Idrissa",
            last_name="Kaboré",
            type_vehicule="velo",
            disponible=False,
        )
        no_stock_article = Article.objects.create(
            entreprise=self.entreprise,
            nom="Article sans stock",
            prix=Decimal("500.00"),
            disponible=True,
            en_bloc=True,
        )
        expired_article = self.create_article(
            "Article expiré",
            date_expiration=timezone.now() - timedelta(days=1),
        )

        response = self.client.get(reverse("clients_app:tableau-de-bord"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Livreurs du réseau")
        self.assertContains(response, "Articles disponibles")
        self.assertContains(response, "Moussa Ouedraogo")
        self.assertContains(response, "Indisponible")
        self.assertContains(response, "Riz local")
        self.assertContains(response, "Idrissa Kaboré")
        self.assertNotContains(response, no_stock_article.nom)
        self.assertNotContains(response, expired_article.nom)

    def test_search_and_filters_apply_to_each_section_independently(self):
        other_article = self.create_article(
            "Huile de karité",
            prix="3000.00",
        )
        self.create_livreur(
            telephone="70000805",
            first_name="Aminata",
            last_name="Sawadogo",
            type_vehicule="velo",
        )

        response = self.client.get(
            reverse("clients_app:tableau-de-bord"),
            {
                "livreur_q": "Moussa",
                "livreur_vehicule": "moto",
                "article_q": "Riz",
                "article_tri": "prix_croissant",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["livreurs"].values_list("user__first_name", flat=True)), ["Moussa"])
        self.assertEqual(list(response.context["articles"].values_list("pk", flat=True)), [self.article.pk])
        self.assertNotContains(response, other_article.nom)
        self.assertContains(response, 'name="article_q" value="Riz"')
        self.assertContains(response, 'name="livreur_q" value="Moussa"')

    def test_htmx_livreur_filter_returns_only_livreur_results(self):
        response = self.client.get(
            reverse("clients_app:tableau-de-bord"),
            {"livreur_q": "Moussa"},
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="client-livreurs-results",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="client-livreurs-results"')
        self.assertContains(response, "Moussa Ouedraogo")
        self.assertNotContains(response, "Articles disponibles")

    def test_htmx_article_filter_returns_only_article_results(self):
        response = self.client.get(
            reverse("clients_app:tableau-de-bord"),
            {"article_q": "Riz"},
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="client-articles-results",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="client-articles-results"')
        self.assertContains(response, "Riz local")
        self.assertNotContains(response, "Livreurs disponibles")

    def test_favorite_filter_and_profile_chat_placeholders_are_available(self):
        livreur = Livreur.objects.get(user__telephone="70000803")
        livreur.favoris_de.add(self.client_profile)

        response = self.client.get(
            reverse("clients_app:tableau-de-bord"),
            {"livreur_favoris": "1"},
        )

        self.assertEqual(list(response.context["livreurs"]), [livreur])
        self.assertContains(response, 'href="#"')
        self.assertContains(response, "Voir le profil")
        self.assertContains(response, "Chat")

    def test_livreur_profile_view_uses_detail_view_and_renders_profile(self):
        livreur = Livreur.objects.get(user__telephone="70000803")

        response = self.client.get(
            reverse("clients_app:profil-livreur", args=[livreur.pk])
        )

        self.assertIs(LivreurProfilViewByClient.model, Livreur)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Moussa Ouedraogo")
        self.assertContains(response, "Bloc Tampouy")
        self.assertContains(response, "Démarrer un chat")

    def test_livreur_profile_view_requires_client_profile(self):
        self.client.logout()
        other_user = User.objects.create(
            telephone="70000808",
            first_name="Admin",
            last_name="Test",
            role="entreprise",
        )
        self.client.force_login(other_user)
        livreur = Livreur.objects.get(user__telephone="70000803")

        response = self.client.get(
            reverse("clients_app:profil-livreur", args=[livreur.pk])
        )

        self.assertEqual(response.status_code, 403)

    def test_livreur_profile_view_hides_inactive_livreurs(self):
        livreur = Livreur.objects.get(user__telephone="70000803")
        livreur.actif = False
        livreur.save(update_fields=["actif"])

        response = self.client.get(
            reverse("clients_app:profil-livreur", args=[livreur.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_dashboard_requires_a_client_profile(self):
        self.client.logout()
        other_user = User.objects.create(
            telephone="70000806",
            first_name="Admin",
            last_name="Test",
            role="entreprise",
        )
        self.client.force_login(other_user)

        response = self.client.get(reverse("clients_app:tableau-de-bord"))

        self.assertEqual(response.status_code, 403)

    def test_authenticated_client_has_dashboard_link_on_homepage(self):
        response = self.client.get(reverse("home_app:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("clients_app:tableau-de-bord"),
        )
