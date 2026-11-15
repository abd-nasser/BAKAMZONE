from django.contrib import admin

from livreurs_app.models import Livreur

@admin.register(Livreur)
class LivreurAdmin(admin.ModelAdmin):
    list_display = ["user__first_name", "user__last_name", "type_vehicule", "actif", "disponible", "statut_verification", "note_moyenne", "nb_livraisons"]
    