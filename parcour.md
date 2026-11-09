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
- Le tableau de bord assistant et ses outils de traitement manuel ont été ajoutés le 1er novembre 2026 (voir section 13). L'envoi WhatsApp réel dépend toujours de la configuration de Meta, Redis/Celery et de l'URL publique HTTPS.
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
- Implémentation de l'accès public destinataire via UUID, capture GPS mobile et validation des plages de coordonnées avant enregistrement. Le token est unique mais n'expire pas encore.
- Documentation détaillée du flux, des routes, des tâches, de la récupération de la demande par token et des limites dans [`client_demande_livraison_workflow.md`](./client_demande_livraison_workflow.md).
- Vérification : 35 tests réussis sur `livreurs_app.tests`, `bakam_zone.tests` et `demande_livraison_app.tests` ; contrôle syntaxique Python et `git diff --check` sans erreur.

## 13. Dashboard assistant opérationnel — 1er novembre 2026

- Confirmation que la tâche 4 de `bakamzone_todo_list.md` est le dashboard assistant de bloc, distinct de l'ancienne tâche 4 de la roadmap superuser en section 4 de ce journal.
- Remplacement de la page générique assistant par un dashboard listant les livraisons actives impliquant le bloc et les alertes destinataire `alerte_assistant`, avec actualisation HTMX toutes les 30 secondes.
- Ajout des outils de résolution pour les alertes : appel direct depuis le téléphone via `tel:`, saisie manuelle de coordonnées GPS avec validation, et statut `injoignable`. Les requêtes d'action sont limitées aux livraisons actives de la région du bloc et à un profil assistant actif.
- Mise à jour de `bakamzone_todo_list.md` : étapes Smart-Drop et escalade marquées terminées ; les deux sous-tâches du dashboard assistant sont également terminées.
- Vérification ciblée : 11 tests assistant et WhatsApp réussis ; `manage.py check` sans problème.

## 14. Détail des blocs et support client — 2 novembre 2026

- Création de la detailView client d'un bloc actif : affichage de ses zones rattachées, de ses livreurs actifs, de leur disponibilité et de leur profil.
- Ajout de liens vers le détail depuis l'espace client et les blocs listés sur l'accueil. Les liens de l'accueil ne sont visibles que pour un utilisateur connecté avec `role == "client"`.
- Création d'une messagerie persistante entre un client et l'assistant opérationnel actif de son bloc, avec une conversation par client et par bloc, actualisation HTMX du fil et signalement lorsque le bloc n'a aucun assistant actif.
- Ajout de la boîte de réception au tableau de bord assistant ; les conversations sont limitées au bloc de l'assistant connecté et l'accès au fil est réservé au client concerné et à un assistant actif de ce bloc.
- Ajout de la migration `clients_app.0002_supportconversation_supportmessage_and_more`.
- Vérification : tests ciblés du détail, du chat, de l'assistant et de la page d'accueil réussis ; `manage.py check`, `makemigrations --check --dry-run` et `git diff --check` sans erreur. La suite complète a révélé trois erreurs préexistantes de résolution de l'URL `entreprise_app:detail`.

## 15. Notifications Web Push pour la messagerie PWA — 3 novembre 2026

