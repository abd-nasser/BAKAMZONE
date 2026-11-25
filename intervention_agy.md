# Rapport d'Intervention — Antigravity (Agy)

**Date & Horodatage :** 9 novembre 2026 à 11:12:00 UTC  
**Branche Git :** `feature/panier_client`  
**Projet :** BAKAMZONE — Plateforme logistique de livraison intégrée  

---

## 1. Contexte & Objectifs de l'Intervention

L'intervention a porté sur deux volets principaux demandés par l'utilisateur :
1. **Mise à niveau documentaire complète** sur l'état du projet et la branche courante via la lecture de tous les fichiers `.md` (hors `reset_data.md`).
2. **Refonte frontend de la responsivité** : refonte de la barre de navigation et résolution de l'ensemble des éléments qui provoquaient des ruptures d'affichage (débordement horizontal, textes tronqués, boutons coupés, etc.) sur les appareils mobiles et tablettes.

---

## 2. Synthèse Documentaire & Changement de Branche

- Détection du basculement sur la branche `feature/panier_client` (basée sur le commit `22e2cad`).
- Prise en compte du nouveau document [`panier_client.md`](./panier_client.md) définissant le cadrage du panier client et des achats de produits des entreprises partenaires.
- Prise en compte de la mise à jour de [`bakamzone_todo_list.md`](./bakamzone_todo_list.md) (Section 7 consacrée au panier).
- Validation de l'orientation d'hébergement confirmée sur VPS KVM 4 Hostinger dans [`plan_strategique_bakamzone .md`](./plan_strategique_bakamzone%20.md).

---

## 3. Détail des Réalisations Techniques

### A. Refonte Responsive de la Navbar ([`src/templates/base.html`](./src/templates/base.html))

1. **Unification en une source de vérité unique** :
   - Suppression des surcharges redondantes et rigides de `{% block navbar %}` présentes dans [`src/templates/home_templates/home_page.html`](./src/templates/home_templates/home_page.html) et [`src/templates/superuser_template/superuser.html`](./src/templates/superuser_template/superuser.html).
   - Le layout maître `base.html` gère désormais la navigation de bout en bout pour l'ensemble des pages du site.

2. **Affichage Desktop (`lg:flex`)** :
   - Logo interactif compact avec badge de marque.
   - Liens directs selon le rôle de l'utilisateur connecté :
     - *Client* : `🛍️ Mon espace`, `⚡ Nouvelle livraison` (bouton émeraude mis en avant).
     - *Livreur* : `🛵 Mon Cockpit Livreur`.
     - *Entreprise* : `📊 Mon entreprise`, `📦 Mon abonnement`.
     - *Admin Bloc* : redirection automatique vers le tableau de bord spécialisé (`Stock`, `Flotte`, `Assistant`, `Responsable`).
     - *Superuser* : `⚡ Cockpit Superuser`.
   - Basculeur de thème sombre / clair 🌙 / ☀️ accessible directement dans la barre supérieure.
   - Bouton de notification Web Push VAPID (`pwa-push-button`) avec icône cloche et label adaptatif.
   - Menu déroulant de profil utilisateur DaisyUI comprenant avatar, initiales, nom complet, téléphone, badge de rôle officiel et bouton de déconnexion.

3. **Affichage Mobile / PWA (`lg:hidden`)** :
   - **En-tête sans débordement** : Logo, bouton de bascule de thème et bouton Hamburger ☰ (animé en ✕ quand ouvert).
   - **Tiroir de navigation fluide (Alpine.js `mobileMenuOpen`)** :
     - Fiche d'identité utilisateur (avatar, nom, téléphone, rôle).
     - Liens d'action pleine largeur avec zones tactiles confortables (> 44 px).
     - Déclencheur des notifications push PWA optimisé pour écran tactile.
     - Bouton de déconnexion stylisé en pied de tiroir.
     - Mode visiteur : boutons pleine largeur bien espacés (🔑 Connexion via modale, Créer compte client, Inscrire entreprise).

---

### B. Corrections Anti-Casse Responsive & Ergonomie Mobile

1. **Suppression du scroll horizontal parasite** :
   - Ajout de la classe `overflow-x-hidden` sur le `body` et les conteneurs racines dans `base.html`.
2. **Alertes Toasts Django ([`src/templates/base.html`](./src/templates/base.html))** :
   - Recentrage sur mobile (`right-0 sm:right-4 left-0 sm:left-auto mx-auto`) pour éviter que les notifications système ne débordent de l'écran sur petit affichage.
