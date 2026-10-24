# BAKAMZONE — Journal de Bord & Parcours d'Avancement

> Ce document consigne l'historique précis des fonctionnalités implémentées, l'état de l'architecture et les prochaines étapes prioritaires pour garantir une continuité parfaite entre les sessions.

---

## 1. Vision & Architecture du Projet

* **Projet** : **BAKAMZONE** — Plateforme logistique intégrée de livraison de proximité.
* **Concept** :
  * Flotte propriétaire de **motos électriques**.
  * Modèle de **« Blocs » de quartier** (stockage de proximité, admins locaux, livreurs assignés).
  * Lancement initial ciblé sur **Ouagadougou** (Quartier pilote : **Tampouy**).
* **Les 4 Rôles Utilisateurs** :
  1. **Client** : Commande géolocalisée, paiement, suivi en direct.
  2. **Livreur** : Employé rattaché à un bloc spécifique, gestion de disponibilité et des courses.
  3. **Admin de Bloc** : Réception des stocks partenaires au bloc, supervision des équipes locales, dispatch.
  4. **Entreprise Partenaire** : Dépôt d'articles dans les blocs, suivi des ventes et des quantités restantes.
  5. *(+ Super Administrateur : Supervision globale du réseau et création des entités)*.

---

## 2. Stack Technique Validée

* **Backend** : Django 6.0.4 (Python 3.13)
* **Styling & UI** :
  * **Tailwind CSS v4** (`@tailwindcss/postcss`) + **DaisyUI v5.7**
  * Palette officielle : **Émeraude** (`#059669`) & **Orange** (`#F97316`)
  * Mode Sombre & Clair natif (`data-theme="light"` / `"dark"`)
* **Interactivité & Animations** :
  * **HTMX** (v1.9.12 / v2) pour les formulaires réactifs sans rechargement de page
  * **Alpine.js** pour les micros-états front-end (modals, toggle mot de passe)
  * **Lenis** (Smooth scroll fluide) synchronisé avec **GSAP** & **ScrollTrigger**
* **Approche** : Mobile-first PWA (Progressive Web App).

---

## 3. Ce qui a été Réalisé