- Ajout du manifeste `src/static/manifest.json`, des icônes PWA (192×192, 512×512) et de l'icône Apple (180×180), puis intégration du manifeste et du bouton d'activation dans `src/templates/base.html`.
- Le bouton visible pour les utilisateurs connectés demande explicitement la permission, récupère la clé publique VAPID et enregistre la souscription avec CSRF. Les routes sont `POST /notifications/pwa/subscribe/`, `POST /notifications/pwa/unsubscribe/` et `GET /notifications/pwa/vapid-key/`.
- Le service worker est servi à la racine par `GET /sw.js` avec `Service-Worker-Allowed: /`. Il affiche les événements `push` et, au clic, ouvre la conversation dans la même origine.
- La tâche `notifier_nouveau_message_support_task` détermine si le destinataire est l'assistant actif du bloc ou le client, puis met en file l'envoi Web Push. `envoyer_notification_webpush_task` envoie via `pywebpush`, purge les souscriptions HTTP 404/410, retente les erreurs temporaires et ne compte plus une simulation comme un envoi réussi.
- Les paramètres `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` et `VAPID_ADMIN_EMAIL` sont lus depuis l'environnement ; `pywebpush==2.5.0` est ajouté à `requirements.txt`.
- Vérification locale : 20 tests ciblés (`notifications_app.tests` et `clients_app.tests.ClientBlocDetailAndSupportChatTests`) réussis ; `manage.py check`, `makemigrations --check --dry-run`, `node --check` pour les deux fichiers JavaScript et `git diff --check` réussis.
- Limite de l'environnement : l'interpréteur local est une build free-threaded Python 3.13, qui ne permet pas l'installation de CFFI/Cryptography requise par `pywebpush`. Le test de la tâche utilise un fournisseur simulé. Avant un envoi réel, installer les dépendances dans un CPython standard, configurer les clés VAPID et démarrer Redis/Celery ; le site doit être accessible en HTTPS.
- Extension du flux le 3 novembre 2026 : lorsqu'un livreur accepte une demande, `notifier_acceptation_demande_livraison_task` programme une notification push pour le client, avec le nom du livreur et un lien vers son tableau de bord. Une indisponibilité du broker pour le push est signalée sans empêcher la programmation du message WhatsApp Smart-Drop.
- Vérification de cette extension : 13 tests ciblés des flux d'acceptation livreur et des tâches Web Push réussis, avec `manage.py check` sans problème. L'envoi réel reste à valider avec les clés VAPID, Redis/Celery et un abonnement actif.

## 16. Préparation du suivi livreur en temps réel — 3 novembre 2026

- Création de [`suivis_livreur_temp_reel.md`](./suivis_livreur_temp_reel.md) comme référence d'architecture et de reprise pour la branche `features/web_socket_livreur_deplacement`. Le document comprend une explication simple, le flux proposé Django Channels/WebSocket/Redis, les règles d'accès et de vie privée, la résilience mobile ainsi que les étapes à réaliser pour Agy.
- État initial vérifié : le modèle `Livreur` possède des coordonnées courantes et `PositionLivreur` conserve des points historiques, mais aucune émission GPS pendant une course, diffusion WebSocket, intégration cartographique ou configuration Channels n'est encore implémentée.
- Ajout de la section 7 à [`bakamzone_todo_list.md`](./bakamzone_todo_list.md) avec les fondations existantes et les étapes non réalisées : décisions métier, carte, infrastructure ASGI/Redis, permissions, émission GPS, diffusion, interface, tests et validation terrain.
- Pas de code applicatif modifié à cette étape ; le suivi en temps réel reste à développer et à tester.
- Précision de périmètre : le suivi ne concerne pas seulement le client. Le superviseur de flotte (`role="bloc_admin"`, profil `AdminBloc` actif avec `poste="superviseur_flotte"`) doit aussi suivre les courses des livreurs rattachés à son bloc. L'architecture, les critères d'autorisation WebSocket et les tests à prévoir ont été mis à jour en conséquence dans [`suivis_livreur_temp_reel.md`](./suivis_livreur_temp_reel.md) et [`bakamzone_todo_list.md`](./bakamzone_todo_list.md).

## 17. Cadrage métier du suivi livreur — 4 novembre 2026

