import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Case, DecimalField, Exists, F, OuterRef, Q, Sum, When
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, TemplateView
from kombu.exceptions import OperationalError as CeleryOperationalError

from admins_app.models import AdminBloc
from articles_app.models import Article, StockBloc
from blocs_app.models import Blocs
from clients_app.forms import InscriptionClientForm, SupportMessageForm
from clients_app.models import Client, SupportConversation, SupportMessage
from demande_livraison_app.forms import DemandeLivraisonForm
from demande_livraison_app.pricing import obtenir_tarifs_livraison
from livreurs_app.models import Livreur
from panier_app.models import Commande, Panier
from zones_app.models import Zone

logger = logging.getLogger(__name__)


class ClientRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy("home_app:home")

    def test_func(self):
        return (
            self.request.user.role == "client"
            and Client.objects.filter(user=self.request.user).exists()
        )


class ClientDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "clients_templates/client_dashboard.html"
    login_url = reverse_lazy("home_app:home")
    htmx_templates = {
        "client-livreurs-results": (
            "partials/clients/client_dashboard_livreurs.html"
        ),
        "client-articles-results": (
            "partials/clients/client_dashboard_articles.html"
        ),
    }

    def test_func(self):
        return (
            self.request.user.role == "client"
            and Client.objects.filter(user=self.request.user).exists()
        )

    def get_template_names(self):
        target = self.request.headers.get("HX-Target")
        if self.request.headers.get("HX-Request") == "true":
            template_name = self.htmx_templates.get(target)
            if template_name:
                return [template_name]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = Client.objects.get(user=self.request.user)

        livreur_query = self.request.GET.get("livreur_q", "").strip()
        livreur_vehicule = self.request.GET.get("livreur_vehicule", "")
        livreur_bloc = self.request.GET.get("livreur_bloc", "")
        livreurs_favoris = self.request.GET.get("livreur_favoris", "")

        livreurs = Livreur.objects.filter(
            actif=True,
            #disponible=True,
            #statut_verification="verifie",
            blocs__actif=True,
        ).select_related("user", "blocs", "zone_actuelle")
        if livreur_query:
            livreurs = livreurs.filter(
                Q(user__first_name__icontains=livreur_query)
                | Q(user__last_name__icontains=livreur_query)
                | Q(user__telephone__icontains=livreur_query)
                | Q(blocs__nom__icontains=livreur_query)
                | Q(blocs__quartier__icontains=livreur_query)
            )
        vehicle_values = {value for value, _ in Livreur.TYPE_VEHICULE}
        if livreur_vehicule in vehicle_values:
            livreurs = livreurs.filter(type_vehicule=livreur_vehicule)

        active_blocs = Blocs.objects.filter(actif=True)
        valid_bloc_ids = {str(pk) for pk in active_blocs.values_list("pk", flat=True)}
        if livreur_bloc in valid_bloc_ids:
            livreurs = livreurs.filter(blocs_id=livreur_bloc)
        if livreurs_favoris == "1":
            livreurs = livreurs.filter(favoris_de=client)
        livreurs = livreurs.order_by("user__first_name", "user__last_name")

        article_query = self.request.GET.get("article_q", "").strip()
        article_entreprise = self.request.GET.get("article_entreprise", "")
        article_tri = self.request.GET.get("article_tri", "recent")
        article_promo = self.request.GET.get("article_promo", "")

        stock_disponible = StockBloc.objects.filter(
            article_id=OuterRef("pk"),
            quantite__gt=0,
            bloc__actif=True,
        )
        catalogue_articles = Article.objects.filter(
            disponible=True,
        ).filter(
            Q(date_expiration__isnull=True) | Q(date_expiration__gt=timezone.now())
        ).annotate(
            stock_disponible=Exists(stock_disponible),
            prix_affiche=Case(
                When(prix_promo__lt=F("prix"), then=F("prix_promo")),
                default=F("prix"),
                output_field=DecimalField(max_digits=10, decimal_places=2),
            ),
        ).select_related("entreprise")
        articles = catalogue_articles
        if article_query:
            articles = articles.filter(
                Q(nom__icontains=article_query)
                | Q(description__icontains=article_query)
                | Q(entreprise__nom_entreprise__icontains=article_query)
            )

        entreprise_ids = {
            str(pk)
            for pk in catalogue_articles.values_list(
                "entreprise_id",
                flat=True,
            ).distinct()
        }
        if article_entreprise in entreprise_ids:
            articles = articles.filter(entreprise_id=article_entreprise)
        if article_promo == "1":
            articles = articles.filter(prix_promo__lt=F("prix"))

        if article_tri == "prix_croissant":
            articles = articles.order_by("prix_affiche", "nom")
        elif article_tri == "prix_decroissant":
            articles = articles.order_by("-prix_affiche", "nom")
        else:
            article_tri = "recent"
            articles = articles.order_by("-date_creation", "nom")

        context.update({
            "client": client,
            "client_commande": Commande.objects.filter(
                client=client,
            ).select_related(
                "zone_arrivee",
            ).order_by(
                "-date_creation",
            ).first(),
            "nombre_articles_panier": (
                Panier.objects.filter(
                    client=client,
                    statut=Panier.STATUT_ACTIF,
                ).aggregate(total=Sum("lignes__quantite"))["total"] or 0
            ),
            "livreurs": livreurs,
            "livreur_query": livreur_query,
            "livreur_vehicule": livreur_vehicule,
            "livreur_bloc": livreur_bloc,
            "livreurs_favoris": livreurs_favoris,
            "livreur_types_vehicule": Livreur.TYPE_VEHICULE,
            "livreur_blocs": active_blocs.order_by("nom"),
            "articles": articles,
            "article_query": article_query,
            "article_entreprise": article_entreprise,
            "article_tri": article_tri,
            "article_promo": article_promo,
            "article_entreprises": catalogue_articles.values_list(
                "entreprise_id",
                "entreprise__nom_entreprise",
            ).distinct().order_by("entreprise__nom_entreprise"),
        })
        return context


