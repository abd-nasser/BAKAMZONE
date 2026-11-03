from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from admins_app.models import AdminBloc
from articles_app.models import Article, StockBloc
from avis_app.models import AvisLivreur
from blocs_app.models import Blocs
from auth_app.models import User
from clients_app.forms import InscriptionClientForm
from clients_app.models import Client, SupportConversation, SupportMessage
from clients_app.views import ClientBlocDetailView, LivreurProfilViewByClient
from demande_livraison_app.models import DemandeLivraison
from entreprise_app.models import Entreprise
from livreurs_app.models import Livreur
from zones_app.models import Zone


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
        self.assertContains(
            response,
            reverse("clients_app:detail-bloc", args=[self.bloc.pk]),
        )
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

    def test_livreur_profile_view_direct_delivery_request_post(self):
        livreur = Livreur.objects.get(user__telephone="70000803")
        zone_depart = Zone.objects.create(
            nom="Tampouy Centre",
            bloc=self.bloc,
            latitude=Decimal("12.390000"),
            longitude=Decimal("-1.540000"),
        )
        zone_arrivee = Zone.objects.create(
            nom="Tampouy Nord",
            bloc=self.bloc,
            latitude=Decimal("12.395000"),
            longitude=Decimal("-1.545000"),
        )

        response = self.client.post(
            reverse("clients_app:profil-livreur", args=[livreur.pk]),
            {
                "zone_depart": zone_depart.pk,
                "zone_arrivee": zone_arrivee.pk,
                "latitude_depart": "12.390000",
                "longitude_depart": "-1.540000",
                "whatsapp_destinataire": "+22678123456",
                "description_colis": "Colis direct pour Moussa",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("clients_app:tableau-de-bord"))

        demande = DemandeLivraison.objects.filter(whatsapp_destinataire="+22678123456").first()
        self.assertIsNotNone(demande)
        self.assertEqual(demande.livreur, livreur)
        self.assertEqual(demande.client, self.client_profile)
        self.assertEqual(demande.statut, "en_attente")
        self.assertEqual(demande.prix, Decimal("1000"))

    def test_toggle_favori_livreur_view(self):
        livreur = Livreur.objects.get(user__telephone="70000803")
        url = reverse("clients_app:toggle-favori-livreur", args=[livreur.pk])

        # 1. Ajouter aux favoris (like)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(livreur.favoris_de.filter(pk=self.client_profile.pk).exists())
        self.assertEqual(livreur.nb_ajout_favoris, 1)

        # 2. Retirer des favoris (unlike) via HTMX
        response_htmx = self.client.post(url, HTTP_HX_REQUEST="true")
        self.assertEqual(response_htmx.status_code, 200)
        self.assertFalse(livreur.favoris_de.filter(pk=self.client_profile.pk).exists())
        self.assertEqual(livreur.nb_ajout_favoris, 0)
        self.assertContains(response_htmx, "Ajouter aux favoris")

    def test_livreur_profile_displays_reviews_and_social_stats(self):
        livreur = Livreur.objects.get(user__telephone="70000803")
        livreur.favoris_de.add(self.client_profile)
        livreur.nb_livraisons = 42
        livreur.note_moyenne = Decimal("4.85")
        livreur.save()

        # Création d'une livraison factice pour rattacher un avis
        zone = Zone.objects.create(nom="Test Zone", bloc=self.bloc)
        demande = DemandeLivraison.objects.create(
            client=self.client_profile,
            livreur=livreur,
            zone_depart=zone,
            zone_arrivee=zone,
            latitude_depart=Decimal("12.39"),
            longitude_depart=Decimal("-1.54"),
            prix=Decimal("1000"),
            whatsapp_destinataire="+22670112233",
        )
        AvisLivreur.objects.create(
            demande_livraison=demande,
            client=self.client_profile,
            livreur=livreur,
            note=5,
            commentaire="Livreur rapide et ponctuel !",
        )

        response = self.client.get(reverse("clients_app:profil-livreur", args=[livreur.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "42")
        self.assertContains(response, "Livreur rapide et ponctuel !")
        self.assertContains(response, "Demander une course à Moussa")
        self.assertContains(response, "Favoris / Likes")


class ClientBlocDetailAndSupportChatTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create(
            telephone="70000931",
            first_name="Awa",
            last_name="Client",
            role="client",
        )
        self.client_profile = Client.objects.create(user=self.client_user)
        self.bloc = Blocs.objects.create(
            nom="Bloc Support Tampouy",
            quartier="tampouy",
            actif=True,
        )
        self.assistant_user = User.objects.create(
            telephone="70000932",
            first_name="Issa",
            last_name="Assistant",
            role="bloc_admin",
        )
        self.assistant = AdminBloc.objects.create(
            user=self.assistant_user,
            bloc=self.bloc,
            poste="assistant",
            actif=True,
        )
        self.zone = Zone.objects.create(
            nom="Tampouy Centre",
            bloc=self.bloc,
        )
        self.livreur_user = User.objects.create(
            telephone="70000933",
            first_name="Moussa",
            last_name="Livreur",
            role="livreur",
        )
        self.livreur = Livreur.objects.create(
            user=self.livreur_user,
            type_vehicule="moto",
            blocs=self.bloc,
            zone_actuelle=self.zone,
            actif=True,
        )
        self.client.force_login(self.client_user)

    def test_client_can_view_active_block_zones_and_active_drivers(self):
        inactive_user = User.objects.create(
            telephone="70000934",
            first_name="Livreur",
            last_name="Inactif",
            role="livreur",
        )
        Livreur.objects.create(
            user=inactive_user,
            type_vehicule="velo",
            blocs=self.bloc,
            actif=False,
        )

        response = self.client.get(
            reverse("clients_app:detail-bloc", args=[self.bloc.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIs(ClientBlocDetailView.model, Blocs)
        self.assertEqual(list(response.context["zones"]), [self.zone])
        self.assertEqual(list(response.context["livreurs"]), [self.livreur])
        self.assertTrue(response.context["assistant_disponible"])
        self.assertContains(response, "Tampouy Centre")
        self.assertContains(response, "Moussa Livreur")
        self.assertContains(response, "Contacter l’assistant")
        self.assertNotContains(response, "Livreur Inactif")

    def test_block_detail_is_hidden_for_inactive_blocks_and_non_clients(self):
        self.bloc.actif = False
        self.bloc.save(update_fields=["actif"])
        response = self.client.get(
            reverse("clients_app:detail-bloc", args=[self.bloc.pk])
        )
        self.assertEqual(response.status_code, 404)

        self.client.force_login(self.assistant_user)
        response = self.client.get(
            reverse("clients_app:detail-bloc", args=[self.bloc.pk])
        )
        self.assertEqual(response.status_code, 403)

    @patch("notifications_app.tasks.notifier_nouveau_message_support_task.delay")
    def test_client_can_start_and_exchange_messages_with_block_assistant(self, mock_push_delay):
        start_url = reverse(
            "clients_app:demarrer-chat-assistant",
            args=[self.bloc.pk],
        )
        response = self.client.post(start_url)
        conversation = SupportConversation.objects.get(
            client=self.client_profile,
            bloc=self.bloc,
        )
        chat_url = reverse("clients_app:chat-assistant", args=[conversation.pk])
        self.assertRedirects(response, chat_url)

        response = self.client.get(chat_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "clients_templates/support_chat.html")

        response = self.client.post(chat_url, {"content": "Bonjour, besoin d’aide."})
        self.assertRedirects(response, chat_url)
        client_message = SupportMessage.objects.get(conversation=conversation)
        self.assertEqual(client_message.sender, self.client_user)
        self.assertEqual(client_message.content, "Bonjour, besoin d’aide.")

        response = self.client.post(
            chat_url,
            {"content": "Message envoyé sans rechargement."},
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="support-chat-messages",
        )
        self.assertContains(response, "Message envoyé sans rechargement.")

        self.client.force_login(self.assistant_user)
        response = self.client.get(
            reverse("admins_app:tableau-de-bord-assistant-messages")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Awa Client")
        self.assertContains(response, "Message envoyé sans rechargement.")
        inbox_response = self.client.get(
            reverse("admins_app:tableau-de-bord-assistant-messages"),
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="assistant-support-conversations",
        )
        self.assertTemplateUsed(
            inbox_response,
            "partials/admins/assistant_support_conversations.html",
        )
        self.assertContains(inbox_response, "Ouvrir la conversation")

        response = self.client.get(chat_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Conversation avec Awa Client.")

        response = self.client.post(
            chat_url,
            {"content": "Bonjour Awa, nous sommes à votre écoute."},
        )
        self.assertRedirects(response, chat_url)
        self.assertEqual(conversation.messages.count(), 3)
        self.assertEqual(mock_push_delay.call_count, 3)

    def test_only_the_client_and_active_assistant_of_the_block_can_open_chat(self):
        conversation = SupportConversation.objects.create(
            client=self.client_profile,
            bloc=self.bloc,
        )
        other_user = User.objects.create(
            telephone="70000935",
            first_name="Autre",
            last_name="Client",
            role="client",
        )
        Client.objects.create(user=other_user)
        self.client.force_login(other_user)
        response = self.client.get(
            reverse("clients_app:chat-assistant", args=[conversation.pk])
        )
        self.assertEqual(response.status_code, 404)

        self.assistant.actif = False
        self.assistant.save(update_fields=["actif"])
        self.client.force_login(self.assistant_user)
        response = self.client.get(
            reverse("clients_app:chat-assistant", args=[conversation.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_chat_start_reports_when_block_has_no_active_assistant(self):
        self.assistant.actif = False
        self.assistant.save(update_fields=["actif"])

        response = self.client.post(
            reverse(
                "clients_app:demarrer-chat-assistant",
                args=[self.bloc.pk],
            ),
            follow=True,
        )

        self.assertContains(response, "Aucun assistant opérationnel")
        self.assertFalse(
            SupportConversation.objects.filter(
                client=self.client_profile,
                bloc=self.bloc,
            ).exists()
        )
