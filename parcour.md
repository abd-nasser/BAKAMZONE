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
  - `auth_app`, `blocs_app`, `entreprise_app`, `clients_app`, `livreurs_app`, `articles_app`, `demande_livraison_app`, `zones_app`, `avis_app`.
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
   - Le backend SMTP et la tâche Celery d'envoi des emails sont configurés ; il reste à les intégrer aux créations d'accès.
   - Une tâche Celery d'envoi de notifications texte via WhatsApp Cloud API est maintenant ajoutée ; les identifiants restent vides jusqu'à leur obtention.

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

### Renommage du domaine des demandes de livraison

- Remplacement de `commandes_app` par `demande_livraison_app` afin de distinguer les demandes de livraison des commandes d'articles.
- Renommage du modèle `Commande` en `DemandeLivraison` ; ses relations client, livreur et zones utilisent désormais des libellés `demandes_livraison`.
- Mise à jour de la relation d'avis livreur vers `DemandeLivraison`. La migration conserve la colonne de base de données `commande_id` et reprend la table historique pour préserver les données existantes.
- Mise à jour de la liste des applications dans `INSTALLED_APPS` et suppression des références Python à `commandes_app`.

### Dashboard du superviseur de flotte

- Le dashboard `SuperviseurFlotteDashbordView` présente maintenant deux accès distincts : la liste des livreurs et la liste des demandes de livraison, avec leurs compteurs.
- La vue `LivreurListView` conserve la recherche de livreurs par nom, prénom, téléphone ou identifiant.
- La vue `DemandeLivraisonListView` liste les demandes dont le départ ou l'arrivée concerne le bloc du superviseur, ainsi que celles attribuées à un livreur de ce bloc. La recherche porte sur le client, son téléphone, la description du colis et les zones.
- L'accès aux trois vues est réservé aux comptes `bloc_admin` disposant d'un profil actif `superviseur_flotte`.
- Vérification : `manage.py test admins_app` — 20 tests réussis ; `manage.py check` et `manage.py makemigrations --check --dry-run` ne signalent pas d'erreur ni de changement manquant.
- La migration `avis_app.0002_add_demande_livraison` reste à appliquer sur la base configurée (`manage.py migrate`).

## 7. Travail réalisé — 26 octobre 2026

### Configuration mail et envoi asynchrone avec Celery

- Configuration SMTP Gmail sur SSL (`smtp.gmail.com:465`) avec identifiants lus depuis l'environnement : `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` et `DEFAULT_FROM_EMAIL` (facultatif, par défaut l'adresse utilisateur). Le délai SMTP est configurable avec `EMAIL_TIMEOUT` (10 secondes par défaut).
- Configuration Celery avec Redis, URLs du broker et du backend de résultats configurables via `CELERY_BROKER_URL` et `CELERY_RESULT_BACKEND`. Le worker découvre la tâche `bakam_zone.tasks.send_email_task`.
- La tâche envoie les versions texte et HTML, utilise l'expéditeur par défaut si aucun expéditeur n'est fourni, refuse les listes de destinataires vides et ne journalise pas leurs adresses. Les erreurs SMTP et réseau sont relancées avec backoff ; les erreurs de configuration ou d'arguments ne sont pas relancées automatiquement.
- Dépendances Celery et Redis ajoutées à `requirements.txt`.
- Démarrage du worker depuis le dossier `src` : `celery -A bakam_zone worker --loglevel=INFO` (Redis doit être disponible).
- Une tâche `bakam_zone.tasks.send_whatsapp_notification_task` envoie un message texte via l'API Graph, renvoie l'identifiant Meta du message et relance les erreurs réseau/temporaires avec backoff. Elle requiert un numéro au format international et un message non vide.
- Paramètres à renseigner quand l'accès Meta sera prêt : `WHATSAPP_PHONE_NUMBER_ID` et `WHATSAPP_ACCESS_TOKEN` (laissés vides pour l'instant). `WHATSAPP_API_VERSION` vaut `v22.0` par défaut et `WHATSAPP_API_TIMEOUT` vaut 10 secondes ; ils restent configurables par variables d'environnement.
- L'envoi email et WhatsApp doit encore être appelé par les vues/services de création des identifiants. Les messages texte libres sont soumis aux règles de fenêtre de conversation de WhatsApp ; hors fenêtre, il faudra utiliser des modèles approuvés par Meta.
- Vérification : `manage.py check`, tests unitaires mail/WhatsApp et vérification de l'enregistrement des tâches dans l'application Celery.

