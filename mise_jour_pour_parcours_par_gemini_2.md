## [2026-11-25 10:55 GMT] — Implémentation du paiement de livraison LigdiCash (`feature/PaiementLivraisonLigdiCash`)

### Contexte & Objectif
Mise en place du système d'encaissement Mobile Money **LigdiCash (Payin sans redirection)** pour le second service majeur de BAKAMZONE (**`DemandeLivraison`**) sur la branche dédiée `feature/PaiementLivraisonLigdiCash`, afin de garantir le règlement de la course après partage de position GPS (`Smart-Drop`) et avant le décollage du livreur.

### Travaux réalisés
1. **Architecture & Cadrage (`feature/workflow_complet.md` & `feature/workflow_complet_paiement_livraison.md`)** :
   * Formalisation complète de la chaîne métier (`Smart-Drop` $\rightarrow$ Notification Push Celery $\rightarrow$ Initiation LigdiCash $\rightarrow$ Callback dédié $\rightarrow$ Autorisation de décollage livreur) et génération de la Mind Map Mermaid.
2. **Modèle de données (`paiement_app/models.py`)** :
   * Création de `PaiementLivraisonLigdiCash` relié en `OneToOneField` (`on_delete=models.PROTECT`, `related_name="paiement_livraison_ligdicash"`) à `demande_livraison_app.DemandeLivraison`.
   * Séparation de `token_creation` et `token_callback`, journalisation `reponse_API` (`JSONField`) et index SQL sur `token_creation` et `statut`.
3. **Services métier (`paiement_app/services_livraison.py`)** :
   * `initier_paiement_livraison_ligdicash()` : appel SDK `ligdicash` sans redirection (`external_id=""`) pointant vers `settings.LIGDICASH_CALLBACK_URL_LIVRAISON`.
   * `confirmer_paiement_livraison_ligdicash()` : vérification serveur-à-serveur via `ligdicash.get_transaction(token=paiement.token_creation)` protégée par `@transaction.atomic`, `select_for_update()` et idempotence stricte.
4. **Vues, Webhook dédié & Routage (`paiement_app/views_livraison.py`, `paiement_app/urls.py`)** :
   * `InitierPaiementLivraisonView` (`livraison/<uuid:reference>/initier/`) : initiation HTMX avec toast `#toast-container` et déclencheur `close_and_reload`.
   * `StatutPaiementLivraisonView` (`livraison/<uuid:reference>/statut/`) : polling HTMX toutes les 4s (`hx-select="#statut-livraison-card"`) avec vérification active non bloquante et support `?format=json`.
   * `LigdiCashLivraisonCallbackView` (`callback/livraison/`, `@csrf_exempt`) : webhook isolé du flux commandes pour traiter exclusivement les callbacks de livraison.
5. **Templates UI (`paiement_templates/`)** :
   * Création de `initier_paiement_livraison.html` et `statut_paiement_livraison.html` respectant la charte BAKAMZONE (`#059669` / `#F97316`, DaisyUI clair/sombre, HTMX + Alpine.js).

### État actuel & Relais pour les agents
* **État actuel** : Toute la brique paiement livraison dans `paiement_app` (modèle, services, vues, callback dédié, URLs et templates) est conçue et documentée.
* **Prochaines actions à exécuter par les agents** :
  1. Appliquer les migrations Django (`python manage.py makemigrations && python manage.py migrate`) et vérifier que `LIGDICASH_CALLBACK_URL_LIVRAISON` pointe bien vers `/paiement/callback/livraison/`.
  2. **Branchement `pywebpush` + Celery** : lors de la validation de position GPS par le destinataire (`Smart-Drop`), envoyer la notification Web Push au client avec le lien `reverse("paiement_app:initier_livraison", kwargs={"reference": demande.reference})`.
  3. **Verrouillage départ livreur** : empêcher le passage au statut de prise en charge / décollage côté livreur tant que `paiement_livraison_ligdicash.statut != "reussi"`.
  4. Écrire les tests unitaires sur `confirmer_paiement_livraison_ligdicash` et `LigdiCashLivraisonCallbackView`.