3. **Synchronisation du script Push ([`src/static/js/push-notifications.js`](./src/static/js/push-notifications.js))** :
   - Évolution vers `querySelectorAll` pour prendre en charge simultanément les boutons de déclenchement desktop et mobile (`#pwa-push-button`, `.pwa-push-button`) sans dupliquer les requêtes.
   - Validation syntaxique avec `node --check`.
4. **Formulaire de Connexion Modal ([`src/templates/modal/login_modal.html`](./src/templates/modal/login_modal.html))** :
   - Ajout d'un fallback intelligent sur les inputs `identifiant` et `password` permettant à la modale de fonctionner même si la vue courante ne passe pas explicitement `connexion_form`.
5. **En-têtes d'inscription ([`clients_register.html`](./src/templates/auth_templates/clients_register.html) & [`livreurs_register.html`](./src/templates/auth_templates/livreurs_register.html))** :
   - Remplacement de `flex justify-between` rigide par `flex flex-wrap items-center justify-between gap-3` pour empêcher la collision entre le bouton de retour et le badge de localisation sur les écrans < 360 px.
6. **Page d'accueil ([`src/templates/home_templates/home_page.html`](./src/templates/home_templates/home_page.html))** :
   - Adaptation des boutons d'action de la section héro en `w-full sm:w-auto` pour un empilement vertical propre sur mobile.
   - Protection de la grille des arguments de réassurance (`gap-3 sm:gap-4`) et de l'en-tête de découverte des blocs (`flex-wrap gap-3`).
7. **Normalisation des scripts dans `base.html`** :
   - Rapatriement des scripts JavaScript (initialisation GSAP, Lenis, ScrollTrigger) à l'intérieur de la balise `<body>` avant sa fermeture.

---

## 4. Fichiers Modifiés & Créés

| Fichier | Nature de la modification |
|---|---|
| [`src/templates/base.html`](./src/templates/base.html) | Navbar responsive unifiée, tiroir mobile Alpine.js, anti-débordement |
| [`src/templates/home_templates/home_page.html`](./src/templates/home_templates/home_page.html) | Suppression de la navbar dupliquée, CTAs héro et grille responsive |
| [`src/templates/superuser_template/superuser.html`](./src/templates/superuser_template/superuser.html) | Suppression de la navbar dupliquée au profit de `base.html` |
| [`src/templates/modal/login_modal.html`](./src/templates/modal/login_modal.html) | Fallback résilient des champs de saisie pour modale globale |
| [`src/templates/auth_templates/clients_register.html`](./src/templates/auth_templates/clients_register.html) | `flex-wrap gap-3` sur l'en-tête de retour |
| [`src/templates/auth_templates/livreurs_register.html`](./src/templates/auth_templates/livreurs_register.html) | `flex-wrap gap-3` sur l'en-tête de retour |
| [`src/static/js/push-notifications.js`](./src/static/js/push-notifications.js) | Multi-triggers desktop/mobile pour les souscriptions Push |
| [`intervention_agy.md`](./intervention_agy.md) | Rapport d'intervention horodaté (présent document) |

---

## 5. Validation & Tests Automatisés

- **Contrôle système Django** :
  ```powershell
  python manage.py check
  # Résultat : System check identified no issues (0 silenced).
  ```
- **Contrôle migrations** :
  ```powershell
  python manage.py makemigrations --check --dry-run
  # Résultat : No changes detected
  ```
- **Syntaxe JavaScript** :
  ```powershell
  node --check static/js/push-notifications.js
  # Résultat : 0 erreur
  ```
- **Suite de tests automatisés (78 tests réussis — 100% OK)** :
  - `home_app.tests`, `auth_app.tests`, `clients_app.tests`, `notifications_app.tests` : 48 tests passés.
  - `livreurs_app.tests`, `demande_livraison_app.tests` : 30 tests passés.

---

## 6. Résolution de l'incident de désynchronisation de la base locale (`db.sqlite3`)

- **Symptôme** : `django.db.utils.OperationalError: no such column: demande_livraison_app_demandelivraison.statut_destinataire` lors de l'appel à `demandes_livraison.count()` dans `SuperviseurFlotteDashbordView` (ligne 344 de `admins_app/views.py`).
- **Cause** : La colonne avait été renommée en `statut_position_destinataire` dans `db.sqlite3` suite à une migration exécutée sur la branche `features/web_socket_livreur_deplacement`. Après bascule sur `feature/panier_client`, le code attendait toujours `statut_destinataire`.
- **Action corrective** :
  1. Sauvegarde préventive de la base : `src/db.sqlite3.bak`.
  2. Renommage de la colonne SQLite vers son nom d'origine : `statut_destinataire`.
  3. Nettoyage des entrées orphelines de la table `django_migrations`.
  4. Vérification d'exécution réussie de la requête : `demandes_livraison_count: 2`.

