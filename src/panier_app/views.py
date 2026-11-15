from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, TemplateView

from articles_app.models import Article, StockBloc
from clients_app.models import Client

from .forms import ValidationCommandeForm
from .models import ArticlePanier, Commande, LigneCommande, Panier


class ClientPanierRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Réserve les vues du panier aux clients disposant d'un profil client."""

    login_url = reverse_lazy("home_app:home")

    def test_func(self):
        return (
            self.request.user.role == "client"
            and Client.objects.filter(user=self.request.user).exists()
        )

    def get_client(self):
        return Client.objects.get(user=self.request.user)


def obtenir_panier_actif(client):
    """Retourne le panier actif du client ou le crée lors de son premier accès."""
    panier, _ = Panier.objects.get_or_create(
        client=client,
        statut=Panier.STATUT_ACTIF,
    )
    return panier


def compter_articles(panier):
    """Compte les unités du panier pour mettre à jour le badge d'interface."""
    return panier.lignes.aggregate(total=Sum("quantite"))["total"] or 0


def reponse_panier(request, panier, message="", est_erreur=False):
    """Rend le contenu actualisé du panier pour HTMX ou le chargement complet."""
    return render(
        request,
        "partials/panier/panier_contenu.html",
        {
            "panier": panier,
            "lignes": panier.lignes.select_related(
                "article",
                "article__entreprise",
            ),
            "nombre_articles": compter_articles(panier),
            "message_panier": message,
            "est_erreur": est_erreur,
            "is_htmx": request.headers.get("HX-Request") == "true",
        },
    )


class PanierView(ClientPanierRequiredMixin, TemplateView):
    """Affiche le panier courant et ses commandes HTMX de modification."""

    template_name = "panier_templates/panier.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        panier = obtenir_panier_actif(self.get_client())
        context.update({
            "panier": panier,
            "lignes": panier.lignes.select_related(
                "article",
                "article__entreprise",
            ),
            "nombre_articles": compter_articles(panier),
            "form_commande": ValidationCommandeForm(),
        })
        return context


