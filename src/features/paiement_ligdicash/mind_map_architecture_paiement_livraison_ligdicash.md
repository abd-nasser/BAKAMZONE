# Architecture & Mind Map : Paiement Livraison LigdiCash — BAKAMZONE

* **Branche Git** : `feature/PaiementLivraisonLigdiCash`
* **Application principale** : `paiement_app` (couplée à `demande_livraison_app`, `livreurs_app` et Celery/WebPush)
* **Date** : 25 novembre 2026 — 10:55 GMT

---

## 1. Mind Map Complète du Flux (Smart-Drop $\rightarrow$ Push Celery $\rightarrow$ LigdiCash $\rightarrow$ Décollage Livreur)

```mermaid
flowchart TD
    subgraph SmartDrop ["1. Déclenchement Smart-Drop & Notification (Relais Agents)"]
        A["Client crée une DemandeLivraison"] --> B["Destinataire ouvre le lien Smart-Drop"]
        B --> C["Destinataire valide et partage sa position GPS"]
        C --> D["Tâche Celery déclenchée (pywebpush)<br/>Envoi notification Push au client"]
        D --> E["Payload Push : URL directe<br/>/paiement/livraison/<uuid:reference>/initier/"]
    end

    subgraph Initiation ["2. Initiation Paiement Sans Redirection (HTMX / Alpine.js)"]
        E --> F{"Session client active ?"}
        F -->|Non| F1["Connexion Django puis redirection ?next="] --> G
        F -->|Oui| G["GET InitierPaiementLivraisonView<br/>(initier_paiement_livraison.html)"]
        G --> H["Saisie Opérateur + Téléphone (226...) + OTP optionnel"]
        H -->|POST HTMX| I["POST InitierPaiementLivraisonView<br/>(transaction.atomic + select_for_update)"]
        I --> J["Service : initier_paiement_livraison_ligdicash()"]
        J -->|SDK ligdicash| K["API LigdiCash : pay_without_redirection<br/>callback_url = LIGDICASH_CALLBACK_URL_LIVRAISON<br/>external_id = ''"]
        K --> L{"Code réponse == '00' ?"}
        L -->|Oui| M["Stockage token_creation & reponse_API<br/>Statut = en_attente<br/>Toast + HX-Trigger: close_and_reload"]
        L -->|Non| N["Statut = echoue + message_erreur<br/>Toast erreur sans fermeture"]
    end

    subgraph Confirmation ["3. Suivi Temps Réel & Webhook Dédié"]
        M -->|Redirection JS 1.2s| O["GET StatutPaiementLivraisonView<br/>(statut_paiement_livraison.html)"]
        O -->|Polling HTMX toutes les 4s| P["hx-select='#statut-livraison-card'<br/>Vérification active si en_attente"]
        Q["Serveur LigdiCash"] -->|POST Webhook| R["POST LigdiCashLivraisonCallbackView<br/>(/paiement/callback/livraison/ - @csrf_exempt)"]
        R --> S["_retrouver_paiement_livraison()<br/>(paiement_livraison_ref -> demande_reference -> token)"]
        P --> T["Service : confirmer_paiement_livraison_ligdicash()"]
        S --> T
        T -->|SDK ligdicash| U["API LigdiCash : get_transaction(token_creation)"]
        U --> V{"Statut réel API ?"}
        V -->|completed / success / paid| W["Idempotence + atomicité :<br/>Paiement.statut = reussi<br/>DemandeLivraison marquée payée"]
        V -->|failed / error| X["Paiement.statut = echoue"]
        V -->|cancelled / aborted| Y["Paiement.statut = annule"]
    end

    subgraph Flotte ["4. Règle Opérationnelle Flotte BAKAMZONE"]
        W --> Z["Décollage du livreur autorisé<br/>(Prise en charge & livraison du colis)"]
        X & Y --> Z1["Course maintenue bloquée au départ<br/>(Aucun décollage sans paiement validé)"]
    end
```