---

## 7. Intervention du 18 novembre 2026 à 10:40:00 UTC — Cockpit Superuser : Liste dynamique HTMX des Entreprises & Alertes Retraits

**Branche Git :** `features/entreprise_list_et_details_views_par_superuser`  
**Objectifs de la session :**
1. Mise à niveau documentaire complète par la lecture exhaustive des 14 fichiers `.md` du projet (hors `reset_data.md`).
2. Extension de [`bakamzone_todo_list.md`](./bakamzone_todo_list.md) avec une nouvelle section 9 dédiée au cockpit Superuser pour la gestion des entreprises, la vue détaillée et le traitement des retraits d'argent (acceptation / refus avec commentaire).
3. Création du mixin de sécurité personnalisé [`SuperuserRequiredMixin`](./src/superuser_app/views.py).
4. Implémentation de la CBV [`ListeEntrepriseViewBySuperUser`](./src/superuser_app/views.py) avec détection et filtrage dynamique par requêtes HTMX.
5. Intégration frontend responsive via DaisyUI / Tailwind et partials HTMX.
6. Branchement de la route dans [`src/superuser_app/urls.py`](./src/superuser_app/urls.py) et ajout d'un accès direct dans le cockpit central [`src/templates/superuser_template/superuser.html`](./src/templates/superuser_template/superuser.html).

### Réalisations techniques détaillées :

1. **Contrôle d'accès personnalisé (`SuperuserRequiredMixin`)** :
   - Hérite de `LoginRequiredMixin` et `UserPassesTestMixin`.
   - Contrôle combiné : `is_authenticated`, `is_active` et `is_superuser`.
   - Gestion personnalisée de l'interdiction (`handle_no_permission`) : notification toast Django `messages.error` et redirection vers `home_app:home`.

2. **CBV Liste Entreprises (`ListeEntrepriseViewBySuperUser`)** :
   - Optimisation ORM haute performance sans produit cartésien : utilisation de `Subquery` et `Coalesce` pour agréger :
     - `nb_articles_disponibles` : nombre d'articles actifs de l'entreprise.
     - `nb_admins` : nombre d'administrateurs rattachés.
     - `nb_retraits_attente` : nombre de demandes de retrait avec statut `en_attente`.
     - `montant_retraits_attente` : montant cumulé en FCFA des retraits en attente.
   - Filtres dynamiques : recherche plein-texte `q` (nom, RC, gérant, téléphone), palier (`standard`, `pro`, `premium`), présence de retraits en attente (`retrait=en_attente`), et statut d'abonnement.
   - Détection HTMX dans `get_template_names()` : renvoie le fragment `partials/superuser/entreprise_list_results.html` si `HX-Request == "true"`, ou le gabarit complet `superuser_template/entreprise_list.html` sinon.

3. **Composants Templates & Dynamisme HTMX** :
   - [`src/templates/superuser_template/entreprise_list.html`](./src/templates/superuser_template/entreprise_list.html) : En-tête avec statistiques globales (total entreprises, nombre et montant total des retraits en attente), formulaire HTMX avec déclencheur réactif `hx-trigger="keyup changed delay:300ms from:#search-input, change from:select, submit"`, spinner de recherche et mise à jour ciblée `hx-target="#entreprises-table-container"`.
   - [`src/templates/partials/superuser/entreprise_list_results.html`](./src/templates/partials/superuser/entreprise_list_results.html) : Tableau complet pour affichage desktop et cartes tactiles pour affichage mobile, badges de quotas, alerte visuelle pulsée pour les retraits en attente et pagination dynamique HTMX préservant les paramètres de filtrage.

4. **Résolution du conflit de branches de migrations** :
   - Détection de têtes de migrations concurrentes dans `demande_livraison_app` (`0003_rename...` et `0004_...`).
   - Génération et application de la migration de fusion `src/demande_livraison_app/migrations/0005_merge_20261118_1033.py`.

