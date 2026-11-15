from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from articles_app.models import Article, StockBloc
from auth_app.models import User
from blocs_app.models import Blocs
from clients_app.models import Client
from entreprise_app.models import Entreprise
from zones_app.models import Zone

from .models import ArticlePanier, Commande, LigneCommande, Panier


class PanierCommandeModelTests(TestCase):
    def setUp(self):
        self.client_user = User.objects.create(
            telephone="70000101",
            first_name="Awa",
            last_name="Client",
            role="client",
        )
        self.client_profil = Client.objects.create(user=self.client_user)
        entreprise_user = User.objects.create(
            telephone="70000102",
            first_name="Moussa",
            last_name="Vendeur",
            role="entreprise",
        )
        self.entreprise = Entreprise.objects.create(
            user_principal=entreprise_user,
            nom_entreprise="Entreprise Faso",
            address="Ouagadougou",
        )
        self.article = Article.objects.create(
            entreprise=self.entreprise,
            nom="Riz local",
            prix=Decimal("2500.00"),
            prix_promo=Decimal("2000.00"),
        )
        self.panier = Panier.objects.create(client=self.client_profil)
        self.bloc = Blocs.objects.create(
            nom="Bloc Tampouy",
            ville="ouagadougou",
            quartier="tampouy",
        )
        self.zone = Zone.objects.create(
            nom="Tampouy",
            bloc=self.bloc,
            latitude=Decimal("12.400000"),
            longitude=Decimal("-1.500000"),
        )
        self.stock = StockBloc.objects.create(
            article=self.article,
            bloc=self.bloc,
            quantite=5,
        )

    def test_total_panier_applies_current_promotion(self):
        ArticlePanier.objects.create(
            panier=self.panier,
            article=self.article,
            quantite=3,
        )

        self.assertEqual(self.panier.total_panier(), Decimal("6000.00"))

    def test_client_can_open_cart_page(self):
        ArticlePanier.objects.create(
            panier=self.panier,
            article=self.article,
            quantite=2,
        )
        self.client.force_login(self.client_user)

        response = self.client.get(reverse("panier_app:panier"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mon panier")
        self.assertContains(response, "Riz local")
        self.assertContains(response, "Sous-total")
        self.assertContains(response, "Total des articles")
        self.assertContains(response, 'id="validation-commande-modal"')
        self.assertContains(response, "Capturer ma position")
        self.assertContains(response, 'x-model="latitude"')
        self.assertContains(response, 'x-model="longitude"')
        self.assertTemplateUsed(
            response,
            "partials/panier/gps_fallback_notice.html",
        )

    def test_client_can_validate_cart_and_open_order_detail(self):
        ArticlePanier.objects.create(
            panier=self.panier,
            article=self.article,
            quantite=2,
        )
        self.client.force_login(self.client_user)

        response = self.client.post(
            reverse("panier_app:valider_commande"),
            {
                "zone_arrivee": self.zone.pk,
                "latitude": "12.401000",
                "longitude": "-1.501000",
            },
        )

        commande = Commande.objects.get(client=self.client_profil)
        self.assertRedirects(
            response,
            reverse(
                "panier_app:detail_commande",
                args=[commande.reference],
            ),
        )
        self.assertEqual(commande.statut, Commande.STATUT_EN_ATTENTE_PAIEMENT)
        self.assertEqual(
            commande.statut_paiement,
            Commande.PAIEMENT_NON_INITIE,
        )
        self.assertEqual(commande.zone_arrivee, self.zone)
        self.assertEqual(commande.latitude_livraison, Decimal("12.401000"))
        self.assertEqual(commande.longitude_livraison, Decimal("-1.501000"))
        self.assertEqual(commande.montant_produits, Decimal("4000.00"))
        self.assertEqual(commande.frais_livraison, Decimal("0.00"))
        self.assertEqual(commande.total_a_payer, Decimal("4000.00"))
        self.assertEqual(commande.lignes.count(), 1)
        ligne = commande.lignes.get()
        self.assertEqual(ligne.quantite, 2)
        self.assertEqual(ligne.prix_unitaire, Decimal("2000.00"))
        self.panier.refresh_from_db()
        self.assertEqual(self.panier.statut, Panier.STATUT_COMMANDE)

    def test_checkout_uses_selected_zone_coordinates_when_gps_is_missing(self):
        ArticlePanier.objects.create(panier=self.panier, article=self.article)
        self.client.force_login(self.client_user)

        response = self.client.post(
            reverse("panier_app:valider_commande"),
            {"zone_arrivee": self.zone.pk},
        )

        commande = Commande.objects.get(client=self.client_profil)
        self.assertRedirects(
            response,
            reverse(
                "panier_app:detail_commande",
                args=[commande.reference],
            ),
        )
        self.assertEqual(commande.latitude_livraison, self.zone.latitude)
        self.assertEqual(commande.longitude_livraison, self.zone.longitude)

    def test_checkout_rejects_order_when_stock_is_insufficient(self):
        ArticlePanier.objects.create(
            panier=self.panier,
            article=self.article,
            quantite=6,
        )
        self.client.force_login(self.client_user)

        response = self.client.post(
            reverse("panier_app:valider_commande"),
            {
                "zone_arrivee": self.zone.pk,
                "latitude": "12.401000",
                "longitude": "-1.501000",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Stock insuffisant", status_code=400)
        self.assertFalse(Commande.objects.exists())
        self.panier.refresh_from_db()
        self.assertEqual(self.panier.statut, Panier.STATUT_ACTIF)

    def test_checkout_uses_article_quantity_for_off_block_items(self):
        self.stock.delete()
        self.article.en_bloc = False
        self.article.quantite_disponible = 2
        self.article.save(update_fields=["en_bloc", "quantite_disponible"])
        ArticlePanier.objects.create(
            panier=self.panier,
            article=self.article,
            quantite=2,
        )
        self.client.force_login(self.client_user)

        response = self.client.post(
            reverse("panier_app:valider_commande"),
            {
                "zone_arrivee": self.zone.pk,
                "latitude": "12.401000",
                "longitude": "-1.501000",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Commande.objects.count(), 1)

    def test_htmx_checkout_error_returns_feedback_partial(self):
        ArticlePanier.objects.create(
            panier=self.panier,
            article=self.article,
            quantite=6,
        )
        self.client.force_login(self.client_user)

        response = self.client.post(
            reverse("panier_app:valider_commande"),
            {
                "zone_arrivee": self.zone.pk,
                "latitude": "12.401000",
                "longitude": "-1.501000",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="commande-feedback"')
        self.assertContains(response, "Stock insuffisant")
        self.assertFalse(Commande.objects.exists())

    def test_htmx_checkout_redirects_to_order_detail(self):
        ArticlePanier.objects.create(panier=self.panier, article=self.article)
        self.client.force_login(self.client_user)

        response = self.client.post(
            reverse("panier_app:valider_commande"),
            {
                "zone_arrivee": self.zone.pk,
                "latitude": "12.401000",
                "longitude": "-1.501000",
            },
            HTTP_HX_REQUEST="true",
        )

        commande = Commande.objects.get(client=self.client_profil)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            response["HX-Redirect"],
            reverse(
                "panier_app:detail_commande",
                args=[commande.reference],
            ),
        )

    def test_checkout_requires_gps_or_zone_coordinates(self):
        zone_sans_gps = Zone.objects.create(
            nom="Zone sans coordonnées",
            bloc=self.bloc,
        )
        ArticlePanier.objects.create(panier=self.panier, article=self.article)
        self.client.force_login(self.client_user)

        response = self.client.post(
            reverse("panier_app:valider_commande"),
            {"zone_arrivee": zone_sans_gps.pk},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "zone_arrivee",
            response.context["form_commande"].errors,
        )
        self.assertTrue(
            any(
                "coordonnées GPS" in error
                for error in response.context["form_commande"].errors[
                    "zone_arrivee"
                ]
            )
        )
        self.assertFalse(Commande.objects.exists())

    def test_client_can_view_only_their_own_order(self):
        commande = Commande.objects.create(
            panier=self.panier,
            client=self.client_profil,
            zone_arrivee=self.zone,
            latitude_livraison=self.zone.latitude,
            longitude_livraison=self.zone.longitude,
            montant_produits=Decimal("2000.00"),
            total_a_payer=Decimal("2000.00"),
        )
        self.client.force_login(self.client_user)

        response = self.client.get(
            reverse(
                "panier_app:detail_commande",
                args=[commande.reference],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(commande.reference))
        self.assertContains(response, "Paiement bientôt disponible")
        self.assertContains(response, "Suivi de la commande")
        self.assertContains(response, "En attente de paiement")
        self.assertContains(response, "aria-current=\"step\"")
        self.assertContains(response, self.zone.nom)
        self.assertContains(response, "Latitude :")
        self.assertContains(response, "Longitude :")
        self.assertContains(response, str(commande.latitude_livraison.normalize()))
        self.assertContains(response, str(commande.longitude_livraison.normalize()))
        self.assertContains(response, self.zone.bloc.nom)
        self.assertContains(response, "Voir la position sur la carte")

    def test_order_timeline_tracks_current_status_and_cancellation(self):
        commande = Commande.objects.create(
            panier=self.panier,
            client=self.client_profil,
            zone_arrivee=self.zone,
            latitude_livraison=self.zone.latitude,
            longitude_livraison=self.zone.longitude,
            montant_produits=Decimal("2000.00"),
            total_a_payer=Decimal("2000.00"),
            statut=Commande.STATUT_EN_LIVRAISON,
        )
        self.client.force_login(self.client_user)

        response = self.client.get(
            reverse(
                "panier_app:detail_commande",
                args=[commande.reference],
            )
        )

        self.assertEqual(response.status_code, 200)
        etapes = response.context["etapes_commande"]
        self.assertTrue(etapes[0]["terminee"])
        self.assertTrue(etapes[1]["terminee"])
        self.assertTrue(etapes[2]["terminee"])
        self.assertTrue(etapes[3]["actuelle"])
        self.assertFalse(etapes[4]["terminee"])

        commande.statut = Commande.STATUT_ANNULEE
        commande.save(update_fields=["statut"])
        response = self.client.get(
            reverse(
                "panier_app:detail_commande",
                args=[commande.reference],
            )
        )
        self.assertTrue(response.context["commande_annulee"])
        self.assertContains(response, "Cette commande a été annulée.")

    def test_client_cannot_view_another_clients_order(self):
        commande = Commande.objects.create(
            panier=self.panier,
            client=self.client_profil,
            zone_arrivee=self.zone,
            latitude_livraison=self.zone.latitude,
            longitude_livraison=self.zone.longitude,
            montant_produits=Decimal("2000.00"),
            total_a_payer=Decimal("2000.00"),
        )
        other_user = User.objects.create(
            telephone="70000104",
            first_name="Mariam",
            last_name="Autre",
            role="client",
        )
        Client.objects.create(user=other_user)
        self.client.force_login(other_user)

        response = self.client.get(
            reverse(
                "panier_app:detail_commande",
                args=[commande.reference],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_client_can_have_only_one_active_cart(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Panier.objects.create(client=self.client_profil)

    def test_article_cannot_be_added_twice_to_same_cart(self):
        ArticlePanier.objects.create(panier=self.panier, article=self.article)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ArticlePanier.objects.create(
                    panier=self.panier,
                    article=self.article,
                )

    def test_order_line_keeps_product_and_price_snapshot(self):
        commande = Commande.objects.create(
            panier=self.panier,
            client=self.client_profil,
            zone_arrivee=self.zone,
            latitude_livraison=Decimal("12.401000"),
            longitude_livraison=Decimal("-1.501000"),
            montant_produits=Decimal("2000.00"),
            total_a_payer=Decimal("2000.00"),
        )
        ligne = LigneCommande.objects.create(
            commande=commande,
            article=self.article,
            entreprise=self.entreprise,
            nom_article=self.article.nom,
            nom_entreprise=self.entreprise.nom_entreprise,
            quantite=1,
            prix_unitaire=self.article.prix_actuel,
        )

        self.article.nom = "Nouveau nom"
        self.article.prix = Decimal("3000.00")
        self.article.save()

        ligne.refresh_from_db()
        self.assertEqual(ligne.nom_article, "Riz local")
        self.assertEqual(ligne.prix_unitaire, Decimal("2000.00"))
        self.assertEqual(ligne.sous_total, Decimal("2000.00"))

    def test_client_can_add_article_and_repeated_add_increments_quantity(self):
        self.client.force_login(self.client_user)
        url = reverse("panier_app:ajouter_panier", args=[self.article.pk])

        first_response = self.client.post(url, HTTP_HX_REQUEST="true")
        second_response = self.client.post(url, HTTP_HX_REQUEST="true")

        self.assertEqual(first_response.status_code, 200)
        self.assertContains(first_response, "a été ajouté au panier")
        self.assertContains(second_response, 'id="panier-count-badge"')
        ligne = ArticlePanier.objects.get(panier=self.panier)
        self.assertEqual(ligne.quantite, 2)

    def test_client_can_update_and_remove_a_cart_line(self):
        ligne = ArticlePanier.objects.create(
            panier=self.panier,
            article=self.article,
            quantite=2,
        )
        self.client.force_login(self.client_user)
        url = reverse("panier_app:modifier_panier", args=[ligne.pk])

        response = self.client.post(
            url,
            {"quantite": "4"},
            HTTP_HX_REQUEST="true",
        )
        ligne.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ligne.quantite, 4)

        response = self.client.post(
            url,
            {"quantite": "0"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ArticlePanier.objects.filter(pk=ligne.pk).exists())
        self.assertContains(response, "Votre panier est vide")

    def test_invalid_quantity_is_reported_without_changing_the_line(self):
        ligne = ArticlePanier.objects.create(
            panier=self.panier,
            article=self.article,
            quantite=2,
        )
        self.client.force_login(self.client_user)

        response = self.client.post(
            reverse("panier_app:modifier_panier", args=[ligne.pk]),
            {"quantite": "invalid"},
            HTTP_HX_REQUEST="true",
        )

        ligne.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "quantité entière valide")
        self.assertEqual(ligne.quantite, 2)

    def test_client_can_empty_active_cart(self):
        ArticlePanier.objects.create(panier=self.panier, article=self.article)
        self.client.force_login(self.client_user)

        response = self.client.post(
            reverse("panier_app:vider_panier"),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.panier.lignes.exists())
        self.assertContains(response, "Votre panier a été vidé")

    def test_unavailable_article_cannot_be_added(self):
        self.stock.quantite = 0
        self.stock.save()
        self.client.force_login(self.client_user)

        response = self.client.post(
            reverse("panier_app:ajouter_panier", args=[self.article.pk]),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "plus disponible dans le catalogue")
        self.assertFalse(self.panier.lignes.exists())

    def test_client_cannot_change_another_clients_cart_line(self):
        ligne = ArticlePanier.objects.create(
            panier=self.panier,
            article=self.article,
        )
        other_user = User.objects.create(
            telephone="70000103",
            first_name="Issa",
            last_name="Autre",
            role="client",
        )
        Client.objects.create(user=other_user)
        self.client.force_login(other_user)

        response = self.client.post(
            reverse("panier_app:modifier_panier", args=[ligne.pk]),
            {"quantite": "4"},
        )

        self.assertEqual(response.status_code, 404)
        ligne.refresh_from_db()
        self.assertEqual(ligne.quantite, 1)
