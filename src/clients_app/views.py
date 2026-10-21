from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView

from clients_app.forms import InscriptionClientForm
from clients_app.models import Client


class InscriptionClientView(CreateView):
    model = Client
    form_class = InscriptionClientForm
    template_name = 'auth_templates/clients_register.html'
    success_url = reverse_lazy('home_app:home')

    def form_valid(self, form):
        messages.success(
            self.request,
            "Votre compte client a été créé. Vous pouvez maintenant vous connecter.",
        )
        return super().form_valid(form)
