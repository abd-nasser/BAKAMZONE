from django.urls import path
from superuser_app.views import SuperuserDashboardView

app_name = 'superuser_app'

urlpatterns = [
    path('', SuperuserDashboardView.as_view(), name='dashboard'),
]
