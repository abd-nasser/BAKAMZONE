import json

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render
from django.views.generic import CreateView

from blocs_app.forms import BlocForm
from blocs_app.models import Blocs


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


class BlocCreateView(SuperuserRequiredMixin, CreateView):
    model = Blocs
    form_class = BlocForm
    template_name = 'blocs_templates/blocs_register.html'

    def form_valid(self, form):
        self.object = form.save()
        response = render(
            self.request,
            'partials/result/bloc_success.html',
            {'bloc': self.object},
        )
        response['HX-Trigger'] = json.dumps({
            'blocCreated': {'id': self.object.pk, 'nom': self.object.nom},
        })
        return response

    def form_invalid(self, form):
        errors = [
            error
            for field_errors in form.errors.values()
            for error in field_errors
        ]
        response = render(
            self.request,
            'partials/result/bloc_error.html',
            {'errors': errors},
        )
        response['HX-Trigger'] = 'blocFormInvalid'
        return response
