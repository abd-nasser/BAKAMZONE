from decimal import Decimal
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage

from articles_app.models import Article
from entreprise_app.models import Entreprise, MembreAdminsEntreprise, RetraitEntreprise
from superuser_app.views import (
    ListeEntrepriseViewBySuperUser,
    EntrepriseDetailViewBySuperUser,
    TraiterDemandeRetraitView,
    SuperuserRequiredMixin,
)

User = get_user_model()


class SuperuserRequiredMixinTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.superuser = User.objects.create_superuser(
            telephone="+22670000001",
            password="password123",
            first_name="Super",
            last_name="Admin",
        )
        self.client_user = User.objects.create_user(
            telephone="+22670000002",
            password="password123",
            first_name="Simple",
            last_name="Client",
            role="client",
        )

    def test_anonymous_user_redirected(self):
        request = self.factory.get("/superuser/entreprises/")
        request.user = type("AnonymousUser", (), {"is_authenticated": False, "is_active": False, "is_superuser": False})()
        
        # Setup session and messages support on request
        setattr(request, "session", {})
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        response = ListeEntrepriseViewBySuperUser.as_view()(request)
        self.assertEqual(response.status_code, 302)

    def test_non_superuser_redirected_to_home(self):
        request = self.factory.get("/superuser/entreprises/")
        request.user = self.client_user
        
        setattr(request, "session", {})
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        response = ListeEntrepriseViewBySuperUser.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")

    def test_superuser_granted_access(self):
        request = self.factory.get("/superuser/entreprises/")
        request.user = self.superuser

        setattr(request, "session", {})
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        response = ListeEntrepriseViewBySuperUser.as_view()(request)
        self.assertEqual(response.status_code, 200)


class ListeEntrepriseViewBySuperUserTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.superuser = User.objects.create_superuser(
            telephone="+22670000099",
            password="password123",
            first_name="Super",
            last_name="Boss",
        )
        self.user_ent1 = User.objects.create_user(
            telephone="+22671111111",
            password="password123",
            first_name="Gerant",
            last_name="Alpha",
            role="entreprise",
        )
        self.entreprise1 = Entreprise.objects.create(
            user_principal=self.user_ent1,
            nom_entreprise="Alpha Distribution",
            rc_number="BF-OUA-01-2026",
            address="Tampouy, Secteur 21",
            palier="standard",
            subscription_active=True,
        )
        self.user_ent2 = User.objects.create_user(
            telephone="+22672222222",
            password="password123",
            first_name="Gerant",
            last_name="Beta",
            role="entreprise",
        )
        self.entreprise2 = Entreprise.objects.create(
            user_principal=self.user_ent2,
            nom_entreprise="Beta Industrie",
            rc_number="BF-OUA-02-2026",
            address="Kamboinsin",
            palier="pro",
            subscription_active=False,
        )

        # Articles
        Article.objects.create(
            entreprise=self.entreprise1,
            nom="Article A1",
            prix=Decimal("1500.00"),
            disponible=True,
        )
        Article.objects.create(
            entreprise=self.entreprise1,
            nom="Article A2 indisponible",
            prix=Decimal("2000.00"),
            disponible=False,
        )

        # Demande de retrait pour entreprise 1
        self.retrait_en_attente = RetraitEntreprise.objects.create(
            entreprise=self.entreprise1,
            montant=Decimal("25000.00"),
            statut=RetraitEntreprise.STATUT_EN_ATTENTE,
        )
        # Demande de retrait payée pour entreprise 2
        self.retrait_paye = RetraitEntreprise.objects.create(
            entreprise=self.entreprise2,
            montant=Decimal("50000.00"),
            statut=RetraitEntreprise.STATUT_PAYE,
        )

    def test_list_contains_annotated_fields(self):
        request = self.factory.get("/superuser/entreprises/")
        request.user = self.superuser
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))

        response = ListeEntrepriseViewBySuperUser.as_view()(request)
        self.assertEqual(response.status_code, 200)

        entreprises = list(response.context_data["entreprises"])
        self.assertEqual(len(entreprises), 2)

        # Alpha doit avoir 1 retrait en attente de 25000 et 1 article disponible
        ent1 = next(e for e in entreprises if e.pk == self.entreprise1.pk)
        self.assertEqual(ent1.nb_articles_disponibles, 1)
        self.assertEqual(ent1.nb_retraits_attente, 1)
        self.assertEqual(ent1.montant_retraits_attente, Decimal("25000.00"))

        # Beta ne doit avoir aucun retrait en attente
        ent2 = next(e for e in entreprises if e.pk == self.entreprise2.pk)
        self.assertEqual(ent2.nb_retraits_attente, 0)
        self.assertEqual(ent2.montant_retraits_attente, Decimal("0.00"))

        # Contexte global
        self.assertEqual(response.context_data["total_retraits_en_attente"], 1)
        self.assertEqual(response.context_data["montant_total_retraits_en_attente"], Decimal("25000.00"))

    def test_dynamic_search_filter(self):
        # Recherche par nom "Alpha"
        request = self.factory.get("/superuser/entreprises/?q=Alpha")
        request.user = self.superuser
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))

        response = ListeEntrepriseViewBySuperUser.as_view()(request)
        entreprises = list(response.context_data["entreprises"])
        self.assertEqual(len(entreprises), 1)
        self.assertEqual(entreprises[0].nom_entreprise, "Alpha Distribution")

    def test_dynamic_retrait_filter(self):
        # Filtrer uniquement les entreprises avec retraits en attente
        request = self.factory.get("/superuser/entreprises/?retrait=en_attente")
        request.user = self.superuser
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))

        response = ListeEntrepriseViewBySuperUser.as_view()(request)
        entreprises = list(response.context_data["entreprises"])
        self.assertEqual(len(entreprises), 1)
        self.assertEqual(entreprises[0].pk, self.entreprise1.pk)

    def test_htmx_request_returns_partial_template(self):
        # Requête HTMX dynamique
        request = self.factory.get("/superuser/entreprises/?q=Beta", HTTP_HX_REQUEST="true")
        request.user = self.superuser
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))

        view = ListeEntrepriseViewBySuperUser()
        view.setup(request)
        template_names = view.get_template_names()

        self.assertIn("partials/superuser/entreprise_list_results.html", template_names)
        self.assertNotIn("superuser_template/entreprise_list.html", template_names)

    def test_standard_request_returns_full_template(self):
        # Requête navigateur standard
        request = self.factory.get("/superuser/entreprises/")
        request.user = self.superuser
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))

        view = ListeEntrepriseViewBySuperUser()
        view.setup(request)
        template_names = view.get_template_names()

        self.assertIn("superuser_template/entreprise_list.html", template_names)


class EntrepriseDetailViewBySuperUserTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.superuser = User.objects.create_superuser(
            telephone="+22670000088",
            password="password123",
            first_name="Super",
            last_name="Boss",
        )
        self.client_user = User.objects.create_user(
            telephone="+22670000077",
            password="password123",
            first_name="Client",
            last_name="User",
            role="client",
        )
        self.user_ent = User.objects.create_user(
            telephone="+22673333333",
            password="password123",
            first_name="Patron",
            last_name="Entreprise",
            role="entreprise",
        )
        self.entreprise = Entreprise.objects.create(
            user_principal=self.user_ent,
            nom_entreprise="Test Distribution SARL",
            rc_number="BF-OUA-03-2026",
            address="1200 Logements, Ouagadougou",
            palier="pro",
            subscription_active=True,
        )

        # Articles
        self.art_bloc = Article.objects.create(
            entreprise=self.entreprise,
            nom="Produit en Bloc",
            prix=Decimal("3000.00"),
            en_bloc=True,
            disponible=True,
        )
        self.art_hors_bloc = Article.objects.create(
            entreprise=self.entreprise,
            nom="Produit Hors Bloc",
            prix=Decimal("5000.00"),
            en_bloc=False,
            disponible=True,
        )

        # Administrateur secondaire
        self.user_admin2 = User.objects.create_user(
            telephone="+22674444444",
            password="password123",
            first_name="Adjoint",
            last_name="Admin",
            role="entreprise_admin",
        )
        self.admin_membre = MembreAdminsEntreprise.objects.create(
            entreprise=self.entreprise,
            membre_admin=self.user_admin2,
            ajoute_par=self.user_ent,
        )

        # Retraits
        self.retrait1 = RetraitEntreprise.objects.create(
            entreprise=self.entreprise,
            montant=Decimal("15000.00"),
            statut=RetraitEntreprise.STATUT_EN_ATTENTE,
        )
        self.retrait2 = RetraitEntreprise.objects.create(
            entreprise=self.entreprise,
            montant=Decimal("40000.00"),
            statut=RetraitEntreprise.STATUT_PAYE,
        )

    def test_anonymous_access_denied(self):
        request = self.factory.get(f"/superuser/entreprises/{self.entreprise.pk}/")
        request.user = type("AnonymousUser", (), {"is_authenticated": False, "is_active": False, "is_superuser": False})()
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))

        response = EntrepriseDetailViewBySuperUser.as_view()(request, pk=self.entreprise.pk)
        self.assertEqual(response.status_code, 302)

    def test_non_superuser_access_denied(self):
        request = self.factory.get(f"/superuser/entreprises/{self.entreprise.pk}/")
        request.user = self.client_user
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))

        response = EntrepriseDetailViewBySuperUser.as_view()(request, pk=self.entreprise.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")

    def test_superuser_access_and_context_data(self):
        request = self.factory.get(f"/superuser/entreprises/{self.entreprise.pk}/")
        request.user = self.superuser
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))

        response = EntrepriseDetailViewBySuperUser.as_view()(request, pk=self.entreprise.pk)
        self.assertEqual(response.status_code, 200)

        context = response.context_data
        self.assertEqual(context["entreprise"], self.entreprise)

        # Vérification des finances
        self.assertIn("solde_data", context)
        self.assertIn("montant_disponible", context["solde_data"])

        # Vérification des articles
        self.assertEqual(context["total_articles"], 2)
        self.assertEqual(context["articles_en_bloc"].count(), 1)
        self.assertEqual(context["articles_hors_bloc"].count(), 1)

        # Vérification des membres admins
        self.assertEqual(len(context["membres_admin"]), 1)
        self.assertEqual(context["membres_admin"][0].membre_admin, self.user_admin2)

        # Vérification des retraits
        self.assertEqual(context["retraits"].count(), 2)
        self.assertEqual(context["nb_retraits_en_attente"], 1)
        self.assertEqual(context["retraits_en_attente"].first(), self.retrait1)
        self.assertEqual(context["retraits_traites"].first(), self.retrait2)


class TraiterDemandeRetraitViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.superuser = User.objects.create_superuser(
            telephone="+22670000066",
            password="password123",
            first_name="Grand",
            last_name="Superuser",
        )
        self.client_user = User.objects.create_user(
            telephone="+22670000055",
            password="password123",
            first_name="Simple",
            last_name="User",
            role="client",
        )
        self.user_ent = User.objects.create_user(
            telephone="+22675555555",
            password="password123",
            first_name="Directeur",
            last_name="Commerce",
            role="entreprise",
        )
        self.entreprise = Entreprise.objects.create(
            user_principal=self.user_ent,
            nom_entreprise="Commerce Express SARL",
            rc_number="BF-OUA-04-2026",
            address="Zone du Bois, Ouagadougou",
            palier="standard",
            subscription_active=True,
        )
        self.retrait = RetraitEntreprise.objects.create(
            entreprise=self.entreprise,
            montant=Decimal("35000.00"),
            statut=RetraitEntreprise.STATUT_EN_ATTENTE,
        )

    def test_access_denied_for_client(self):
        request = self.factory.post(
            f"/superuser/retraits/{self.retrait.pk}/traiter/",
            {"action": "approuver", "commentaire": "OK"},
        )
        request.user = self.client_user
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))

        response = TraiterDemandeRetraitView.as_view()(request, pk=self.retrait.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")

        # La demande ne doit pas avoir changé
        self.retrait.refresh_from_db()
        self.assertEqual(self.retrait.statut, RetraitEntreprise.STATUT_EN_ATTENTE)

    def test_approuver_retrait_avec_commentaire(self):
        request = self.factory.post(
            f"/superuser/retraits/{self.retrait.pk}/traiter/",
            {"action": "approuver", "commentaire": "Virement validé par la trésorerie"},
        )
        request.user = self.superuser
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))

        response = TraiterDemandeRetraitView.as_view()(request, pk=self.retrait.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/superuser/entreprises/{self.entreprise.pk}/")

        self.retrait.refresh_from_db()
        self.assertEqual(self.retrait.statut, RetraitEntreprise.STATUT_APPROUVE)
        self.assertEqual(self.retrait.commentaire, "Virement validé par la trésorerie")
        self.assertEqual(self.retrait.traite_par, self.superuser)
        self.assertIsNotNone(self.retrait.date_traitement)

    def test_marquer_payer_retrait(self):
        # Passage au statut paye
        request = self.factory.post(
            f"/superuser/retraits/{self.retrait.pk}/traiter/",
            {"action": "payer", "commentaire": "Fonds reçus par le gérant"},
        )
        request.user = self.superuser
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))

        response = TraiterDemandeRetraitView.as_view()(request, pk=self.retrait.pk)
        self.assertEqual(response.status_code, 302)

        self.retrait.refresh_from_db()
        self.assertEqual(self.retrait.statut, RetraitEntreprise.STATUT_PAYE)
        self.assertEqual(self.retrait.traite_par, self.superuser)

    def test_rejeter_retrait_avec_commentaire(self):
        request = self.factory.post(
            f"/superuser/retraits/{self.retrait.pk}/traiter/",
            {"action": "rejeter", "commentaire": "Coordonnées de paiement non conformes"},
        )
        request.user = self.superuser
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))

        response = TraiterDemandeRetraitView.as_view()(request, pk=self.retrait.pk)
        self.assertEqual(response.status_code, 302)

        self.retrait.refresh_from_db()
        self.assertEqual(self.retrait.statut, RetraitEntreprise.STATUT_REJETE)
        self.assertEqual(self.retrait.commentaire, "Coordonnées de paiement non conformes")
        self.assertEqual(self.retrait.traite_par, self.superuser)

    def test_rejeter_retrait_sans_commentaire_echoue(self):
        request = self.factory.post(
            f"/superuser/retraits/{self.retrait.pk}/traiter/",
            {"action": "rejeter", "commentaire": ""},
        )
        request.user = self.superuser
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))

        response = TraiterDemandeRetraitView.as_view()(request, pk=self.retrait.pk)
        self.assertEqual(response.status_code, 302)

        # Le retrait doit rester en attente car le motif était manquant
        self.retrait.refresh_from_db()
        self.assertEqual(self.retrait.statut, RetraitEntreprise.STATUT_EN_ATTENTE)
        self.assertIsNone(self.retrait.date_traitement)


