from django.contrib import admin
from .models import PaiementLigdiCash, PaiementLivraisonLigdiCash
@admin.register(PaiementLivraisonLigdiCash)
class PaiementLivraisonLigdiCashAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "demande_livraison",
        "montant",
        "numero_client",
        "operateur",
        "statut",
        "date_creation",
    )
    list_filter = ("statut", "date_creation")
    search_fields = ("reference", "numero_client", "operateur")
    ordering = ("-date_creation",)    
    

@admin.register(PaiementLigdiCash)
class PaiementLigdiCashAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "commande",
        "montant",
        "numero_client",
        "operateur",
        "statut",
        "date_creation",
    )
    list_filter = ("statut", "date_creation")
    search_fields = ("reference", "numero_client", "operateur")
    ordering = ("-date_creation",)