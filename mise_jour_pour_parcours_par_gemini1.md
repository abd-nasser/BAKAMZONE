## [2026-11-23 10:40 GMT] — Implémentation du module de paiement LigdiCash (`paiement_app`)

### Contexte & Objectif
Mise en place complète du flux d'encaissement Mobile Money **LigdiCash (Payin sans redirection)** dans `paiement_app` sur une branche dédiée, avec expérience utilisateur fluide sans rechargement complet de page (HTMX + Alpine.js + DaisyUI) et garantie d'atomicité sur la validation des commandes et la décrémentation des stocks.

### Ce qui a été conçu et implémenté
1. **Modèle de données (`paiement_app/models.py`)** :
   - Création de `PaiementLigdiCash` lié en `OneToOneField` (`PROTECT`) à `panier_app.Commande`.
   - Séparation explicite de `token_creation` (utilisé pour l'API `confirm`) et `token_callback` (reçu via webhook), accompagnée d'un champ `reponse_API` (`JSONField`) pour l'audit.
   - Ajout d'index SQL (`models.Index`) sur `token_creation` et `statut`.

2. **Service métier & SDK (`paiement_app/services.py`)** :
   - Intégration du package officiel `ligdicash` (`pip install ligdicash`) configuré via `settings`.
   - `initier_paiement_ligdicash()` : appel sans redirection (`external_id=""`, `custom_data` embarquant les références UUID de commande et de paiement).
   - `confirmer_paiement_ligdicash()` : vérification serveur-à-serveur via `token_creation` protégée par `@transaction.atomic` et `select_for_update()`.
   - **Gestion atomique des stocks** : lors du passage idempotent à `PAIEMENT_REUSSI`, décrémentation SQL sécurisée (`Greatest(F("quantite_disponible") - ligne.quantite, 0)`) pour les articles hors bloc.

3. **Vues & Routage (`paiement_app/views.py`, `paiement_app/urls.py`)** :
   - `InitierPaiementView` : soumission HTMX retournant le partial toast `paiement_result.html` avec l'en-tête `HX-Trigger: close_and_reload` en cas de succès.
   - `LigdiCashCallbackView` (`@csrf_exempt`) : résolution résiliente du paiement (`custom_data` puis tokens) et confirmation systématique côté serveur.
   - `StatutPaiementView` : support du polling HTMX HTML (`hx-select="#statut-paiement-card"`) avec vérification active non bloquante et maintien d'une sortie `?format=json`.

4. **Templates & UX (`paiement_templates/` & `partials/result/`)** :
   - `initier_paiement.html` : formulaire mobile-first aux couleurs BAKAMZONE (`#059669` / `#F97316`), formatage automatique du numéro (`226...`) et gestion dynamique du champ OTP via Alpine.js.
   - `paiement_result.html` : notification toast injectée dans `#toast-container` de `base.html`.
   - `statut_paiement.html` : suivi temps réel toutes les 4 secondes (`hx-trigger="every 4s"`) tant que la transaction est `en_attente`.

### État actuel & Prochaines étapes pour les agents
- **État actuel** : L'architecture complète de `paiement_app` (modèle, services, vues, URLs et 3 templates) est définie et prête à être vérifiée par migrations (`makemigrations` / `migrate`) et tests d'intégration.
- **À vérifier / compléter ensuite** :
  1. Ajouter les variables d'environnement `LIGDICASH_API_KEY`, `LIGDICASH_AUTH_TOKEN`, `LIGDICASH_PLATFORM` et `LIGDICASH_CALLBACK_URL` dans `.env` et `settings.py`.
  2. Brancher le bouton de redirection vers `paiement_app:initier` depuis la validation du panier (`panier_app`).
  3. Vérifier si une décrémentation complémentaire sur `StockBloc` est requise lors de la confirmation de paiement pour les articles marqués `en_bloc=True`.
  4. Écrire les tests unitaires sur `confirmer_paiement_ligdicash` (idempotence des callbacks multiples et non-régression sur les stocks).