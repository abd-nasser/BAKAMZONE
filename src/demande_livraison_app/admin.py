from django.contrib import admin

from demande_livraison_app.models import DemandeLivraison

@admin.register(DemandeLivraison)
class DemandeLivraisonAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'client',
        'zone_depart',
        'zone_arrivee',
        'whatsapp_destinataire',
        'description_colis',
        'latitude_depart',
        'longitude_depart',
        
        'date_creation',
    )
    list_filter = ('zone_depart', 'zone_arrivee', 'date_creation')
    search_fields = ('client__user__username', 'whatsapp_destinataire', 'description_colis')
    ordering = ('-date_creation',)