# 📦 Architecture & Flux : Panier et Création de Commande (BAKAMZONE)

Ce document synthétise l'architecture technique, les règles de sécurité et le cycle de vie complet d'une commande dans la marketplace **BAKAMZONE**, de l'ajout au panier jusqu'à son éclatement multi-vendeur.

---

## 🧠 Carte Mentale du Flux de Validation

```text
📦 PANIER ET CRÉATION DE COMMANDE — FLUX DE VALIDATION (BAKAMZONE)

 ├── 1. GESTION DU PANIER (Panier & ArticlePanier)
 │     ├── Panier actif unique par client (Contrainte unique PostgreSQL)
 │     ├── Ajout d'un article (Vérification de disponibilité et date d'expiration)
 │     └── Vérification intelligente du stock :
 │           ├── Si Article en bloc (Somme des StockBloc actifs > 0)
 │           └── Si Article hors bloc (Vérification de `quantite_disponible`)
 │
 ├── 2. LE CHECKOUT & SAISIE DE LIVRAISON (ValidationCommandeForm)
 │     ├── Sélection de la zone d'arrivée (Filtrée par blocs actifs)
 │     ├── Capture GPS du client (Latitude / Longitude via Alpine.js)
 │     └── Mécanisme de repli (Fallback automatique sur les coordonnées de la zone si le GPS échoue)
 │
 ├── 3. LA TRANSACTION ATOMIQUE & SÉCURISÉE (ValiderCommandeView)
 │     ├── @transaction.atomic & Verrouillage pessimiste (select_for_update)
 │     ├── Anti-double validation (Vérification si le panier est déjà "commandé")
 │     └── Recontrôle final des stocks en temps réel (Bloque si rupture de dernière minute)
 │
 └── 4. TRANSFORMATION & ÉCLATEMENT (Commande & LigneCommande)
       ├── Création de la Commande maîtresse :
       │     ├── Référence unique UUID (anti-scraping / sécurisation LigdiCash)
       │     ├── Fixation de la position GPS exacte de livraison
       │     ├── Statut logistique par défaut : "En attente de paiement"
       │     └── Statut de paiement : "Non initié"
       ├── Génération du Snapshot immuable (LigneCommande) :
       │     ├── Éclatement par entreprise (Chaque marchand voit ses propres lignes)
       │     ├── Copie figée des prix unitaires et des noms (protection contre modif du catalogue)
       │     └── Passage du Panier actif au statut "commandé" (ouverture d'un nouveau panier vide)
       └── Redirection vers la vue de détail / page de paiement en ligne
```

---

## 🛡️ Détails Techniques & Garanties d'Intégrité

### 1. Sécurité & Contrôle d'Accès (`ClientPanierRequiredMixin`)
* **Validation du profil :** Vérification stricte que `request.user.role == "client"` et que l'objet `Client` existe.
* **Protection IDOR :** Toutes les requêtes sur les commandes (`DetailCommandeView`) filtrent par `client=self.get_client()`, empêchant tout accès non autorisé via manipulation d'URL.

### 2. Tolérance aux Pannes GPS (`ValidationCommandeForm`)
* Le front-end capture la géolocalisation via Alpine.js dans des champs cachés (`latitude`, `longitude`).
* Si le GPS échoue ou est refusé par le navigateur, la méthode `clean()` bascule automatiquement sur les coordonnées géographiques de la `zone_arrivee` sélectionnée.

### 3. Protection Contre la Concurrence (`ValiderCommandeView`)
* **Transaction Atomique & Verrouillage Pessimiste :** L'utilisation de `transaction.atomic()` combinée à `select_for_update()` sur le `Panier` et les `ArticlePanier` empêche toute double soumission simultanée ou corruption de données.
* **Revalidation en Temps Réel :** Les prix, dates d'expiration et niveaux de stocks (en bloc via `StockBloc` ou hors bloc via `quantite_disponible`) sont recontrôlés juste avant la création en base.

### 4. Éclatement Multi-Vendeurs & Snapshot (`Commande` & `LigneCommande`)
* **Commande Maîtresse :** Centralise le paiement global (LigdiCash), l'adresse GPS de livraison et la référence UUID.
* **Lignes de Commande (`LigneCommande`) :** Utilisent `bulk_create` pour figer le nom de l'article, le nom de l'entreprise et le prix unitaire payé. Chaque entreprise partenaire accède uniquement à ses propres lignes dans son espace marchand pour préparer ses articles ou initier une course de livraison.