class ClientArticleDetailView(ClientRequiredMixin, DetailView):
    model = Article
    template_name = "clients_templates/article_detail.html"
    context_object_name = "article"

    def get_queryset(self):
        return Article.objects.filter(
            disponible=True,
        ).filter(
            Q(date_expiration__isnull=True)
            | Q(date_expiration__gt=timezone.now())
        ).select_related("entreprise")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = Client.objects.get(user=self.request.user)
        context.update({
            "est_favori": client.articles_favoris.filter(
                pk=self.object.pk,
            ).exists(),
            "nb_favoris": self.object.favoris_de.count(),
        })
        return context


class LivreurProfilViewByClient(
    LoginRequiredMixin,
    UserPassesTestMixin,
    DetailView,
):
    model = Livreur
    template_name = "clients_templates/livreur_profil.html"
    context_object_name = "livreur"
    login_url = reverse_lazy("home_app:home")

    def test_func(self):
        return (
            self.request.user.role == "client"
            and Client.objects.filter(user=self.request.user).exists()
        )

    def get_queryset(self):
        return Livreur.objects.filter(
            actif=True,
            blocs__actif=True,
        ).select_related("user", "blocs", "zone_actuelle")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = Client.objects.get(user=self.request.user)
        livreur = self.object

        est_favori = livreur.favoris_de.filter(pk=client.pk).exists()
        avis_qs = livreur.avis.select_related("client__user").order_by("-date_creation")
        nb_avis = avis_qs.count()

        tarif_intra, tarif_inter = obtenir_tarifs_livraison()
        zones = Zone.objects.select_related("bloc").all().order_by("bloc__nom", "nom")

        if "form" not in context:
            initial_data = {}
            if livreur.zone_actuelle:
                initial_data["zone_depart"] = livreur.zone_actuelle
            context["form"] = DemandeLivraisonForm(initial=initial_data)

        context.update({
            "client": client,
            "est_favori": est_favori,
            "nb_favoris": livreur.nb_ajout_favoris,
            "avis_list": avis_qs[:10],
            "nb_avis": nb_avis,
            "zones": zones,
            "tarif_intra": int(tarif_intra),
            "tarif_inter": int(tarif_inter),
        })
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        client = Client.objects.get(user=request.user)

        form = DemandeLivraisonForm(request.POST)
        if form.is_valid():
            demande = form.save(client=client, commit=False)
            demande.livreur = self.object
            demande.statut = "en_attente"
            demande.save()
            messages.success(
                request,
                f"Votre demande de livraison #{demande.pk} a été envoyée directement à {self.object.user.get_full_name()} !",
            )
            return redirect("clients_app:tableau-de-bord")

        context = self.get_context_data(form=form)
        return self.render_to_response(context)


