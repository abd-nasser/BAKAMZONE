from django.urls import path
from home_app.views import HomePageView

app_name = 'home_app'

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
]