class ValiderCommandeView(ClientPanierRequiredMixin, View):
    """Revalide le panier et crée une commande en attente de paiement."""

    def _render_erreur(self, request, form, panier, message):
        if message:
            form.add_error(None, message)

        feedback_context = {
            "form_commande": form,
            "message_commande": (
                message or "Vérifiez les informations de livraison."
            ),
        }
        if request.headers.get("HX-Request") == "true":
            return render(
                request,
                "partials/panier/commande_feedback.html",
                feedback_context,
            )

        return render(
            request,
            "panier_templates/panier.html",
            {
                "panier": panier,
                "lignes": panier.lignes.select_related(
                    "article",
                    "article__entreprise",
                ),
                "nombre_articles": compter_articles(panier),
                "form_commande": form,
                "checkout_open": True,
                **feedback_context,
            },
            status=400,
        )

    def post(self, request, *args, **kwargs):
        client = self.get_client()
        form = ValidationCommandeForm(request.POST)
        panier = Panier.objects.filter(
            client=client,
            statut=Panier.STATUT_ACTIF,
        ).first()

        if panier is None:
            messages.error(request, "Votre panier actif est introuvable.")
            return redirect("panier_app:panier")
        if not form.is_valid():
            return self._render_erreur(request, form, panier, "")

        panier_initial = panier
        message_erreur = None
        with transaction.atomic():
            panier = Panier.objects.select_for_update().filter(
                pk=panier.pk,
                client=client,
                statut=Panier.STATUT_ACTIF,
            ).first()
            if panier is None:
                message_erreur = (
                    "Ce panier a déjà été validé. Consultez le détail de votre commande."
                )
                panier = panier_initial
            else:
                lignes_panier = list(
                    ArticlePanier.objects.select_for_update().filter(
                        panier=panier,
                    ).select_related(
                        "article__entreprise",
                    )
                )
                if not lignes_panier:
                    message_erreur = "Votre panier est vide."

            lignes_commande = []
            montant_produits = Decimal("0.00")
            if message_erreur is None:
                maintenant = timezone.now()
                for ligne in lignes_panier:
                    article = Article.objects.filter(
                        pk=ligne.article_id,
                    ).select_related(
                        "entreprise",
                    ).first()
                    if (
                        article is None
                        or not article.disponible
                        or (
                            article.date_expiration is not None
                            and article.date_expiration <= maintenant
                        )
                    ):
                        message_erreur = (
                            f"« {ligne.article.nom} » n'est plus disponible. "
                            "Retirez cet article avant de valider."
                        )
                        break

                    if article.en_bloc:
                        stocks_actifs = StockBloc.objects.filter(
                            article=article,
                            bloc__actif=True,
                        ).values_list(
                            "quantite",
                            flat=True,
                        )
                        quantite_disponible = sum(stocks_actifs)
                    else:
                        quantite_disponible = article.quantite_disponible

                    if ligne.quantite > quantite_disponible:
                        message_erreur = (
                            f"Stock insuffisant pour « {article.nom} » : "
                            f"{quantite_disponible} disponible(s), "
                            f"{ligne.quantite} demandé(s)."
                        )
                        break

                    prix_unitaire = article.prix_actuel
                    montant_produits += prix_unitaire * ligne.quantite
                    lignes_commande.append(
                        LigneCommande(
                            article=article,
                            entreprise=article.entreprise,
                            nom_article=article.nom,
                            nom_entreprise=article.entreprise.nom_entreprise,
                            quantite=ligne.quantite,
                            prix_unitaire=prix_unitaire,
                        )
                    )

            if message_erreur is None:
                commande = Commande.objects.create(
                    panier=panier,
                    client=client,
                    zone_arrivee=form.cleaned_data["zone_arrivee"],
                    latitude_livraison=form.cleaned_data["latitude"],
                    longitude_livraison=form.cleaned_data["longitude"],
                    montant_produits=montant_produits,
                    frais_livraison=0,
                    total_a_payer=montant_produits,
                )
                for ligne_commande in lignes_commande:
                    ligne_commande.commande = commande
                LigneCommande.objects.bulk_create(lignes_commande)
                panier.statut = Panier.STATUT_COMMANDE
                panier.save(update_fields=["statut", "date_modification"])

        if message_erreur is not None:
            return self._render_erreur(
                request,
                form,
                panier,
                message_erreur,
            )

        detail_url = reverse_lazy(
            "panier_app:detail_commande",
            kwargs={"reference": commande.reference},
        )
        if request.headers.get("HX-Request") == "true":
            response = HttpResponse(status=204)
            response["HX-Redirect"] = detail_url
            return response
        return redirect(detail_url)


