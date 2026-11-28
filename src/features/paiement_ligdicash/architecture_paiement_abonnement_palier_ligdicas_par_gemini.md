# Architecture — Paiement des Abonnements de Palier Entreprise (LigdiCash)

**Branche Git :** `feature/paiement_abonnement_palier_ligdicash`  
**Projet :** BAKAMZONE  
**Objectif :** Remplacer la sélection passive de palier (`ChoixPalierEntrepriseView`) par un parcours complet de souscription/renouvellement avec paiement mobile money sans redirection via **LigdiCash**, validation idempotente et synchronisation fiable des quotas de l'entreprise.

---

## 1. Grille Tarifaire Provisoire (FCFA)

> **Note :** Tarifs provisoires à ajuster lors de la validation finale avec l'associé.  
> **Règle de sécurité :** Le montant facturé est **toujours** résolu côté serveur à partir du palier choisi (jamais depuis le payload client).

| Palier | Tarif Standard | Tarif Promotionnel (Actif) | Quota Articles | Quota Admins |
| :--- | :---: | :---: | :---: | :---: |
| `standard` | 10 000 FCFA | **7 750 FCFA** | `Entreprise.QUOTAS_ARTICLES["standard"]` | `Entreprise.QUOTAS_ADMINS["standard"]` |
| `pro` | 25 000 FCFA | **17 750 FCFA** | `Entreprise.QUOTAS_ARTICLES["pro"]` | `Entreprise.QUOTAS_ADMINS["pro"]` |
| `premium` | 35 000 FCFA | **27 750 FCFA** | `Entreprise.QUOTAS_ARTICLES["premium"]` | `Entreprise.QUOTAS_ADMINS["premium"]` |

Centraliser ces tarifs dans un dictionnaire de configuration métier (ex. `TARIFS_PALIERS_ENTREPRISE` dans `entreprise_app/models.py` ou `paiement_app/services_abonnement.py`) afin de pouvoir basculer facilement entre tarif promotionnel et tarif standard sans toucher aux vues.

---

## 2. Architecture des Données

### A. Modèle `PaiementAbonnementLigdiCash` (dans `paiement_app/models.py`)

Modèle transactionnel isolé des paiements de commandes et des paiements de livraisons :

