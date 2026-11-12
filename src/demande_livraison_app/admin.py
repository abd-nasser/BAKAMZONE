from django.contrib import admin
from demande_livraison_app.models import DemandeLivraison

@admin.register(DemandeLivraison)
class DemandeLivraisonAdmin(admin.ModelAdmin):
    list_display = ["ligne_commande", "zone_depart", "zone_arrivee", "date_creation"]