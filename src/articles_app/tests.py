from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from admins_app.models import AdminBloc
from auth_app.models import User
from blocs_app.models import Blocs
from entreprise_app.models import Entreprise, MembreAdminsEntreprise

from .forms import ArticleBlocAdminForm, ArticleEntrepriseForm
from .models import Article, StockBloc


class ArticleEntrepriseFormTests(TestCase):
    def setUp(self):
        self.entreprise_user = User.objects.create(
            telephone="70000111",
            first_name="Awa",
            last_name="Traore",
            role="entreprise",
        )
        self.entreprise = Entreprise.objects.create(
            user_principal=self.entreprise_user,
            nom_entreprise="Entreprise Faso",
            address="Ouagadougou",
        )
        self.article_data = {
            "nom": "Riz local",
            "description": "Sac de riz local",
            "prix": "2500.00",
            "disponible": "on",
            "en_bloc": "on",
        }

    def test_form_widgets_follow_project_styles(self):
        form = ArticleEntrepriseForm(user=self.entreprise_user)

        for field_name in ("nom", "description", "prix", "prix_promo", "date_expiration"):
            self.assertIn(
                "input-bordered" if field_name != "description" else "textarea-bordered",
                form.fields[field_name].widget.attrs["class"],
            )
            self.assertIn("w-full", form.fields[field_name].widget.attrs["class"])
        self.assertIn("file-input-bordered", form.fields["image"].widget.attrs["class"])
        self.assertEqual(
            form.fields["date_expiration"].widget.input_type,
            "datetime-local",
        )
        self.assertEqual(
            form.fields["disponible"].widget.attrs["class"],
            "checkbox checkbox-success rounded-lg",
        )

    def test_datetime_local_expiration_is_validated_and_saved(self):
        form = ArticleEntrepriseForm(
            data={
                **self.article_data,
                "date_expiration": "2026-10-24T16:30",
            },
            user=self.entreprise_user,
        )

        self.assertTrue(form.is_valid(), form.errors)
        article = form.save()

        self.assertEqual(
            article.date_expiration.strftime("%Y-%m-%dT%H:%M"),
            "2026-10-24T16:30",
        )

    def test_entreprise_user_creates_article_outside_a_bloc(self):
        form = ArticleEntrepriseForm(
            data=self.article_data,
            user=self.entreprise_user,
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn("entreprise", form.fields)
        self.assertNotIn("en_bloc", form.fields)

        article = form.save()

        self.assertEqual(article.entreprise, self.entreprise)
        self.assertFalse(article.en_bloc)

    def test_block_admin_form_creates_article_and_stock_in_the_admin_block(self):
        bloc = Blocs.objects.create(
            nom="Bloc Tampouy",
            ville="ouagadougou",
            quartier="tampouy",
        )
        bloc_admin = User.objects.create(
            telephone="70000114",
            first_name="Oumar",
            last_name="Kone",
            role="bloc_admin",
        )
        AdminBloc.objects.create(
            user=bloc_admin,
            bloc=bloc,
            actif=True,
        )
        form = ArticleBlocAdminForm(
            data=self.article_data | {"entreprise": self.entreprise.pk},
            user=bloc_admin,
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertIn(self.entreprise, form.fields["entreprise"].queryset)

        article = form.save()

        self.assertEqual(article.entreprise, self.entreprise)
        self.assertTrue(article.en_bloc)
        stock = StockBloc.objects.get(article=article)
        self.assertEqual(stock.bloc, bloc)
        self.assertEqual(stock.quantite, 0)

    def test_block_admin_form_rejects_user_without_active_block_profile(self):
        bloc_admin = User.objects.create(
            telephone="70000115",
            first_name="Issa",
            last_name="Sawadogo",
            role="bloc_admin",
        )
        form = ArticleBlocAdminForm(
            data=self.article_data | {"entreprise": self.entreprise.pk},
            user=bloc_admin,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "Aucun bloc actif n'est associé à cet administrateur.",
            form.non_field_errors(),
        )

    def test_block_admin_form_rejects_non_block_admin(self):
        form = ArticleBlocAdminForm(
            data=self.article_data | {"entreprise": self.entreprise.pk},
            user=self.entreprise_user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn(
            "Seuls les administrateurs de bloc peuvent utiliser ce formulaire.",
            form.non_field_errors(),
        )

    def test_entreprise_admin_creates_article_for_their_enterprise(self):
        admin_user = User.objects.create(
            telephone="70000112",
            first_name="Issa",
            last_name="Ouedraogo",
            role="entreprise_admin",
        )
        MembreAdminsEntreprise.objects.create(
            entreprise=self.entreprise,
            membre_admin=admin_user,
            ajoute_par=self.entreprise_user,
        )
        form = ArticleEntrepriseForm(
            data=self.article_data,
            user=admin_user,
        )

        self.assertTrue(form.is_valid(), form.errors)

        article = form.save()

        self.assertEqual(article.entreprise, self.entreprise)
        self.assertFalse(article.en_bloc)

    def test_unassociated_user_cannot_create_an_article(self):
        unrelated_user = User.objects.create(
            telephone="70000113",
            first_name="Mariam",
            last_name="Sawadogo",
            role="client",
        )
        form = ArticleEntrepriseForm(
            data=self.article_data,
            user=unrelated_user,
        )

        self.assertTrue(form.is_valid(), form.errors)
        with self.assertRaisesMessage(
            ValidationError,
            "Votre compte n'est associé à aucune entreprise autorisée.",
        ):
            form.save()


class AjouteArticleViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            telephone="70000211",
            first_name="Awa",
            last_name="Traore",
            role="entreprise",
        )
        self.entreprise = Entreprise.objects.create(
            user_principal=self.user,
            nom_entreprise="Entreprise Faso",
            address="Ouagadougou",
            palier="standard",
        )
        self.url = reverse("articles_app:ajoute_article")
        self.article_data = {
            "nom": "Riz local",
            "description": "Sac de riz local",
            "prix": "2500.00",
            "disponible": "on",
        }

    def test_entreprise_user_can_open_form_and_create_article_under_quota(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["quota_articles"], 15)
        self.assertEqual(response.context["nb_articles"], 0)
        self.assertContains(response, f'hx-post="{self.url}"')
        self.assertContains(response, 'hx-encoding="multipart/form-data"')

        response = self.client.post(self.url, self.article_data)

        self.assertRedirects(response, self.url)
        article = Article.objects.get(nom="Riz local")
        self.assertEqual(article.entreprise, self.entreprise)
        self.assertFalse(article.en_bloc)

    def test_htmx_article_creation_returns_success_partial_and_trigger(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.url,
            self.article_data,
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["HX-Trigger"], "articleCreated")
        self.assertTemplateUsed(response, "partials/result/article_success.html")
        self.assertContains(response, "Riz local")
        self.assertEqual(Article.objects.count(), 1)

    def test_htmx_invalid_form_returns_error_partial(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.url,
            {"nom": "Riz local"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "partials/result/article_error.html")
        self.assertContains(response, "Prix")
        self.assertEqual(Article.objects.count(), 0)

    def test_article_creation_is_blocked_when_quota_is_reached(self):
        Article.objects.bulk_create([
            Article(
                entreprise=self.entreprise,
                nom=f"Article {index}",
                prix="100.00",
            )
            for index in range(self.entreprise.quota_articles)
        ])
        self.client.force_login(self.user)

        response = self.client.post(self.url, self.article_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Le quota d&#x27;articles de votre entreprise est atteint.")
        self.assertEqual(Article.objects.filter(entreprise=self.entreprise).count(), 15)

    def test_htmx_article_creation_returns_quota_error_partial(self):
        Article.objects.bulk_create([
            Article(
                entreprise=self.entreprise,
                nom=f"Article {index}",
                prix="100.00",
            )
            for index in range(self.entreprise.quota_articles)
        ])
        self.client.force_login(self.user)

        response = self.client.post(
            self.url,
            self.article_data,
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "partials/result/article_error.html")
        self.assertContains(response, "quota d&#x27;articles")
        self.assertEqual(Article.objects.filter(entreprise=self.entreprise).count(), 15)

    def test_non_enterprise_user_is_forbidden(self):
        client_user = User.objects.create(
            telephone="70000212",
            first_name="Mariam",
            last_name="Sawadogo",
            role="client",
        )
        self.client.force_login(client_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)


class EntrepriseArticleListeViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            telephone="70000311",
            first_name="Awa",
            last_name="Traore",
            role="entreprise",
        )
        self.entreprise = Entreprise.objects.create(
            user_principal=self.user,
            nom_entreprise="Entreprise Faso",
            address="Ouagadougou",
            palier="standard",
        )
        self.url = reverse("articles_app:entreprise_articles")
        self.article = Article.objects.create(
            entreprise=self.entreprise,
            nom="Riz local",
            description="Riz de qualité",
            prix="2500.00",
            disponible=True,
            en_bloc=False,
        )
        self.client.force_login(self.user)

    def test_list_page_renders_filter_controls_and_company_articles(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "articles_templates/entreprise_articles.html",
        )
        self.assertContains(
            response,
            'hx-get="/articles/entreprise/"',
        )
        self.assertContains(response, "Riz local")
        self.assertEqual(list(response.context["articles"]), [self.article])

    def test_htmx_request_filters_search_availability_and_block_status(self):
        matching_article = Article.objects.create(
            entreprise=self.entreprise,
            nom="Riz blanc",
            description="Riz importé",
            prix="3000.00",
            disponible=True,
            en_bloc=True,
        )
        Article.objects.create(
            entreprise=self.entreprise,
            nom="Riz brun",
            description="Riz local",
            prix="2000.00",
            disponible=False,
            en_bloc=True,
        )

        response = self.client.get(
            self.url,
            {
                "q": "Riz",
                "disponible": "oui",
                "en_bloc": "oui",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "partials/articles/entreprise_articles_list.html",
        )
        self.assertContains(response, matching_article.nom)
        self.assertNotContains(response, self.article.nom)
        self.assertNotContains(response, "Riz brun")
        self.assertEqual(list(response.context["articles"]), [matching_article])

    def test_admin_member_can_view_their_company_articles(self):
        admin_user = User.objects.create(
            telephone="70000312",
            first_name="Issa",
            last_name="Ouedraogo",
            role="entreprise_admin",
        )
        MembreAdminsEntreprise.objects.create(
            entreprise=self.entreprise,
            membre_admin=admin_user,
            ajoute_par=self.user,
        )
        self.client.force_login(admin_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["articles"]), [self.article])

    def test_other_company_articles_are_not_visible(self):
        other_user = User.objects.create(
            telephone="70000313",
            first_name="Mariam",
            last_name="Sawadogo",
            role="entreprise",
        )
        other_entreprise = Entreprise.objects.create(
            user_principal=other_user,
            nom_entreprise="Autre entreprise",
            address="Bobo-Dioulasso",
        )
        Article.objects.create(
            entreprise=other_entreprise,
            nom="Article privé",
            prix="100.00",
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["articles"]), [self.article])
        self.assertNotContains(response, "Article privé")

    def test_non_enterprise_user_is_forbidden(self):
        client_user = User.objects.create(
            telephone="70000314",
            first_name="Client",
            last_name="Test",
            role="client",
        )
        self.client.force_login(client_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)


class EntrepriseArticleModificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            telephone="70000411",
            first_name="Awa",
            last_name="Traore",
            role="entreprise",
        )
        self.entreprise = Entreprise.objects.create(
            user_principal=self.user,
            nom_entreprise="Entreprise Faso",
            address="Ouagadougou",
            palier="standard",
        )
        self.article = Article.objects.create(
            entreprise=self.entreprise,
            nom="Riz local",
            description="Riz de qualité",
            prix="2500.00",
            disponible=True,
            en_bloc=True,
        )
        self.update_url = reverse(
            "articles_app:modifier_article",
            args=[self.article.pk],
        )
        self.delete_url = reverse(
            "articles_app:supprimer_article",
            args=[self.article.pk],
        )
        self.article_data = {
            "nom": "Riz local modifié",
            "description": "Riz de qualité supérieure",
            "prix": "3000.00",
            "disponible": "on",
        }
        self.client.force_login(self.user)

    def test_update_view_renders_article_form(self):
        response = self.client.get(self.update_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "articles_templates/article_form.html")
        self.assertContains(response, 'hx-post="' + self.update_url + '"')
        self.assertEqual(response.context["article"], self.article)

    def test_update_saves_article_and_preserves_block_assignment(self):
        response = self.client.post(self.update_url, self.article_data)

        self.assertRedirects(response, reverse("articles_app:entreprise_articles"))
        self.article.refresh_from_db()
        self.assertEqual(self.article.nom, "Riz local modifié")
        self.assertEqual(self.article.prix, Decimal("3000.00"))
        self.assertTrue(self.article.en_bloc)

    def test_htmx_update_returns_success_partial_and_trigger(self):
        response = self.client.post(
            self.update_url,
            self.article_data,
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["HX-Trigger"], "articleUpdated")
        self.assertTemplateUsed(
            response,
            "partials/result/article_updated.html",
        )
        self.article.refresh_from_db()
        self.assertEqual(self.article.nom, "Riz local modifié")

    def test_htmx_invalid_update_returns_error_partial(self):
        response = self.client.post(
            self.update_url,
            {"nom": "Riz local modifié"},
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "partials/result/article_update_error.html",
        )
        self.assertContains(response, "Prix")
        self.article.refresh_from_db()
        self.assertEqual(self.article.nom, "Riz local")

    def test_delete_view_renders_confirmation_page(self):
        response = self.client.get(self.delete_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "articles_templates/article_confirm_delete.html",
        )

    def test_htmx_delete_returns_trigger_and_deletes_article(self):
        response = self.client.post(
            self.delete_url,
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.headers["HX-Trigger"], "articleDeleted")
        self.assertFalse(Article.objects.filter(pk=self.article.pk).exists())

    def test_user_cannot_update_or_delete_another_enterprise_article(self):
        other_user = User.objects.create(
            telephone="70000412",
            first_name="Mariam",
            last_name="Sawadogo",
            role="entreprise",
        )
        other_entreprise = Entreprise.objects.create(
            user_principal=other_user,
            nom_entreprise="Autre entreprise",
            address="Bobo-Dioulasso",
        )
        other_article = Article.objects.create(
            entreprise=other_entreprise,
            nom="Article privé",
            prix="100.00",
        )
        update_url = reverse(
            "articles_app:modifier_article",
            args=[other_article.pk],
        )
        delete_url = reverse(
            "articles_app:supprimer_article",
            args=[other_article.pk],
        )

        self.assertEqual(self.client.get(update_url).status_code, 404)
        self.assertEqual(self.client.post(delete_url).status_code, 404)
        self.assertTrue(Article.objects.filter(pk=other_article.pk).exists())

    def test_non_enterprise_user_cannot_update_or_delete_articles(self):
        client_user = User.objects.create(
            telephone="70000413",
            first_name="Client",
            last_name="Test",
            role="client",
        )
        self.client.force_login(client_user)

        self.assertEqual(self.client.get(self.update_url).status_code, 403)
        self.assertEqual(self.client.post(self.delete_url).status_code, 403)
        self.assertTrue(Article.objects.filter(pk=self.article.pk).exists())
