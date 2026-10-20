from django.views.generic import TemplateView
from django.contrib.auth.mixins import UserPassesTestMixin
from superuser_app.forms import BlocForm
from blocs_app.models import Blocs


class SuperuserRequiredMixin(UserPassesTestMixin):
    """Vérifie que l'utilisateur est bien un Superuser"""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser


class SuperuserDashboardView(SuperuserRequiredMixin, TemplateView):
    """
    Cockpit de pilotage central pour le Superuser BAKAMZONE.
    Permet la création et la supervision des blocs, équipes admins et livreurs.
    """
    template_name = 'superuser_template/superuser.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bloc_form'] = BlocForm()
        context['blocs'] = Blocs.objects.all().order_by('-date_creation')
        context['total_blocs'] = context['blocs'].count()
        return context
