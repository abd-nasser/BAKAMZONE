from django.contrib import admin

from articles_app.models import Article

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = (
        "nom",
        "entreprise",
        "prix",
        "prix_promo",
        "en_bloc",
        'quantite_disponible',
        "disponible",
        "date_expiration",
        "date_creation",
        "date_modification",
    )
    list_filter = ("entreprise", "en_bloc", "disponible")
    search_fields = ("nom", "description", "entreprise__nom_entreprise")