class ClientBlocDetailView(ClientRequiredMixin, DetailView):
    model = Blocs
    template_name = "clients_templates/bloc_detail.html"
    context_object_name = "bloc"

    def get_queryset(self):
        return Blocs.objects.filter(actif=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["zones"] = self.object.zones.order_by("nom")
        context["livreurs"] = self.object.livreurs_bloc.filter(
            actif=True,
        ).select_related(
            "user",
            "zone_actuelle",
        ).order_by(
            "user__first_name",
            "user__last_name",
        )
        context["assistant_disponible"] = AdminBloc.objects.filter(
            bloc=self.object,
            poste="assistant",
            actif=True,
            user__is_active=True,
        ).exists()
        return context


class StartBlocSupportChatView(ClientRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        bloc = get_object_or_404(Blocs, pk=kwargs["pk"], actif=True)
        assistant_disponible = AdminBloc.objects.filter(
            bloc=bloc,
            poste="assistant",
            actif=True,
            user__is_active=True,
        ).exists()
        if not assistant_disponible:
            messages.error(
                request,
                "Aucun assistant opérationnel n’est actuellement disponible pour ce bloc.",
            )
            return redirect("clients_app:detail-bloc", pk=bloc.pk)

        client = Client.objects.get(user=request.user)
        conversation, _ = SupportConversation.objects.get_or_create(
            client=client,
            bloc=bloc,
        )
        return redirect(
            "clients_app:chat-assistant",
            pk=conversation.pk,
        )


class SupportChatView(LoginRequiredMixin, DetailView):
    model = SupportConversation
    template_name = "clients_templates/support_chat.html"
    context_object_name = "conversation"
    login_url = reverse_lazy("home_app:home")

    def dispatch(self, request, *args, **kwargs):
        self.client_profile = None
        self.admin_bloc = None
        if request.user.is_authenticated:
            if request.user.role == "client":
                self.client_profile = Client.objects.filter(
                    user=request.user,
                ).first()
            elif request.user.role == "bloc_admin":
                self.admin_bloc = AdminBloc.objects.filter(
                    user=request.user,
                    poste="assistant",
                    actif=True,
                    bloc__actif=True,
                ).select_related("bloc").first()

            if self.client_profile is None and self.admin_bloc is None:
                raise PermissionDenied(
                    "Cette conversation est réservée au client et à l’assistant du bloc."
                )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = SupportConversation.objects.filter(
            bloc__actif=True,
        ).select_related(
            "client__user",
            "bloc",
        )
        if self.client_profile is not None:
            return queryset.filter(client=self.client_profile)
        return queryset.filter(bloc=self.admin_bloc.bloc)

    def get_template_names(self):
        if (
            self.request.headers.get("HX-Request") == "true"
            and self.request.headers.get("HX-Target") == "support-chat-messages"
        ):
            return ["partials/clients/support_chat_messages.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = kwargs.get("form", SupportMessageForm())
        context["is_client"] = self.client_profile is not None
        context["messages"] = SupportMessage.objects.filter(
            conversation=self.object,
        ).select_related(
            "sender",
        ).order_by(
            "created_at",
        )
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = SupportMessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = self.object
            message.sender = request.user
            message.save()
            self.object.save(update_fields=["updated_at"])

            from notifications_app.tasks import notifier_nouveau_message_support_task
            try:
                notifier_nouveau_message_support_task.delay(message.pk)
            except CeleryOperationalError:
                logger.warning(
                    "Le message #%s est enregistré, mais la notification Push "
                    "n'a pas pu être mise en file Celery.",
                    message.pk,
                    exc_info=True,
                )
            if request.headers.get("HX-Request") == "true":
                return render(
                    request,
                    "partials/clients/support_chat_messages.html",
                    self.get_context_data(),
                )
            return redirect("clients_app:chat-assistant", pk=self.object.pk)

        if request.headers.get("HX-Request") == "true":
            return render(
                request,
                "partials/clients/support_chat_messages.html",
                self.get_context_data(form=form),
                status=400,
            )
        return self.render_to_response(
            self.get_context_data(form=form),
            status=400,
        )


class ToggleFavoriLivreurView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Permet au client d'ajouter ou retirer un livreur de ses favoris (likes)."""
    login_url = reverse_lazy("home_app:home")

    def test_func(self):
        return (
            self.request.user.role == "client"
            and Client.objects.filter(user=self.request.user).exists()
        )

    def post(self, request, pk, *args, **kwargs):
        livreur = get_object_or_404(Livreur, pk=pk, actif=True, blocs__actif=True)
        client = Client.objects.get(user=request.user)

        if livreur.favoris_de.filter(pk=client.pk).exists():
            livreur.favoris_de.remove(client)
            est_favori = False
        else:
            livreur.favoris_de.add(client)
            est_favori = True

        if request.headers.get("HX-Request") == "true":
            return render(
                request,
                "partials/clients/livreur_favori_button.html",
                {
                    "livreur": livreur,
                    "est_favori": est_favori,
                    "nb_favoris": livreur.nb_ajout_favoris,
                },
            )
        return redirect("clients_app:profil-livreur", pk=livreur.pk)


class ToggleFavoriArticleView(ClientRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        article = get_object_or_404(
            Article.objects.filter(
                disponible=True,
            ).filter(
                Q(date_expiration__isnull=True)
                | Q(date_expiration__gt=timezone.now())
            ),
            pk=pk,
        )
        client = Client.objects.get(user=request.user)

        if client.articles_favoris.filter(pk=article.pk).exists():
            client.articles_favoris.remove(article)
            est_favori = False
        else:
            client.articles_favoris.add(article)
            est_favori = True

        if request.headers.get("HX-Request") == "true":
            return render(
                request,
                "partials/clients/article_favori_button.html",
                {
                    "article": article,
                    "est_favori": est_favori,
                    "nb_favoris": article.favoris_de.count(),
                },
            )
        return redirect("clients_app:detail-article", pk=article.pk)


class InscriptionClientView(CreateView):
    model = Client
    form_class = InscriptionClientForm
    template_name = 'auth_templates/clients_register.html'
    success_url = reverse_lazy('home_app:home')

    def form_valid(self, form):
        messages.success(
            self.request,
            "Votre compte client a été créé. Vous pouvez maintenant vous connecter.",
        )
        return super().form_valid(form)