### A. Configuration & Base Globale
- [x] Configuration de [`src/bakam_zone/settings.py`](file:///D:/SAAS_PROJECT/BAKAMZONE/src/bakam_zone/settings.py) :
  - Applications enregistrées (`auth_app`, `home_app`, `superuser_app`, `blocs_app`, etc.).
  - `AUTH_USER_MODEL = "auth_app.User"`.
  - Configuration Tailwind & Static files (`bakam_zone/static/`, `static/`).
  - `ALLOWED_HOSTS = ['*']` pour le développement local et mobile.
- [x] Scripts statiques locaux copiés dans [`src/static/vendor/js/`](file:///D:/SAAS_PROJECT/BAKAMZONE/src/static/vendor/js/) :
  - `htmx.min.js`, `gsap.min.js`, `ScrollTrigger.min.js`, `lenis.min.js`.
- [x] Template maître [`src/templates/base.html`](file:///D:/SAAS_PROJECT/BAKAMZONE/src/templates/base.html) :
  - Intégration Tailwind compilé (`{% tailwind_css %}`).
  - Header CSRF automatique pour HTMX (`X-CSRFToken`).
  - Réinitialisation d'Alpine.js sur événements `htmx:afterSwap`.
  - Conteneur DaisyUI automatique pour messages Django (Toasts).
  - Gestion du thème clair/sombre avec persistance `localStorage`.
- [x] Tailwind CSS vérifié et compilé (`src/theme/static_src/tailwind.config.js`) avec daisyUI 5.

### B. Gestion des Blocs (`blocs_app`)
- [x] Modèle complet [`Blocs`](file:///D:/SAAS_PROJECT/BAKAMZONE/src/blocs_app/models.py) dans [`src/blocs_app/models.py`](file:///D:/SAAS_PROJECT/BAKAMZONE/src/blocs_app/models.py) :
  - `nom` (unique) et `code` unique auto-généré (ex: `BLK-TAMPOUY`).
  - `ville` avec liste de choix `VILLE_CHOICES` (défaut : `'ouagadougou'`).
  - `quartier` avec liste de choix `QUARTIER_CHOICES` (défaut : `'tampouy'`).
  - `adresse`, `telephone`, `latitude`, `longitude`, `rayon_couverture_km` (5.00 km par défaut).
  - `capacite_stockage` (100) et `capacite_motos` (10).
  - Propriétés utilitaires : `.name` (rétro-compatibilité) et `.google_maps_url`.
- [x] Formulaire [`BlocForm`](file:///D:/SAAS_PROJECT/BAKAMZONE/src/superuser_app/forms.py) dans [`src/superuser_app/forms.py`](file:///D:/SAAS_PROJECT/BAKAMZONE/src/superuser_app/forms.py) :
  - Tous les widgets stylés avec DaisyUI & focus émeraude (`#059669`).
  - Validation personnalisée sur le nom du bloc.

### C. Authentification & Modals HTMX (`auth_app`)
- [x] Résolution et validation du chargement statique de `htmx.min.js` (HTTP 200 via `staticfiles_urlpatterns`).
- [x] Sécurisation du formulaire de connexion (`method="POST"` + `hx-post`) anti-fallback GET.
- [x] Formulaire [`ConnexionForm`](file:///D:/SAAS_PROJECT/BAKAMZONE/src/auth_app/forms.py) universel :
  - Connexion possible indifféremment par **Numéro de téléphone** OU **Nom d'utilisateur**.
- [x] Vues CBV dans [`src/auth_app/views.py`](file:///D:/SAAS_PROJECT/BAKAMZONE/src/auth_app/views.py) :
  - `ConnexionHTMXView` : validation et authentification par HTMX, calcul de redirection selon le rôle utilisateur (`is_superuser`, `administrateur`, `livreur`, `entreprise`, `client`).
  - `DeconnexionView` : déconnexion propre et redirection accueil.
- [x] Modal DaisyUI [`src/templates/modal/login_modal.html`](file:///D:/SAAS_PROJECT/BAKAMZONE/src/templates/modal/login_modal.html) :
  - Intégration `hx-post="{% url 'auth_app:connexion_htmx' %}"`, `hx-target="#login-result"`, `hx-indicator="#login-spinner"`.
  - Masquage/affichage dynamique du mot de passe avec Alpine.js.
- [x] Partials HTMX dans [`src/templates/partials/result/`](file:///D:/SAAS_PROJECT/BAKAMZONE/src/templates/partials/result/) :
  - `login_error.html` : alerte d'erreur DaisyUI.
  - `login_success.html` : alerte de succès et script de redirection fluide.

### D. Page d'Accueil Intelligente (`home_app`)
- [x] CBV [`HomePageView`](file:///D:/SAAS_PROJECT/BAKAMZONE/src/home_app/views.py) :
  - Fournit le formulaire de connexion, les blocs actifs, et adapte le contexte selon le rôle.
- [x] Template intelligent [`src/templates/home_templates/home_page.html`](file:///D:/SAAS_PROJECT/BAKAMZONE/src/templates/home_templates/home_page.html) :
  - Navbar responsive avec bascule de thème, détection de rôle de l'utilisateur connecté ou bouton *Connexion*.
  - Section dynamique selon le statut :
    - Non connecté : vitrine complète de BAKAMZONE, arguments de vente et bouton ouverture du modal.
    - Connecté : carte personnalisée selon le rôle (Superuser avec lien direct cockpit, Admin de bloc, Livreur, Entreprise, Client).
  - Grille réactive listant les blocs du réseau.

### E. Base de Données & Migrations
- [x] Migrations initiales créées et exécutées avec succès sur SQLite :
  - `auth_app`, `blocs_app`, `entreprise_app`, `clients_app`, `livreurs_app`, `articles_app`, `commandes_app`, `zones_app`, `avis_app`.
- [x] Tests de bout en bout validés : code HTTP 200 sur `/` et traitement HTMX validé.

---

## 4. Prochaines Étapes Immédiates (Roadmap)

1. **Modélisation de l'Équipe Admin de Bloc** :
   - Créer le modèle `AdminBloc` dans `src/admins_app/models.py` (liaison `User` + `Blocs` + poste/responsabilité).
2. **Formulaires Superuser (`superuser_app/forms.py`)** :
   - `AdminBlocForm` : création d'un administrateur rattaché à un bloc avec génération auto du username et mot de passe par UUID.
   - `LivreurForm` : création/rattachement d'un livreur à un bloc avec génération auto des accès par UUID.
3. **Vues CBV HTMX du Cockpit Superuser (`superuser_app/views.py`)** :
   - Vues de création avec swap dynamique HTMX (`hx-post`, `hx-target`, `hx-indicator`) pour rafraîchir la liste sans recharger la page.
   - Partials de succès / retour pour les créations de bloc, admin et livreur.
4. **Interface Superuser complète (`templates/superuser_template/superuser.html`)** :
   - Cockpit complet avec onglets DaisyUI ou modales dédiées pour ajouter un Bloc, une Équipe Admin, et des Livreurs.
5. **Services de notification des accès** :
   - Module d'envoi des identifiants générés (Email + WhatsApp Cloud API / Meta).

---

## 5. Historique chronologique des sessions de travail

> Horaires enregistrés en UTC. Les sessions sont classées par date et heure de début. Quand le transcript détaillé n'est pas disponible, le résumé se limite au titre et aux métadonnées de la session.

### 19 octobre 2026

- **15:44–15:45 — « problème avec python manage.py tailwind init »**
  - Session consacrée au problème rencontré lors de la commande `python manage.py tailwind init`.
  - Le détail du diagnostic n'est pas disponible dans l'historique consultable.

### 20 octobre 2026

- **15:26–17:20 — « le post par en get pk »**
  - Session autour d'un problème où une requête ou un formulaire attendu en `POST` partait en `GET`, avec une question concernant une clé primaire (`pk`).
  - Le détail du diagnostic et de la solution n'est pas disponible dans l'historique consultable.

### 21 octobre 2026

- **09:03–11:37 — « Inscription livreur avec UUID »**
  - Session de travail sur l'inscription d'un livreur avec UUID.
  - Métadonnées : 40 fichiers concernés, 3 645 ajouts et 314 suppressions.
  - Le transcript détaillé n'est pas disponible ; vérifier l'état du code avant de reprendre les étapes de la roadmap.

### 22 octobre 2026

- **08:59–10:21 — « condition if password dans clean »**
  - Échange sur l'utilité de vérifier `if password:` dans `clean()`.
  - La condition évite de lancer la validation du mot de passe lorsque la valeur est absente ou vide.

- **16:47–17:04 — « Explanation of get_entreprise method »**
  - Explications sur la mise en cache de l'entreprise dans `self.entreprise`, l'usage de `kwargs.pop("instance", None)` dans `get_form_kwargs()`, et des propriétés de quotas dépendant du palier.
  - Un possible typo dans `self.atiicles` a également été signalé comme point à vérifier.

### 23 octobre 2026

- **09:15–15:02 — « Formulaires pour ajout d'articles »**
  - Session de travail consacrée aux formulaires d'ajout d'articles.
  - Métadonnées : 30 fichiers concernés, 1 940 ajouts et 22 suppressions.
  - Le transcript détaillé n'est pas disponible ; vérifier le code actuel avant de considérer cette partie comme terminée.

### 24 octobre 2026

- **10:05–en cours — « liste des sessions projet »**
  - Recensement des sessions associées au projet, puis mise à jour de ce journal pour conserver leur ordre chronologique et leurs horaires.

### Point de reprise

La roadmap de la section 4 correspond à l'état antérieur à l'historique ci-dessus. Les sessions suivantes mentionnent notamment l'inscription des livreurs avec UUID et les formulaires d'ajout d'articles, mais leurs transcripts détaillés ne sont pas tous accessibles. Il faut donc vérifier l'état présent du code avant de marquer les étapes de la roadmap comme terminées ou de décider de la prochaine tâche.

---

## 6. Travail réalisé — 24 octobre 2026

### Gestion des articles par le gestionnaire de stock

- Ajout d'une fiche entreprise accessible depuis la liste du tableau de bord du gestionnaire de stock.
- La fiche est réservée à un utilisateur `role == "bloc_admin"` disposant d'un profil actif avec `poste == "gestionnaire_stock"` (valeur du modèle ; « gestionnaire_de_stkok » était une faute de frappe dans la demande).
- Ajout du CRUD des articles de l'entreprise avec `ArticleBlocAdminForm` :
  - création d'un article lié à l'entreprise sélectionnée et ajout d'un stock initial à zéro dans le bloc de l'administrateur ;
  - modification et suppression des articles de cette entreprise ;
  - refus des accès d'autres rôles/postes et des tentatives de modifier un article d'une autre entreprise.
- La confirmation de suppression précise que la suppression de l'article retire également ses stocks dans les autres blocs.
- Vérification : `manage.py test admins_app.tests articles_app.tests` — 47 tests réussis.
- Limite constatée hors périmètre : l'exécution incluant `entreprise_app.tests` rencontre trois erreurs préexistantes dues aux tests qui inversent `entreprise_app:detail`, nom d'URL absent du routeur actuel.

### Transmission de l'entreprise au formulaire d'article

- Dans `ArticleBlocAdminAccessMixin.dispatch()`, `self.entreprise` est initialisée depuis le `entreprise_pk` de l'URL. C'est une instance du modèle `Entreprise`, pas l'entreprise récupérée depuis l'article.
- Les vues de création et de modification ajoutent cette instance aux arguments du formulaire dans `get_form_kwargs()` avec `user=self.request.user` et `entreprise=self.entreprise`.
- Django transmet ces arguments nommés au constructeur `ArticleBlocAdminForm.__init__()`. Le formulaire les conserve dans `self.user` et `self.entreprise`, car ses méthodes `clean()` et `save()` en ont besoin après l'initialisation.
- À la création, `save()` associe l'article à `self.entreprise`. À la modification, `get_queryset()` restreint d'abord l'article à cette même entreprise ; `self.entreprise` est donc celle qui lui est associée, sans être obtenue directement via `article.entreprise`.
