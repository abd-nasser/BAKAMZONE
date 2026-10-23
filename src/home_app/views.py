from django.views.generic import TemplateView
from auth_app.forms import ConnexionForm
from admins_app.dashboard_routes import get_admin_bloc_dashboard_url
from admins_app.models import AdminBloc
from blocs_app.models import Blocs


class HomePageView(TemplateView):
    """
    Vue principale (CBV) de la page d'accueil de BAKAMZONE.
    Adapte intelligemment l'expérience et le contenu selon le statut et le rôle de l'utilisateur connecté :
    - Visiteur : Vitrine mobile-first, flotte électrique, blocs de quartier à Ouagadougou, modal de connexion HTMX.
    - Client : Suivi commandes, accès catalogue, panier.
    - Livreur : Cockpit livreur, statut disponibilité, bloc de rattachement.
    - Administrateur de Bloc : Gestion locale du bloc, stock et assignations.
    - Entreprise Partenaire : Pilotage des articles et stocks déposés en blocs.
    - Superuser : Raccourci vers le cockpit central de supervision.
    """
    template_name = 'home_templates/home_page.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Formulaire de connexion pour le modal HTMX
        context['connexion_form'] = ConnexionForm()

        # Statistiques publiques des blocs actifs
        context['blocs_actifs'] = Blocs.objects.filter(actif=True)
        context['total_blocs'] = context['blocs_actifs'].count()

        # Données contextuelles intelligentes selon le rôle
        if user.is_authenticated:
            context['user_role'] = getattr(user, 'role', 'client')
            context['is_superadmin'] = user.is_superuser
            if user.role == 'bloc_admin':
                context['admin_bloc_profil'] = AdminBloc.objects.filter(
                    user=user,
                    actif=True,
                ).select_related('bloc').first()
                context['admin_bloc_dashboard_url'] = get_admin_bloc_dashboard_url(user)

            # Profils spécifiques selon le rôle
            if hasattr(user, 'livreur_profil'):
                context['livreur_profil'] = user.livreur_profil
            if hasattr(user, 'enterprise_profile'):
                context['enterprise_profil'] = user.enterprise_profile
            if hasattr(user, 'client_profil'):
                context['client_profil'] = user.client_profil

        return context