## 8. Espace client — 26 octobre 2026

- Création de `ClientDashboardView` et de son template `clients_templates/client_dashboard.html`, accessibles aux comptes clients possédant un profil client.
- Première section : livreurs actifs, avec recherche (nom, téléphone, bloc/quartier), filtres par véhicule, bloc et favoris. Le statut disponible/indisponible est affiché ; les liens « Voir le profil » et « Chat » sont provisoirement `#`.
- Deuxième section : articles actifs, en bloc, non expirés et ayant du stock dans au moins un bloc actif ; recherche par nom, description ou entreprise, filtre entreprise/promotion et tri par prix ou date.
- Les formulaires des deux sections conservent les filtres de l'autre section. Les clients sont redirigés vers leur dashboard après connexion et disposent d'un lien vers cet espace dans la navigation.
- Les filtres sont actualisés par HTMX : recherche après frappe avec délai de 350 ms, filtres sur changement et résultats remplacés séparément pour chaque section. Une requête HTMX renvoie uniquement le partial correspondant.
- Ajout de `LivreurProfilViewByClient` (`DetailView`, modèle `Livreur`) et de sa route `clients_app:profil-livreur`. La vue est réservée aux clients ayant un profil client et limite les profils consultables aux livreurs actifs rattachés à un bloc actif. Le lien « Voir le profil » ouvre cette page ; le chat reste provisoirement `#`.
- Vérification : `manage.py test clients_app.tests auth_app.tests` — 18 tests réussis avant l'ajout du profil ; `manage.py test clients_app.tests` — 15 tests réussis après l'ajout ; `manage.py check`, `makemigrations --check --dry-run` et `git diff --check` sans erreur.

## 9. Modèle de livraison — géolocalisation du destinataire — 26 octobre 2026

- Le modèle `DemandeLivraison` prévoit maintenant un numéro WhatsApp pour le destinataire et un `token_pwa_destinataire` UUID unique, généré automatiquement et non modifiable. Ce token sert de clé d'accès au lien PWA de partage de position, sans compte destinataire ; il n'expire pas actuellement.
- Les coordonnées estimées d'arrivée sont facultatives ; les coordonnées GPS réelles du destinataire sont enregistrées séparément. `position_destinataire_validee` et `statut_destinataire` permettent de suivre l'état de la réponse et de prévoir une escalade vers l'assistant du bloc après trois minutes.
- `date_acceptation` complète les horodatages de la demande. Le modèle déclare également un index dédié au token pour les recherches par lien PWA.
- Le flux côté livreur et destinataire a depuis été implémenté : affichage des demandes du bloc et des demandes directes dans son tableau de bord, acceptation/refus, programmation de la notification WhatsApp avec lien GPS, récupération de la demande par UUID, validation/enregistrement de la position et tâche d'escalade après trois minutes. Le détail du fonctionnement et les limites restantes sont documentés dans [`client_demande_livraison_workflow.md`](./client_demande_livraison_workflow.md).
- La partie opérationnelle de l'assistant reste à développer : le délai dépassé passe `statut_destinataire` à `alerte_assistant`, mais aucun tableau de bord ni outil d'appel manuel dédié n'est encore fourni. L'envoi WhatsApp réel dépend de la configuration de Meta, Redis/Celery et de l'URL publique HTTPS.
- La note de report des migrations est obsolète : la migration `demande_livraison_app.0002_demandelivraison_date_acceptation_and_more` a été appliquée le 27 octobre 2026 (voir section 10).


## 10. Workflow de livraison & Smart-Drop (Section 1) — 27 octobre 2026