- `reference` : `UUIDField(default=uuid.uuid4, unique=True, editable=False)` (identifiant public d'URL).
- `entreprise` : `ForeignKey("entreprise_app.Entreprise", on_delete=models.CASCADE, related_name="paiements_abonnement")`.
- `palier_cible` : `CharField(max_length=20, choices=...)` (`standard`, `pro`, `premium`) — fige le palier acheté au moment de la transaction.
- `montant` : `DecimalField(max_digits=12, decimal_places=2)` — fige le montant réel débité (ex. `7750.00`).
- `duree_jours` : `PositiveIntegerField(default=30)` — durée d'activation accordée par le paiement.
- `operateur` : `CharField(max_length=20)` (`ORANGE`, `MOOV`, `CORIS`, `LIGDICASH`).
- `numero_client` : `CharField(max_length=20)`.
- `token_creation` : `CharField(max_length=255, blank=True, db_index=True)`.
- `token_callback` : `CharField(max_length=255, blank=True)`.
- `statut` : `CharField(max_length=20, default="en_attente")` :
  - `en_attente`
  - `reussi`
  - `echoue`
  - `annule`
- `reponse_api` : `JSONField(default=dict, blank=True)`.
- `date_creation` : `DateTimeField(auto_now_add=True)`.
- `date_paiement` : `DateTimeField(null=True, blank=True)`.

### B. Cohérence avec `Entreprise` (`entreprise_app/models.py`)

- Ne **plus** modifier `entreprise.palier` directement dans `ChoixPalierEntrepriseForm.save()` avant la confirmation du paiement (évite les sélections « mortes » ou le déclassement/surclassement non payé).
- Lors de l'activation confirmée :
  - `entreprise.palier = paiement.palier_cible`
  - Activation du statut d'abonnement actif sur `Entreprise` et calcul/prolongation de la date d'expiration (`timezone.now() + timedelta(days=paiement.duree_jours)` ou ajout à l'échéance restante en cas de renouvellement anticipé sur le même palier).
  - Les propriétés `quota_articles` et `quota_admins` de `Entreprise` reflètent immédiatement le palier validé (et retournent `0` tant que l'abonnement n'est pas actif/valide).

---

## 3. Flux Bout-en-Bout

```text
[Responsable Entreprise]
        │
        ▼ (1) ChoixPalierEntrepriseView (POST : choix palier)
[Redirection vers initiation paiement]
        │
        ▼ (2) InitierPaiementAbonnementView (GET/POST : opérateur, téléphone, OTP)
[services_abonnement.py -> ligdicash.Invoice.pay_without_redirection]
        │
        ├──► Échec API : statut = "echoue", entreprise inchangée
        │
        └──► Succès API (code == "00") : token_creation enregistré, statut = "en_attente"
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
(3a) Webhook LigdiCash     (3b) Polling StatutPaiementAbonnementView
LigdiCashAbonnementCallbackView
        │                       │
        └───────────┬───────────┘
                    ▼
[confirmer_paiement_ligdicash_abonnement()] (transaction.atomic + select_for_update)
        │
        ├──► Vérification via ligdicash.get_transaction(token)
        ├──► Idempotence : si déjà "reussi", sortie immédiate sans double prolongation
        └──► Si "completed" :
               1. paiement.statut = "reussi", paiement.date_paiement = now()
               2. Mise à jour atomique de Entreprise (palier + statut actif + expiration)
               3. Déblocage immédiat des quotas (articles & admins)
```

---

## 4. Composants Techniques à Implémenter

### 1. Configuration (`settings.py` & `.env`)
- Ajouter `LIGDICASH_CALLBACK_URL_ABONNEMENT` distinct de `LIGDICASH_CALLBACK_URL` (commandes) et `LIGDICASH_CALLBACK_URL_LIVRAISON` (courses) pour isoler les webhooks.

### 2. Service Métier (`paiement_app/services_abonnement.py`)
- `obtenir_tarif_palier(palier: str, promo: bool = True) -> Decimal` : résout le prix serveur et lève une `ValueError` si le palier est invalide (`pas_defini` ou inconnu).
- `initier_paiement_ligdicash_abonnement(paiement, otp: str) -> dict` :
  - Construit `ligdicash.Invoice` avec `add_item(...)`, `external_id = ""`, `callback_url = settings.LIGDICASH_CALLBACK_URL_ABONNEMENT`.
  - Appelle `invoice.pay_without_redirection(otp=otp, customer=paiement.numero_client, ...)`.
  - Enregistre `token_creation` et `reponse_api`.
- `confirmer_paiement_ligdicash_abonnement(paiement_id: int, token_callback: str = "") -> PaiementAbonnementLigdiCash` :
  - Exécuté sous `@transaction.atomic` avec `select_for_update()` sur `PaiementAbonnementLigdiCash` **et** `Entreprise`.
  - Vérifie l'état auprès de `ligdicash.get_transaction(token)`.
  - Si `status == "completed"` et `paiement.statut != "reussi"` : passe à `reussi` et applique l'activation du palier sur `Entreprise`.

### 3. Vues & Routes (`paiement_app/views_paiement_abonnement.py` & `paiement_app/urls.py`)
- `InitierPaiementAbonnementView` (`abonnement/<uuid:reference>/initier/`) :
  - Vérifie que `request.user` est le `user_principal` (`role == "entreprise"`) de l'entreprise concernée.
  - Empêche de ré-initier un paiement déjà `reussi`.
- `StatutPaiementAbonnementView` (`abonnement/<uuid:reference>/statut/`) :
  - Affiche l'état en temps réel (`en_attente`, `reussi`, `echoue`) et déclenche la vérification idempotente si encore `en_attente`.
- `LigdiCashAbonnementCallbackView` (`webhook/ligdicash/abonnement/`, `@csrf_exempt`) :
  - Retourne `200 OK` après traitement idempotent (ou `404` si le `token` ne correspond à aucun `PaiementAbonnementLigdiCash`).

### 4. Refactoring `ChoixPalierEntrepriseView` (`entreprise_app/views.py`)
- Lors de la soumission d'un palier (`standard`, `pro`, `premium`) :
  - Crée (ou réutilise une transaction `en_attente` non expirée pour le même palier) une instance `PaiementAbonnementLigdiCash` avec le tarif serveur.
  - Redirige immédiatement vers `paiement_app:initier_abonnement` avec `paiement.reference`.

---

## 5. Règles de Sécurité & Plan de Tests

1. **Isolation des accès** : Seul le `user_principal` de l'entreprise propriétaire peut initier ou consulter le paiement d'abonnement (les admins délégués `entreprise_admin` et autres entreprises reçoivent une `403`/`404`).
2. **Idempotence stricte** : Appeler deux fois le webhook ou rafraîchir la page de statut sur un paiement déjà confirmé ne doit ni doubler la durée d'abonnement ni réinitialiser les dates.
3. **Intégrité des quotas** : Tant que `PaiementAbonnementLigdiCash.statut != "reussi"`, l'entreprise ne bénéficie pas des quotas (`quota_articles`, `quota_admins`) du nouveau palier.
4. **Tests unitaires & d'intégration (`paiement_app/tests.py` & `entreprise_app/tests.py`)** :
   - Résolution des tarifs promotionnels (`7750`, `17750`, `27750`) et refus des paliers invalides.
   - Initiation LigdiCash mockée (succès `code="00"` vs échec API).
   - Confirmation via callback et via vue statut + test d'idempotence (double appel webhook).
   - Vérification du déblocage de `can_add_admin` et `can_add_article` uniquement après paiement réussi.