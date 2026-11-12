from django.contrib import admin

from .models import ArticlePanier, Commande, LigneCommande, Panier


class ArticlePanierInline(admin.TabularInline):
    model = ArticlePanier
    extra = 0


class LigneCommandeInline(admin.TabularInline):
    model = LigneCommande
    extra = 0
    readonly_fields = (
        "article",
        "entreprise",
        "nom_article",
        "nom_entreprise",
        "quantite",
        "prix_unitaire",
    )


@admin.register(Panier)
class PanierAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "statut", "date_creation", "date_modification")
    list_filter = ("statut",)
    inlines = (ArticlePanierInline,)


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "client",
        "total_a_payer",
        "statut",
        "statut_paiement",
        "date_creation",
    )
    list_filter = ("statut", "statut_paiement")
    search_fields = ("reference", "client__user__telephone")
    inlines = (LigneCommandeInline,)
