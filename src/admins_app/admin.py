from django.contrib import admin

from admins_app.models import AdminBloc

# Register your models here.
@admin.register(AdminBloc)
class AdminBlocAdmin(admin.ModelAdmin):
    list_display = ("user", "bloc", "poste", "actif")
    list_filter = ("poste", "actif")
    search_fields = ("user__username", "user__email", "bloc__nom_bloc")
    ordering = ("user__username",)