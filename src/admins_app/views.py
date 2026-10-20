import json

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render
from django.views.generic import CreateView

from admins_app.forms import AdminBlocForms
from admins_app.models import AdminBloc


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


class AdminBlocCreateView(SuperuserRequiredMixin, CreateView):
    model = AdminBloc
    form_class = AdminBlocForms
    template_name = 'blocs_templates/admin_bloc_register.html'

    def form_valid(self, form):
        self.object = form.save()
        response = render(
            self.request,
            'partials/result/admin_bloc_success.html',
            {
                'admin_bloc': self.object,
                'username': form.generated_username,
                'password': form.generated_password,
            },
        )
        response['HX-Trigger'] = json.dumps({
            'adminBlocCreated': {
                'id': self.object.pk,
                'nom': self.object.user.get_full_name(),
                'bloc': self.object.bloc.nom,
            },
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
            'partials/result/admin_bloc_error.html',
            {'errors': errors},
        )
        response['HX-Trigger'] = 'adminBlocFormInvalid'
        return response
