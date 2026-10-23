from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from entreprise_app.models import Entreprise, MembreAdminsEntreprise

from .forms import ArticleEntrepriseForm
from .models import Article


class EntrepriseArticleListeView(LoginRequiredMixin, ListView):
    model = Article
    context_object_name = "articles"
    template_name = "articles_templates/entreprise_articles.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if request.user.role not in ("entreprise", "entreprise_admin"):
            return HttpResponseForbidden(
                "Seuls les comptes d'entreprise peuvent consulter ces articles."
            )
        self.entreprise = self.get_entreprise()
        return super().dispatch(request, *args, **kwargs)

    def get_entreprise(self):
        if self.request.user.role == "entreprise":
            return get_object_or_404(
                Entreprise,
                user_principal=self.request.user,
            )
        membership = get_object_or_404(
            MembreAdminsEntreprise.objects.select_related("entreprise"),
            membre_admin=self.request.user,
        )
        return membership.entreprise

    def get_queryset(self):
        queryset = Article.objects.filter(
            entreprise=self.entreprise,
        ).order_by("-date_creation")

        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(
                Q(nom__icontains=search) | Q(description__icontains=search)
            )

        disponible = self.request.GET.get("disponible")
        if disponible == "oui":
            queryset = queryset.filter(disponible=True)
        elif disponible == "non":
            queryset = queryset.filter(disponible=False)

        en_bloc = self.request.GET.get("en_bloc")
        if en_bloc == "oui":
            queryset = queryset.filter(en_bloc=True)
        elif en_bloc == "non":
            queryset = queryset.filter(en_bloc=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "entreprise": self.entreprise,
            "nb_articles": self.entreprise.nb_articles_actuels,
            "quota_articles": self.entreprise.quota_articles,
            "can_add_article": (
                self.entreprise.nb_articles_actuels
                < self.entreprise.quota_articles
            ),
            "search_query": self.request.GET.get("q", ""),
            "disponible_filter": self.request.GET.get("disponible", ""),
            "en_bloc_filter": self.request.GET.get("en_bloc", ""),
            "is_htmx": self.request.headers.get("HX-Request") == "true",
        })
        return context

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return ["partials/articles/entreprise_articles_list.html"]
        return [self.template_name]


class EntrepriseArticleAccessMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if request.user.role not in ("entreprise", "entreprise_admin"):
            return HttpResponseForbidden(
                "Seuls les comptes d'entreprise peuvent gérer ces articles."
            )
        self.entreprise = self.get_entreprise()
        return super().dispatch(request, *args, **kwargs)

    def get_entreprise(self):
        if self.request.user.role == "entreprise":
            return get_object_or_404(
                Entreprise,
                user_principal=self.request.user,
            )
        membership = get_object_or_404(
            MembreAdminsEntreprise.objects.select_related("entreprise"),
            membre_admin=self.request.user,
        )
        return membership.entreprise

    def get_queryset(self):
        return Article.objects.filter(entreprise=self.entreprise)


class EntrepriseArticleUpdateView(
    LoginRequiredMixin,
    EntrepriseArticleAccessMixin,
    UpdateView,
):
    model = Article
    form_class = ArticleEntrepriseForm
    template_name = "articles_templates/article_form.html"
    context_object_name = "article"
    success_url = reverse_lazy("articles_app:entreprise_articles")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["entreprise"] = self.entreprise
        return context

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get("HX-Request") == "true":
            response = render(
                self.request,
                "partials/result/article_updated.html",
                {"article": self.object},
            )
            response["HX-Trigger"] = "articleUpdated"
            return response

        messages.success(self.request, "L'article a été modifié avec succès.")
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        if self.request.headers.get("HX-Request") == "true":
            errors = [
                (
                    form.fields[field].label if field in form.fields else "Formulaire",
                    error,
                )
                for field, field_errors in form.errors.items()
                for error in field_errors
            ]
            return render(
                self.request,
                "partials/result/article_update_error.html",
                {"errors": errors},
            )

        return super().form_invalid(form)


class EntrepriseArticleDeleteView(
    LoginRequiredMixin,
    EntrepriseArticleAccessMixin,
    DeleteView,
):
    model = Article
    template_name = "articles_templates/article_confirm_delete.html"
    context_object_name = "article"
    success_url = reverse_lazy("articles_app:entreprise_articles")

    def form_valid(self, form):
        article_name = self.object.nom
        response = super().form_valid(form)
        if self.request.headers.get("HX-Request") == "true":
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "articleDeleted"
            return response

        messages.success(
            self.request,
            f"L'article « {article_name} » a été supprimé.",
        )
        return response


class AjouteArticleView(LoginRequiredMixin, CreateView):
    model = Article
    form_class = ArticleEntrepriseForm
    template_name = "articles_templates/ajoute_article.html"
    success_url = reverse_lazy("articles_app:ajoute_article")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if request.user.role not in ("entreprise", "entreprise_admin"):
            return HttpResponseForbidden(
                "Seuls les comptes d'entreprise peuvent ajouter un article."
            )
        self.entreprise = self.get_entreprise()
        return super().dispatch(request, *args, **kwargs)

    def get_entreprise(self):
        if self.request.user.role == "entreprise":
            return get_object_or_404(
                Entreprise,
                user_principal=self.request.user,
            )
        membership = get_object_or_404(
            MembreAdminsEntreprise.objects.select_related("entreprise"),
            membre_admin=self.request.user,
        )
        return membership.entreprise

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "entreprise": self.entreprise,
            "nb_articles": self.entreprise.nb_articles_actuels,
            "quota_articles": self.entreprise.quota_articles,
        })
        return context

    @transaction.atomic
    def form_valid(self, form):
        self.entreprise = get_object_or_404(
            Entreprise.objects.select_for_update(),
            pk=self.entreprise.pk,
        )
        if self.entreprise.nb_articles_actuels >= self.entreprise.quota_articles:
            form.add_error(
                None,
                "Le quota d'articles de votre entreprise est atteint. "
                "Choisissez un palier supérieur pour ajouter des articles.",
            )
            return self.form_invalid(form)

        self.object = form.save()
        if self.request.headers.get("HX-Request") == "true":
            response = render(
                self.request,
                "partials/result/article_success.html",
                {"article": self.object},
            )
            response["HX-Trigger"] = "articleCreated"
            return response

        messages.success(self.request, "L'article a été ajouté avec succès.")
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get("HX-Request") == "true":
            errors = [
                (
                    form.fields[field].label if field in form.fields else "Formulaire",
                    error,
                )
                for field, field_errors in form.errors.items()
                for error in field_errors
            ]
            return render(
                self.request,
                "partials/result/article_error.html",
                {"errors": errors},
            )

        return super().form_invalid(form)