---

## 2. Cartographie des Fichiers & Responsabilités

| Fichier | Rôle & Responsabilité |
| :--- | :--- |
| `paiement_app/models.py` | Modèle **`PaiementLivraisonLigdiCash`** (`OneToOneField` avec `on_delete=models.PROTECT` et `related_name="paiement_livraison_ligdicash"`, `reference` UUID, `token_creation`, `token_callback`, `reponse_API`, index SQL). |
| `paiement_app/services_livraison.py` | Logique métier pure et appels SDK `ligdicash` : `initier_paiement_livraison_ligdicash()` (utilisant `LIGDICASH_CALLBACK_URL_LIVRAISON`) et `confirmer_paiement_livraison_ligdicash()` (verrouillage pessimiste + idempotence). |
| `paiement_app/views_livraison.py` | Contrôleurs dédiés au flux livraison : `InitierPaiementLivraisonView`, `StatutPaiementLivraisonView` et webhook isolé `LigdiCashLivraisonCallbackView` (`@csrf_exempt`). |
| `paiement_app/urls.py` | Routes dédiées : `livraison/<uuid:reference>/initier/`, `livraison/<uuid:reference>/statut/`, et `callback/livraison/`. |
| `templates/paiement_templates/initier_paiement_livraison.html` | Formulaire Mobile Money (charte `#059669` / `#F97316`, HTMX + Alpine.js, injection toast `#toast-container` + redirection sur `close_and_reload`). |
| `templates/paiement_templates/statut_paiement_livraison.html` | Page de suivi avec polling HTMX toutes les 4s (`hx-select="#statut-livraison-card"`) tant que `statut == "en_attente"`. |

---

## 3. Mécanique Interne Détaillée

### A. Séparation stricte Commande vs Livraison
* **Modèle dédié** : `PaiementLivraisonLigdiCash` évite tout champ nullable croisé avec `PaiementLigdiCash` (dédié à `panier_app.Commande`).
* **Webhook dédié (`LIGDICASH_CALLBACK_URL_LIVRAISON`)** : `LigdiCashLivraisonCallbackView` écoute exclusivement `/paiement/callback/livraison/`, évitant toute collision d'identifiants ou d'aiguillage avec `/paiement/callback/ligdicash/`.

### B. Garanties Transactionnelles & Idempotence
1. **Verrouillage concurrentiel (`select_for_update`)** : Dans `InitierPaiementLivraisonView.post` et `confirmer_paiement_livraison_ligdicash`, les lignes `PaiementLivraisonLigdiCash` et `DemandeLivraison` sont verrouillées dans `@transaction.atomic` pour neutraliser les accès concurrents (webhook simultané au polling client).
2. **Vérification serveur-à-serveur** : Le webhook ne valide jamais un paiement sur la seule foi du payload entrant ; il interroge systématiquement `ligdicash.get_transaction(token=paiement.token_creation)`.
3. **Idempotence** : Si `paiement.statut == PaiementLivraisonLigdiCash.STATUT_REUSSI`, toute relance du webhook ou du polling met uniquement à jour les traces d'audit sans ré-exécuter les transitions métier.

---

## 4. Cahier des Charges pour le Relais des Agents (`pywebpush` & Garde-fou Flotte)

1. **Tâche Celery `pywebpush` post-`Smart-Drop`** :
   * Déclencher la notification push au client (`demande_livraison.client.user`) dès l'enregistrement de la position GPS du destinataire.
   * Injecter l'URL cible générée via `reverse("paiement_app:initier_livraison", kwargs={"reference": demande.reference})`.
2. **Garde-fou côté Livreur (`livreurs_app` / `demande_livraison_app`)** :
   * Vérifier avant toute transition vers le statut *en route / récupération / décollage* que le paiement de la course est validé (`paiement_livraison_ligdicash.statut == "reussi"`).