class DetailCommandeView(ClientPanierRequiredMixin, DetailView):
    model = Commande
    template_name = "panier_templates/detail_commande.html"
    context_object_name = "commande"
    slug_url_kwarg = "reference"
    slug_field = "reference"

    def get_queryset(self):
        return Commande.objects.filter(
            client=self.get_client(),
        ).select_related(
            "zone_arrivee__bloc",
        ).prefetch_related(
            "lignes",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        commande = self.object
        etapes = [
            (
                Commande.STATUT_EN_ATTENTE_PAIEMENT,
                "Commande enregistrée",
                "La commande attend la confirmation du paiement.",
            ),
            (
                Commande.STATUT_CONFIRMEE,
                "Commande confirmée",
                "Le paiement a été confirmé et la commande est prise en charge.",
            ),
            (
                Commande.STATUT_EN_PREPARATION,
                "En préparation",
                "Les articles sont en cours de préparation.",
            ),
            (
                Commande.STATUT_EN_LIVRAISON,
                "En livraison",
                "La commande est en route vers votre zone.",
            ),
            (
                Commande.STATUT_LIVREE,
                "Livrée",
                "La commande a été livrée.",
            ),
        ]
        statut_index = next(
            (
                index
                for index, (statut, _, _) in enumerate(etapes)
                if statut == commande.statut
            ),
            -1,
        )
        context.update({
            "etapes_commande": [
                {
                    "statut": statut,
                    "label": label,
                    "description": description,
                    "terminee": statut_index >= 0 and index < statut_index,
                    "actuelle": index == statut_index,
                    "date": (
                        commande.date_creation
                        if index == 0
                        else commande.date_paiement
                        if index == 1
                        else None
                    ),
                }
                for index, (statut, label, description) in enumerate(etapes)
            ],
            "commande_annulee": (
                commande.statut == Commande.STATUT_ANNULEE
            ),
        })
        return context


class AjouterPanierView(ClientPanierRequiredMixin, View):
    """Ajoute un article disponible au panier ou augmente sa quantité."""

    def post(self, request, article_id):
        client = self.get_client()
        article = Article.objects.filter(
            pk=article_id,
            disponible=True,
        ).filter(
            Q(date_expiration__isnull=True)
            | Q(date_expiration__gt=timezone.now())
        ).select_related("entreprise").distinct().first()

        stock_existant = (
            article is not None
            and (
                StockBloc.objects.filter(
                    article=article,
                    quantite__gt=0,
                    bloc__actif=True,
                ).exists()
                if article.en_bloc
                else article.quantite_disponible > 0
            )
        )
        if article is None or not stock_existant:
            message = "Cet article n'est plus disponible dans le catalogue."
            if request.headers.get("HX-Request") == "true":
                return render(
                    request,
                    "partials/panier/panier_feedback.html",
                    {"message_panier": message, "est_erreur": True},
                )
            messages.error(request, message)
            return redirect("clients_app:tableau-de-bord")

        with transaction.atomic():
            panier = obtenir_panier_actif(client)
            panier = Panier.objects.select_for_update().get(pk=panier.pk)
            ligne, creee = ArticlePanier.objects.get_or_create(
                panier=panier,
                article=article,
                defaults={"quantite": 1},
            )
            if not creee:
                ligne.quantite += 1
                ligne.save(update_fields=["quantite", "date_modification"])

        message = f"{article.nom} a été ajouté au panier."
        if request.headers.get("HX-Request") == "true":
            return render(
                request,
                "partials/panier/panier_feedback.html",
                {
                    "message_panier": message,
                    "est_erreur": False,
                    "nombre_articles": compter_articles(panier),
                },
            )
        messages.success(request, message)
        return redirect("panier_app:panier")


class ModifierPanierView(ClientPanierRequiredMixin, View):
    """Met à jour une quantité ou retire sa ligne lorsque la quantité vaut zéro."""

    def post(self, request, ligne_id):
        client = self.get_client()
        panier = obtenir_panier_actif(client)
        ligne = get_object_or_404(
            ArticlePanier.objects.select_related("article"),
            pk=ligne_id,
            panier=panier,
        )
        try:
            quantite = int(request.POST.get("quantite", ""))
        except (TypeError, ValueError):
            message = "Veuillez saisir une quantité entière valide."
            if request.headers.get("HX-Request") != "true":
                messages.error(request, message)
                return redirect("panier_app:panier")
            return reponse_panier(
                request,
                panier,
                message,
                est_erreur=True,
            )

        if quantite < 0:
            message = "La quantité ne peut pas être négative."
            if request.headers.get("HX-Request") != "true":
                messages.error(request, message)
                return redirect("panier_app:panier")
            return reponse_panier(
                request,
                panier,
                message,
                est_erreur=True,
            )

        if quantite == 0:
            ligne.delete()
            message = "L'article a été retiré du panier."
        else:
            ligne.quantite = quantite
            ligne.save(update_fields=["quantite", "date_modification"])
            message = "La quantité a été mise à jour."

        if request.headers.get("HX-Request") == "true":
            return reponse_panier(request, panier, message)
        messages.success(request, message)
        return redirect("panier_app:panier")


class ViderPanierView(ClientPanierRequiredMixin, View):
    """Supprime les lignes du panier sans effacer son historique."""

    def post(self, request):
        panier = obtenir_panier_actif(self.get_client())
        panier.lignes.all().delete()
        if request.headers.get("HX-Request") == "true":
            return reponse_panier(request, panier, "Votre panier a été vidé.")
        messages.success(request, "Votre panier a été vidé.")
        return redirect("panier_app:panier")
