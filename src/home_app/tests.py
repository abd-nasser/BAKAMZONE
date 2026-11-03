from django.test import TestCase
from django.urls import reverse

from blocs_app.models import Blocs
from auth_app.models import User
from clients_app.models import Client


class HomeBlockLinksTests(TestCase):
    def setUp(self):
        self.bloc = Blocs.objects.create(
            nom="Bloc Tampouy",
            quartier="tampouy",
            actif=True,
        )

    def test_client_can_open_block_detail_from_homepage(self):
        user = User.objects.create(
            telephone="70000991",
            first_name="Awa",
            last_name="Client",
            role="client",
        )
        Client.objects.create(user=user)
        self.client.force_login(user)

        response = self.client.get(reverse("home_app:home"))

        detail_url = reverse("clients_app:detail-bloc", args=[self.bloc.pk])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{detail_url}"')
        self.assertContains(response, "Voir le détail")

    def test_non_client_does_not_get_block_detail_link(self):
        user = User.objects.create(
            telephone="70000992",
            first_name="Moussa",
            last_name="Livreur",
            role="livreur",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("home_app:home"))

        detail_url = reverse("clients_app:detail-bloc", args=[self.bloc.pk])
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, f'href="{detail_url}"')
        self.assertNotContains(response, "Voir le détail")

    def test_anonymous_visitor_does_not_get_block_detail_link(self):
        response = self.client.get(reverse("home_app:home"))

        detail_url = reverse("clients_app:detail-bloc", args=[self.bloc.pk])
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, f'href="{detail_url}"')
        self.assertNotContains(response, "Voir le détail")
