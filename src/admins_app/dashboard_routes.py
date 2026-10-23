from django.urls import reverse

from .models import AdminBloc


ADMIN_BLOC_DASHBOARDS = {
    "responsable": "admins_app:tableau-de-bord-responsable",
    "gestionnaire_stock": "admins_app:tableau-de-bord-stock",
    "superviseur_flotte": "admins_app:tableau-de-bord-flotte",
    "assistant": "admins_app:tableau-de-bord-assistant",
}


def get_admin_bloc_dashboard_url(user):
    if not user.is_authenticated or user.role != "bloc_admin":
        return None

    admin_bloc = AdminBloc.objects.filter(
        user=user,
        actif=True,
    ).only("poste").first()
    if admin_bloc is None:
        return None

    route_name = ADMIN_BLOC_DASHBOARDS.get(admin_bloc.poste)
    return reverse(route_name) if route_name else None
