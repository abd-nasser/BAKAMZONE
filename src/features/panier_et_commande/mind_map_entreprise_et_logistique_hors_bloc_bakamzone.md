# 🏢 Module Entreprise — Architecture & Flux Métier (BAKAMZONE)

Ce document détaille l'architecture technique et la logique métier de l'espace partenaire dans la marketplace **BAKAMZONE**, couvrant le contrôle d'accès, le calcul financier des soldes, les demandes de retrait et la gestion logistique des articles hors-bloc.

## 🧠 Carte Mentale du Module Entreprise

```text
🏢 MODULE ENTREPRISE — ARCHITECTURE & FLUX MÉTIER (BAKAMZONE)

 ├── 1. SÉCURITÉ & CONTEXTE (EntrepriseRequiredMixin)
 │     ├── Vérification de l'authentification (LoginRequiredMixin)
 │     ├── Contrôle du rôle strict ("entreprise" + existence de l'objet Entreprise)
 │     └── `get_entreprise()` : Récupération sécurisée du profil marchand associé
 │
 ├── 2. GESTION DU SOLDE & COMPTABILITÉ (obtenir_solde_entreprise)
 │     ├── Filtrage des ventes payées (LigneCommande avec `statut_paiement = REUSSI`)
 │     ├── Ventilation temporelle (Chiffre d'affaires global vs Chiffre d'affaires du mois)
 │     ├── Calcul des retraits réservés (En attente, approuvés ou payés)
 │     └── Calcul du solde disponible :
 │           └── `montant_ventes` - `montant_retraits_reserves` (planché à 0 min)
 │
 ├── 3. DEMANDES DE RETRAIT (DemanderRetraitEntrepriseView)
 │     ├── Validation du formulaire (`DemandeRetraitEntrepriseForm`)
 │     ├── Verrouillage pessimiste (`select_for_update`) sur l'objet Entreprise
 │     ├── Vérification en temps réel : Le montant demandé dépasse-t-il le solde disponible ?
 │     └── Création transactionnelle (`RetraitEntreprise.objects.create`) en statut "en_attente"
 │
 ├── 4. SUIVI DES LIVRAISONS D'ARTICLES HORS BLOC (EntrepriseLivraisonsArticlesView)
 │     ├── Filtrage strict :
 │           ├── Lignes de l'entreprise (`entreprise=entreprise`)
 │           ├── Produits hors bloc uniquement (`article__en_bloc = False`)
 │           ├── Commandes payées (`statut_paiement = REUSSI`) et non annulées
 │     ├── Structuration par commande : Groupement intelligent des lignes par `commande_id`
 │     ├── Association des courses existantes (`DemandeLivraison`)
 │     └── Verrouillage dynamique (`peut_creer_course`) : Interdit les doublons si une course est active
 │
 └── 5. CRÉATION D'UNE COURSE DE LIVRAISON (CreerLivraisonCommandeEntrepriseView)
       ├── @transaction.atomic & Verrouillage pessimiste (`select_for_update`)
       ├── Contrôle de validité : Vérifie que la commande n'est pas annulée
       ├── Récupération des données figées de livraison (Position GPS du client au checkout)
       ├── Calcul automatique du tarif de course (`calculer_tarif_livraison`)
       └── Publication de la course (`DemandeLivraison`) aux livreurs du bloc de départ choisi
```

## 🛡️ Détails Techniques & Garanties d'Intégrité

### 1. Contrôle d'Accès et Cloisonnement (`EntrepriseRequiredMixin`)
* **Validation des permissions :** Garantit que seuls les utilisateurs authentifiés ayant le rôle `entreprise` et liés à une entité `Entreprise` active peuvent accéder aux vues marchandes.
* **Isolation des données :** Toutes les requêtes filtrent systématiquement sur l'instance `entreprise` de l'utilisateur connecté, empêchant tout accès transversal aux ventes ou livraisons d'un autre partenaire.

### 2. Comptabilité Temps Réel & Retraits (`obtenir_solde_entreprise` & `DemanderRetraitEntrepriseView`)
* **Revenus confirmés uniquement :** Le calcul du chiffre d'affaires agrège exclusivement les `LigneCommande` dont la `Commande` associée possède le statut `PAIEMENT_REUSSI` (utilisant `ExpressionWrapper` pour multiplier la quantité par le prix unitaire figé).
* **Protection contre le sur-retrait :** Lors d'une demande de retrait, la vue utilise `@transaction.atomic` et verrouille la ligne de l'entreprise via `select_for_update()`. Elle soustrait les retraits déjà engagés (`en_attente`, `approuve`, `paye`) du total des ventes pour valider que le solde disponible couvre la demande.

### 3. Logistique des Produits Hors-Bloc (`EntrepriseLivraisonsArticlesView`)
* **Séparation des flux :** Les articles stockés en bloc (`en_bloc=True`) sont gérés directement par les administrateurs de quartier, tandis que les articles hors-bloc (`en_bloc=False`) apparaissent sur le tableau de bord de l'entreprise dès confirmation du paiement.
* **Optimisation SQL & Anti-doublon :** L'utilisation combinée de `select_related` et `prefetch_related` évite les requêtes N+1. Le drapeau `peut_creer_course` vérifie l'absence de course active (`en_attente`, `acceptee`, `en_cours`, `livree`) avant d'autoriser une nouvelle publication.

### 4. Déclenchement de la Course (`CreerLivraisonCommandeEntrepriseView`)
* **Données géographiques figées :** La course hérite automatiquement de la `zone_arrivee` et des coordonnées GPS exactes (`latitude_livraison`, `longitude_livraison`) capturées lors de la validation du panier par le client.
* **Publication à la flotte interne :** La course groupée est créée avec le tarif calculé dynamiquement (`calculer_tarif_livraison`) et diffusée immédiatement aux livreurs rattachés au bloc de départ de l'entreprise.