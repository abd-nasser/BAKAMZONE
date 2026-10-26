from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import login, logout, get_user_model
from django.db.models import Q
from django.urls import reverse
from auth_app.forms import ConnexionForm
from admins_app.dashboard_routes import get_admin_bloc_dashboard_url

User = get_user_model()


class ConnexionHTMXView(View):
    """
    Vue de connexion traitée via HTMX.
    Identifie l'utilisateur par téléphone ou nom d'utilisateur,
    puis renvoie le fragment partial approprié (succès ou erreur) vers #login-result.
    """

    def post(self, request, *args, **kwargs):
        form = ConnexionForm(request.POST)

        if not form.is_valid():
            return render(
                request,
                'partials/result/login_error.html',
                {'error': "Veuillez renseigner tous les champs correctement."}
            )

        identifiant = form.cleaned_data['identifiant'].strip()
        password = form.cleaned_data['password']

        # Recherche de l'utilisateur par téléphone ou username
        user = User.objects.filter(
            Q(telephone__iexact=identifiant) | Q(username__iexact=identifiant)
        ).first()

        if user is None or not user.check_password(password):
            return render(
                request,
                'partials/result/login_error.html',
                {'error': "Identifiant ou mot de passe incorrect."}
            )

        if not user.is_active:
            return render(
                request,
                'partials/result/login_error.html',
                {'error': "Ce compte est désactivé. Veuillez contacter le support BAKAMZONE."}
            )

        # Authentification réussie
        login(request, user)

        # Détermination de l'URL de redirection selon le rôle
        redirect_url = reverse('home_app:home')
        if user.is_superuser:
            redirect_url = reverse('superuser_app:dashboard')
        elif user.role == 'bloc_admin':
            redirect_url = (
                get_admin_bloc_dashboard_url(user)
                or reverse('home_app:home')
            )
        elif user.role == 'livreur':
            redirect_url = reverse('home_app:home')  # ou dashboard livreur
        elif user.role == 'client':
            redirect_url = reverse('clients_app:tableau-de-bord')
        elif user.role == 'entreprise':
            redirect_url = reverse('home_app:home')  # ou dashboard entreprise

        response = render(
            request,
            'partials/result/login_success.html',
            {
                'user': user,
                'redirect_url': redirect_url,
            }
        )
        # Permet aussi à HTMX de déclencher la redirection automatique côté client si nécessaire
        response['HX-Redirect'] = redirect_url
        return response


class DeconnexionView(View):
    """Déconnexion standard et redirection vers l'accueil"""

    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect('home_app:home')

    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect('home_app:home')