5. **CBV Fiche Détail Entreprise (`EntrepriseDetailViewBySuperUser`)** :
   - Fiche complète dans [`src/superuser_app/views.py`](./src/superuser_app/views.py) et template [`src/templates/superuser_template/entreprise_detail.html`](./src/templates/superuser_template/entreprise_detail.html).
   - Intégration du bilan comptable via `obtenir_solde_entreprise` (chiffre d'affaires total payé, ventes du mois, retraits engagés, et solde disponible déblocable).
   - Découpage du catalogue d'articles (en bloc / hors bloc, disponibilité et prix promo) et inventaire des administrateurs rattachés.
   - Section prioritaire des demandes de retraits de fonds (`RetraitEntreprise`) avec détection des demandes `en_attente` d'arbitrage.
   - Branchement de la route `path('entreprises/<int:pk>/', EntrepriseDetailViewBySuperUser.as_view(), name='detail-entreprise')` dans [`src/superuser_app/urls.py`](./src/superuser_app/urls.py) et mise à jour des liens d'actions dans la liste des entreprises.

6. **Actions de Décision sur les Demandes de Retrait (`TraiterDemandeRetraitView`)** :
   - Évolution du modèle `RetraitEntreprise` avec le champ `commentaire = models.TextField(blank=True, default="")` et application de la migration `0003_retraitentreprise_commentaire`.
   - CBV `TraiterDemandeRetraitView` dans [`src/superuser_app/views.py`](./src/superuser_app/views.py) et route `path('retraits/<int:pk>/traiter/', TraiterDemandeRetraitView.as_view(), name='traiter-retrait')`.
   - Gestion transactionnelle sécurisée (`transaction.atomic()` et `select_for_update()`) :
     - Action `approuver` : statut `approuve`, horodatage et note facultative.
     - Action `payer` : statut `paye`, confirmation finale du versement effectif.
     - Action `rejeter` : statut `rejete`, exigence stricte d'un motif / commentaire obligatoire, entraînant le déblocage immédiat des fonds dans le solde disponible de l'entreprise.
   - Intégration de modales DaisyUI interactives dans [`src/templates/superuser_template/entreprise_detail.html`](./src/templates/superuser_template/entreprise_detail.html) pour valider ou refuser avec saisie de commentaire.

7. **Validation et couverture par tests unitaires** :
   - 16 tests unitaires validés dans [`src/superuser_app/tests.py`](./src/superuser_app/tests.py) :
     - Sécurité : refus des utilisateurs anonymes et clients, validation des droits superuser sur liste, détail et traitement de retraits.
     - Précision ORM : vérification des compteurs annotés d'articles et des montants de retraits en attente.
     - Filtrage : tests de la recherche textuelle et du filtre des demandes de retrait.
     - HTMX : validation de la bascule de template entre fragment et page complète.
     - Fiche Détail : validation du contexte financier (`solde_data`), du découpage des articles et du suivi des retraits.
     - Décision de Retrait : tests complets d'approbation, de mise en paiement, de refus avec motif, et de blocage si le motif de refus est omis.
   - Exécution : `Ran 16 tests in 59.210s — OK (100% succès)`.

---

## 8. Intervention du 25 novembre 2026 à 11:29:14 UTC — Relais `feature/PaiementLivraisonLigdiCash` : Stabilisation Paiement Livraison, Smart-Drop & Garde-fou Livreur

**Branche Git :** `feature/PaiementLivraisonLigdiCash`  
**Objectifs de la session :**
1. Lecture complète de l'ensemble des 20 fichiers `.md` du projet (hors `reset_data.md` et licences des environnements virtuels) afin de reprendre le travail initié par Gemini sur `paiement_app` (paiement des commandes et paiement des livraisons sans redirection).
2. Ajout du champ `reference` (`UUIDField`) sur `DemandeLivraison` avec migration sécurisée en 3 étapes.
3. Audit et correction des anomalies bloquantes dans la brique paiement livraison (`services_livraison.py`, `views_paiement_livraison.py`, `urls.py` et templates).
4. Branchement du lien de paiement dans la notification Web Push post-`Smart-Drop` et verrouillage du décollage côté livreur tant que le paiement requis n'est pas confirmé.
5. Couverture et validation par tests unitaires et d'intégration.

### Réalisations techniques détaillées :

1. **Modèle `DemandeLivraison` & Migration ([`src/demande_livraison_app/models.py`](./src/demande_livraison_app/models.py))** :
   - Ajout du champ `reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)` et des propriétés `est_payee` et `paiement_requis` (distinguant les courses soumises au paiement dédié des courses créées par les entreprises sur commande déjà payée).
   - Création et application de [`0007_demandelivraison_reference.py`](./src/demande_livraison_app/migrations/0007_demandelivraison_reference.py) (ajout nullable, peuplement d'UUID uniques via `RunPython`, puis contrainte `unique=True` non nulle).

2. **Stabilisation Services & SDK LigdiCash ([`src/paiement_app/services_livraison.py`](./src/paiement_app/services_livraison.py))** :
   - Alignement de `initier_paiement_ligdicash_livraison()` sur la signature réelle du SDK `ligdicash.Invoice` : ajout de ligne via `invoice.add_item(...)`, `invoice.external_id = ""`, appel `invoice.pay_without_redirection(otp=otp, customer=paiement.numero_client, ...)`.
   - Correction des retours d'erreur (`code != "00"` retournait `None` auparavant) et synchronisation de `DemandeLivraison.statut_paiement` (`PAIEMENT_EN_ATTENTE`, `PAIEMENT_ECHOUE`, `PAIEMENT_REUSSI`, `PAIEMENT_NON_INITIE`).
   - Correction dans `confirmer_paiement_ligdicash_livraison()` : valeur par défaut `token_callback=""`, sortie anticipée si `token_creation` vide ou paiement déjà confirmé, et réindentation du bloc `completed`/`failed`/`cancelled` pour empêcher de marquer une demande payée hors confirmation.

3. **Vues, Routage & Templates ([`src/paiement_app/views_paiement_livraison.py`](./src/paiement_app/views_paiement_livraison.py), [`src/paiement_app/urls.py`](./src/paiement_app/urls.py))** :
   - Renommage `InitierPaiementLIvraisonView` $\rightarrow$ `InitierPaiementLivraisonView`.
   - Ajout de `@transaction.atomic` sur `post()`, vérification stricte de `position_destinataire_validee`, blocage sur course annulée ou montant invalide, normalisation du numéro client.
   - Correction de `clien__user` $\rightarrow$ `client__user` dans `StatutPaiementLivraisonView.get()` et `status=20` $\rightarrow$ `status=200` (et `404` si introuvable) dans `LigdiCashLivraisonCallbackView.post()`.
   - Mise à jour de [`initier_paiement_livraison.html`](./src/templates/paiement_templates/initier_paiement_livraison.html) (opérateurs `ORANGE`, `MOOV`, `CORIS`, `LIGDICASH`, formatage numéro et OTP Alpine.js) et [`status_paiement_livraison.html`](./src/templates/paiement_templates/status_paiement_livraison.html) (lien `clients_app:suivi-livraison`).

4. **Branchement Smart-Drop & Garde-fou Livreur** :
   - [`src/notifications_app/services.py`](./src/notifications_app/services.py) : `programmer_notification_position_destinataire()` envoie la Web Push avec l'URL `paiement_app:initier_livraison` lorsque `demande.paiement_requis and not demande.est_payee`.
   - [`src/templates/clients_templates/client_dashboard.html`](./src/templates/clients_templates/client_dashboard.html) : ajout du bouton d'accès au paiement sur les livraisons actives en attente de règlement.
   - [`src/livreurs_app/views.py`](./src/livreurs_app/views.py) & [`src/templates/livreurs_templates/livreur_dashboard.html`](./src/templates/livreurs_templates/livreur_dashboard.html) : `ChangerStatutCourseView` bloque le passage à `en_cours` (et le contournement direct vers `livree`) tant que `demande.paiement_requis and not demande.est_payee`, avec indication visuelle et bouton désactivé côté dashboard livreur.

5. **Validation & Tests Automatisés** :
   - Ajout des tests dans [`src/paiement_app/tests.py`](./src/paiement_app/tests.py) (10 tests), [`src/livreurs_app/tests.py`](./src/livreurs_app/tests.py) (`LivreurTakeoffPaymentGuardTests`, 3 tests) et mise à jour de [`src/demande_livraison_app/tests.py`](./src/demande_livraison_app/tests.py) (`DestinataireGeoViewTestCase`).
   - Exécution ciblée (`paiement_app.tests`, `DestinataireGeoViewTestCase`, `LivreurTakeoffPaymentGuardTests`, `notifications_app.tests`, `AssistantOperationnelDashboardTests`, avec SDK `ligdicash` et dispatch Celery mockés) : **44 tests réussis — OK (100 %)**.
   - Contrôles Django : `manage.py check` (0 erreur) et `manage.py makemigrations --check --dry-run --noinput` (`No changes detected`).