- Application de la migration `demande_livraison_app.0002_demandelivraison_date_acceptation_and_more` avec génération sécurisée du token unique UUID, index et statuts de suivi.
- Moteur de tarification `src/demande_livraison_app/pricing.py` : calcul selon matrice Zone-à-Zone (forfait intra-bloc à 1 000 FCFA, majoration inter-blocs à 1 500 FCFA, configurables via settings).
- Formulaire `DemandeLivraisonForm` (`src/demande_livraison_app/forms.py`) : sélection des zones de départ et d'arrivée, capture des coordonnées GPS avec repli sur la position de la zone de départ, validation du numéro WhatsApp du destinataire et calcul sécurisé du prix côté serveur.
- Vue client `CreerDemandeLivraisonView` (`src/demande_livraison_app/views.py`) et endpoint JSON `CalculerTarifView`, branchés sous le namespace `demande_livraison_app`.
- Template mobile-first `creer_demande.html` avec Alpine.js : bouton de géolocalisation GPS en un clic avec gestion des erreurs et des états de chargement, affichage réactif immédiat du tarif garanti et du badge de secteur (Intra-bloc / Inter-blocs).
- Intégration du bouton « ⚡ Commander une livraison » dans le tableau de bord client (`client_dashboard.html`) et ajout d'un accès rapide dans la barre de navigation (`base.html`).
- Tests unitaires et d'intégration validés (`manage.py test demande_livraison_app.tests`) : 11 tests réussis.


## 11. Refactorisation du profil Livreur & Commande Directe — 27 octobre 2026

- **Modèle Livreur** : Ajout de la propriété `nb_ajout_favoris` basée sur le comptage de la relation `favoris_de`.
- **Vue `LivreurProfilViewByClient`** :
  - Support de la réservation directe par `POST` : instanciation et validation de `DemandeLivraisonForm`, assignation directe au livreur ciblé (`demande.livreur = self.object`), statut `en_attente` et redirection vers le tableau de bord avec message flash.
  - Enrichissement du contexte `GET` : injection du formulaire pré-rempli (zone actuelle du livreur), statuts de favoris (`est_favori`, `nb_favoris`), liste des avis récents (`avis_list`, `nb_avis`), tarifs et zones disponibles.
- **Ajout/Retrait des favoris (Likes)** :
  - Nouvelle vue `ToggleFavoriLivreurView` (`clients_app:toggle-favori-livreur`).
  - Partial HTMX `src/templates/partials/clients/livreur_favori_button.html` pour basculer en temps réel le like/favori et incrémenter le compteur sans recharger la page.
- **Design du template `livreur_profil.html` façon profil réseau social** :
  - Grande bannière de couverture avec pastille de disponibilité en direct (*En ligne* vert pulsé / *Hors ligne*).
  - Avatar rond avec bordure épaisse, badge officiel certifié BAKAMZONE et handle `@username`.
  - Barre de compteurs sociaux : ❤️ **Favoris / Likes**, 📦 **Courses livrées**, ⭐ **Note globale / 5**, 🛵 **Véhicule**.
  - Section de commande directe intégrée avec bouton Alpine.js de capture GPS, sélection de zones et calcul de tarif garanti en temps réel.
  - Section avis & retours d'expérience clients avec étoiles (1 à 5), nom abrégé, date relative et commentaire.
- **Tests** : 18 tests `clients_app.tests` réussis (dont commande directe, bascule de favoris en HTMX et affichage des avis).

## 12. Workflow livreur et Smart-Drop — 27 octobre 2026

- Reprise et achèvement du flux de traitement d'une demande depuis l'espace livreur : demandes directes ou ouvertes dans le bloc, actions POST accepter/refuser, changement de statut de course et suivi de la position destinataire.
- Sécurisation de l'acceptation par mise à jour conditionnelle : seule une demande en attente qui est attribuée au livreur courant ou ouverte dans son bloc peut être acceptée, et la prise concurrente est évitée.
- Après acceptation, programmation Celery de la notification Smart-Drop : récupération par identifiant de demande, construction de l'URL `/geo/verify/<token_pwa_destinataire>/`, tentative d'envoi WhatsApp et planification du contrôle de délai à 180 secondes.
- Implémentation de l'accès public destinataire via UUID, capture GPS mobile et validation des plages de coordonnées avant enregistrement. Le token est unique mais n'expire pas encore ; le tableau de bord assistant et ses actions manuelles restent hors périmètre.
- Documentation détaillée du flux, des routes, des tâches, de la récupération de la demande par token et des limites dans [`client_demande_livraison_workflow.md`](./client_demande_livraison_workflow.md).
- Vérification : 35 tests réussis sur `livreurs_app.tests`, `bakam_zone.tests` et `demande_livraison_app.tests` ; contrôle syntaxique Python et `git diff --check` sans erreur.
