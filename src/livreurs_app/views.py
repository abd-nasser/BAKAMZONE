from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render
from django.views.generic import CreateView

from livreurs_app.forms import InscriptionLivreurForm
from livreurs_app.models import Livreur


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


class InscriptionLivreurView(SuperuserRequiredMixin, CreateView):
    model = Livreur
    form_class = InscriptionLivreurForm
    template_name = 'auth_templates/livreurs_register.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['admin_user'] = self.request.user
        return context

    def form_valid(self, form):
        self.object = form.save()
        context = {
            'livreur': self.object,
            'username': form.generated_username,
            'password': form.generated_password,
            'admin_user': self.request.user,
        }
        if self.request.headers.get('HX-Request') == 'true':
            response = render(
                self.request,
                'partials/result/livreur_success.html',
                context,
            )
            response['HX-Trigger'] = 'livreur-register-success'
            return response

        return render(self.request, self.template_name, {
            'form': self.get_form_class()(),
            'registration_success': context,
            **context,
        })

    def form_invalid(self, form):
        if self.request.headers.get('HX-Request') == 'true':
            errors = [
                (
                    form.fields[field].label if field in form.fields else 'Formulaire',
                    error,
                )
                for field, field_errors in form.errors.items()
                for error in field_errors
            ]
            return render(
                self.request,
                'partials/result/livreur_error.html',
                {'errors': errors, 'admin_user': self.request.user},
            )

        return super().form_invalid(form)