- Décision : le suivi ne démarre pas à la seule acceptation de la demande. Il commence lorsque les coordonnées GPS du destinataire sont validées (par le destinataire via la PWA ou saisies par l'assistant) et disponibles au livreur assigné. Le suivi s'arrête à la livraison, à l'annulation ou à la désassignation du livreur.
- À cette disponibilité, le client doit recevoir une Web Push l'informant que les coordonnées de localisation du destinataire sont disponibles pour le livreur ; aucun accusé de réception manuel du livreur n'est requis. L'envoi effectif nécessite une souscription Push active. Le suivi est alors activé, et la collecte GPS commence lorsque le livreur ouvre sa course et autorise la géolocalisation.
- Politique de position : transmission GPS toutes les 15 secondes au plus ; un point historique `PositionLivreur` toutes les 60 secondes au plus ; purge automatique de l'historique après 7 jours.
- Les lecteurs restent le client propriétaire de la demande et le superviseur de flotte actif du bloc du livreur. La première tâche de cadrage de la section 7 est terminée et les étapes d'implémentation correspondantes sont ajoutées à [`bakamzone_todo_list.md`](./bakamzone_todo_list.md) et [`suivis_livreur_temp_reel.md`](./suivis_livreur_temp_reel.md).
- Choix cartographique initial : Leaflet avec cartographie OpenStreetMap. Le client suivra une seule livraison active ; le superviseur aura une vue multi-courses limitée à son bloc avec liste et filtres. Le mode d'hébergement des tuiles a été décidé ensuite (voir section 18).
- Mise à jour initiale de la TODO : la décision cartographique et UX est terminée ; l'intégration de Leaflet et la configuration des tuiles restent à réaliser.

## 18. Choix d'hébergement des tuiles cartographiques — 4 novembre 2026

- Choix initial : auto-héberger les tuiles OpenStreetMap pour Ouagadougou et ses environs sur le KVM 2 alors envisagé pour Django/Nginx.
- Caractéristiques annoncées à cette date : 2 vCPU, 8 Go RAM, 100 Go NVMe et 8 To de bande passante. Leaflet, le serveur de tuiles et les données cartographiques n'étaient pas déployés.
- Ce choix d'hébergement a été remplacé par la décision en section 19. La souscription/migration et la mesure des ressources libres restent à faire.

## 19. Passage au KVM 4 — 4 novembre 2026

- Décision : retenir le KVM 4 et écarter le KVM 2 pour l'hébergement cible de l'application et des tuiles OpenStreetMap auto-hébergées pour Ouagadougou et environs.
- Caractéristiques annoncées du KVM 4 : 4 vCPU, 16 Go RAM, 200 Go NVMe et 16 To de bande passante mensuelle. Ces capacités sont nominales ; la place réellement disponible après système, Django, Redis et autres services devra être mesurée.
- La souscription ou migration vers le KVM 4 n'est pas présumée effectuée. La TODO, le plan stratégique et [`suivis_livreur_temp_reel.md`](./suivis_livreur_temp_reel.md) sont mis à jour avec cette cible et les prochaines étapes.

## 20. Début du développement Channels local — 4 novembre 2026

- La souscription/migration KVM 4 et la mise en place du serveur de tuiles OSM sont reportées jusqu'à ce que la feature soit prête pour les tests de production ; elles ne bloquent pas le développement WebSocket local.
- Ajout de `channels==4.3.2`, `channels-redis==4.3.0` et `daphne==4.2.3`. Configuration du channel layer `channels_redis` via `CHANNEL_REDIS_URL`, avec Redis `/2` par défaut (Celery conserve `/0` et `/1`).
- Configuration de l'application ASGI pour HTTP et WebSocket, authentification de session et validation via la liste `WEBSOCKET_ALLOWED_ORIGINS`. Le routage WebSocket est préparé, mais ne contient pas encore de route ni de consumer de suivi.
- Vérification de l'installation dans un Python 3.13 standard : `manage.py check` et les 9 tests de `bakam_zone.tests` réussissent. Tests ajoutés pour le channel layer Redis, le routeur ASGI et le refus des origines non autorisées.
- La réception/validation des coordonnées GPS, leur persistance/diffusion et le test avec Redis local restent à faire.

## 21. Routes et autorisations WebSocket du suivi — 4 novembre 2026

- Ajout de la route `/ws/livraisons/<id>/suivi/` et du consumer de suivi.
- Le serveur n'accepte que les courses acceptées/en cours, attribuées à un livreur actif, avec coordonnées validées du destinataire.
- Accès réservé au livreur assigné, au client propriétaire ou au superviseur de flotte actif du bloc du livreur ; les autres connexions sont refusées.
- Autorisations revalidées à chaque diffusion ; un superviseur dont le profil est désactivé est déconnecté avant de recevoir une position.
- Tests couvrant l'accès autorisé/refusé pour ces profils, la révocation d'un accès, les demandes terminées et le suivi non encore activé.
- L'émission des coordonnées, leur validation/persistance et leur diffusion sont encore à implémenter ; les tests de connexions utilisent le channel layer mémoire, aucun Redis local n'a été testé.

## 22. Émission et diffusion GPS du livreur — 4 novembre 2026

- À la première validation des coordonnées du destinataire, par la PWA ou par la saisie manuelle de l'assistant, programmation d'une Web Push au client ; les mises à jour ultérieures n'envoient pas de notification répétée. Une indisponibilité du broker est signalée sans perdre les coordonnées enregistrées.
- Ajout au tableau de bord livreur d'un démarrage/arrêt volontaire du GPS, avec demande de permission du navigateur et envoi WebSocket au plus toutes les 15 secondes.
- Le serveur n'accepte les coordonnées que du livreur assigné sur une demande active et activée ; il vérifie les bornes GPS et applique sa propre limite de cadence.
- Enregistrement de la position courante avec son horodatage, création d'un point d'historique au plus toutes les 60 secondes et diffusion réservée au groupe privé de la course.
- Ajout de `Livreur.position_suivi_mise_a_jour` et de sa migration pour permettre le contrôle serveur de la cadence, y compris après reconnexion.
- Tests couvrant l'émission autorisée, la cadence 15/60 s, les coordonnées invalides, l'interdiction d'émission par un lecteur, la Web Push unique et l'affichage du contrôle GPS.
- Les interfaces de suivi client/superviseur restent à développer. Les tests WebSocket utilisent le channel layer mémoire ; Redis local n'a pas encore été vérifié.

## 23. Purge de l'historique GPS — 9 novembre 2026

- Ajout de `livreurs_app.tasks.purger_historique_positions_task`, qui supprime les points `PositionLivreur` de plus de 7 jours et journalise le nombre supprimé.
- Configuration Celery Beat pour exécuter la purge chaque jour à 02:00 UTC. Le service Beat doit être démarré séparément du worker Celery pour que la planification soit effective.
- Tests couvrant le seuil exact de 7 jours, la conservation des points récents, une purge vide et la configuration de la planification.

## 24. Cartes de suivi client et superviseur — 9 novembre 2026

- Ajout d'une page de suivi accessible depuis les livraisons actives du tableau de bord client ; la vue renvoie 404 si la demande n'appartient pas au client connecté.
- Ajout d'une carte Leaflet multi-courses dans le tableau de bord du superviseur de flotte, limitée aux courses GPS actives des livreurs de son bloc, avec recherche par livreur, client et zones.
- Les pages se connectent aux WebSockets par course et affichent le marqueur uniquement après réception d'une nouvelle position ; aucune position persistée au niveau du livreur n'est traitée comme une position récente de la course.
- Ajout de l'heure de dernière position, de l'indication de coupure et d'obsolescence après 45 secondes, ainsi que d'une reconnexion avec délai progressif.
- L'URL des tuiles est configurable avec `OPENSTREETMAP_TILE_URL`. La valeur de développement utilise le service public OSM ; le service régional auto-hébergé reste à configurer pour la production sur le KVM 4.
- Ajout de tests de périmètre client et superviseur. Leur exécution reste à valider : l'écart préexistant entre `statut_position_destinataire` dans le modèle et les migrations empêche déjà les tests liés aux demandes de livraison de démarrer correctement.

## 25. Migration et validation du suivi GPS — 9 novembre 2026

- Application de la migration de renommage `statut_destinataire` vers `statut_position_destinataire`, sans recréer la colonne ni perdre ses données.
- Alignement des références restantes dans le workflow livreur, le tableau du livreur, le tableau de l'assistant et les tests.
- Validation : 49 tests des demandes de livraison, des vues client et du tableau superviseur réussis ; 7 tests du workflow livreur réussis. `manage.py check` et `makemigrations --check --dry-run --noinput` réussissent aussi.
- Restent à faire : tests avec Redis/Daphne réels, coupures/reconnexions, HTTPS/WSS derrière proxy et validation sur téléphone.
