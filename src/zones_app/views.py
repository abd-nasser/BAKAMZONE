from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from zones_app.forms import ZoneForm
from zones_app.models import Zone


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


class ZoneCreateView(SuperuserRequiredMixin, CreateView):
    model = Zone
    form_class = ZoneForm
    template_name = 'blocs_template/create_zone.html'
    success_url = reverse_lazy('superuser_app:dashboard')

    def form_valid(self, form):
        self.object = form.save()
        if self.request.headers.get('HX-Request') == 'true':
            response = render(
                self.request,
                'partials/result/zone_success.html',
                {'zone': self.object},
            )
            response['HX-Trigger'] = 'zoneCreated'
            return response
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        if self.request.headers.get('HX-Request') == 'true':
            errors = [
                error
                for field_errors in form.errors.values()
                for error in field_errors
            ]
            return render(
                self.request,
                'partials/result/zone_error.html',
                {'errors': errors},
            )
        return super().form_invalid(form)
