from django.contrib import admin

from .models import Entreprise, MembreAdminsEntreprise

@admin.register(Entreprise)
class EntrepriseAdmin(admin.ModelAdmin):
    list_display = ['nom_entreprise', 'date_creation']
    search_fields = ['nom_entreprise' ]
    ordering = ['nom_entreprise']
    
    
@admin.register(MembreAdminsEntreprise)
class MembreAdminsEntrepriseAdmin(admin.ModelAdmin):
    list_display = ['membre_admin', 'entreprise', 'date_ajout']
    search_fields = ['membre_admin__username', 'entreprise__nom']
    ordering = ['membre_admin']
    
