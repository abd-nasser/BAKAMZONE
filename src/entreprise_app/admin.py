from django.contrib import admin
from django.utils import timezone

from .models import Entreprise, MembreAdminsEntreprise, RetraitEntreprise

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


@admin.register(RetraitEntreprise)
class RetraitEntrepriseAdmin(admin.ModelAdmin):
    list_display = (
        "entreprise",
        "montant",
        "statut",
        "date_demande",
        "date_traitement",
        "traite_par",
    )
    list_filter = ("statut", "date_demande")
    search_fields = (
        "entreprise__nom_entreprise",
        "entreprise__user_principal__telephone",
    )
    readonly_fields = (
        "entreprise",
        "montant",
        "statut",
        "date_demande",
        "date_traitement",
        "traite_par",
    )
    actions = (
        "approuver_retraits",
        "marquer_retraits_payes",
        "rejeter_retraits",
    )

    @admin.action(description="Approuver les demandes en attente")
    def approuver_retraits(self, request, queryset):
        nombre = queryset.filter(
            statut=RetraitEntreprise.STATUT_EN_ATTENTE,
        ).update(
            statut=RetraitEntreprise.STATUT_APPROUVE,
            date_traitement=timezone.now(),
            traite_par=request.user,
        )
        self.message_user(request, f"{nombre} demande(s) approuvée(s).")

    @admin.action(description="Marquer comme payés les retraits approuvés")
    def marquer_retraits_payes(self, request, queryset):
        nombre = queryset.filter(
            statut=RetraitEntreprise.STATUT_APPROUVE,
        ).update(
            statut=RetraitEntreprise.STATUT_PAYE,
            date_traitement=timezone.now(),
            traite_par=request.user,
        )
        self.message_user(request, f"{nombre} retrait(s) marqué(s) payé(s).")

    @admin.action(description="Rejeter les retraits en attente ou approuvés")
    def rejeter_retraits(self, request, queryset):
        nombre = queryset.filter(
            statut__in=[
                RetraitEntreprise.STATUT_EN_ATTENTE,
                RetraitEntreprise.STATUT_APPROUVE,
            ],
        ).update(
            statut=RetraitEntreprise.STATUT_REJETE,
            date_traitement=timezone.now(),
            traite_par=request.user,
        )
        self.message_user(request, f"{nombre} demande(s) rejetée(s).")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
    
