# BAKAMZONE — Plan stratégique

*Document de synthèse : vision, modèle, organisation et plan de lancement. Version de travail, à compléter et valider avec l'associé.*

---

## 1. Origine du projet

BAKAMZONE remplace Livrez-vous, le projet de marketplace ouverte (connecter des livreurs indépendants à des clients) sur lequel le travail avait commencé.

Le changement vient d'une proposition de l'associé : monter une **entreprise de livraison intégrée** avec sa propre flotte, plutôt qu'une plateforme qui met en relation des tiers. Les deux modèles ne se combinent pas : une marketplace ouverte et une flotte propriétaire ont des intérêts opposés. Le choix est donc tranché : **modèle intégré, sans mélange**.

**Le constat de départ reste valable.** Selon l'observation de terrain du fondateur, plus de 90 % des livreurs et sociétés de livraison locaux n'ont ni site ni application : leur seul canal est WhatsApp. Chaque soir, des ventes se perdent parce qu'un client ne trouve pas de livreur rapidement et sans incertitude.

---

## 2. Le concept

- **Une flotte propre** de motos électriques, fabriquées sur commande en Chine.
- **Des « blocs »** : un bloc par quartier, avec une équipe de 5 à 10 livreurs et du personnel technique sur place. Les admins du bloc y travaillent.
- **Un système central** qui relie tous les blocs.
- **Du stockage de proximité** : les entreprises partenaires envoient leurs produits dans les blocs. Quand un client commande, le produit sort du bloc le plus proche et est livré par un livreur de la flotte.
- **Une référence locale** : devenir le nom que l'on associe d'abord à la livraison en ville, avec une qualité de service contrôlée de bout en bout.

---

## 3. Les quatre rôles

| Rôle | Ce qu'il fait |
|---|---|
| **Client** | Parcourt le catalogue, commande avec sa position, paie (mobile money ou à la livraison), suit sa livraison en temps réel, note le livreur. |
| **Livreur** | Employé de la flotte rattaché à un bloc. Signale sa disponibilité, accepte les courses, valide chaque étape (récupéré, en route, livré). |
| **Admin de bloc** | Gère le stock du bloc (réception, quantités, alertes), prépare les commandes, assigne les livreurs, suit son équipe. |
| **Entreprise partenaire** | Ajoute et gère ses **produits** (et non des livreurs) : stock par bloc, quantité restante, commandes en cours, évolution de chaque produit de l'envoi au bloc jusqu'à la livraison, ventes. |

Cycle de vie d'un produit côté entreprise : envoyé au bloc, reçu et en stock, commandé, en livraison, livré.

---

## 4. Zone et lancement

- **Un seul quartier au départ**, avec un premier bloc. Si le modèle tient, on étend ensuite, quartier par quartier.
- **Objectif de lancement : janvier 2027.**
- **État d'avancement de la plateforme** : environ 25 %. L'authentification (client, livreur, entreprise) et les interfaces correspondantes sont prêtes.
- La date de janvier 2027 est un objectif. Elle doit être ajustée plutôt que précipitée si les délais d'import ou de mise en place du premier bloc ne la permettent pas.

---

## 5. Modèle économique (à finaliser)

**Ce qui est posé :** les entreprises qui ont des produits à vendre et à faire livrer paient un **abonnement** pour les stocker dans les blocs et utiliser la plateforme.

**Ce qui reste à décider ensemble :**
- Les paliers d'abonnement : ils reposaient sur le nombre de livreurs dans l'ancien projet, il faut les repenser autour du nombre de produits, du volume stocké ou du nombre de blocs utilisés.
- Qui paie la livraison et combien : frais côté client, inclus dans l'abonnement, ou mélange des deux.
- Les prix, une fois les coûts réels connus (motos, personnel, entretien, stockage).

---

## 6. Différenciation

1. **Contrôle de la qualité** : flotte, équipes et stock sont à nous. Pas de dépendance à des prestataires indépendants dont on ne maîtrise ni la ponctualité ni le comportement.
2. **Rapidité par la proximité** : le produit est déjà stocké dans le quartier, donc la livraison part d'à côté.
3. **Visibilité complète pour les entreprises** : chaque partenaire voit en direct ses commandes et ses quantités restantes.
4. **Présence humaine locale** : équipes dans chaque quartier et support réel, dans un contexte où la relation compte.
5. **Connaissance fine du terrain** de lancement.

---

## 7. Vision et impact

L'objectif n'est pas seulement de livrer des colis : c'est de **créer des emplois pour des jeunes** (livreurs, techniciens, admins de bloc), dans un contexte où les postes publics sont saturés. L'approche reste prudente : commencer petit dans un quartier, prouver que le modèle tient, puis étendre.

---

## 8. Organisation et associés

L'associé apporte le capital et une partie de la vision. Avant tout engagement financier (import des motos, recrutement), il faut **acter par écrit** :

- la répartition des parts ;
- les rôles : qui pilote la plateforme/technique, qui pilote la logistique physique et le capital ;
- le mode de décision en cas de désaccord ;
- ce qui se passe si l'un des deux veut quitter le projet.

Une checklist de cadrage à cocher à deux a été préparée à cet effet.

---

## 9. Direction technique

**Ce qui est réutilisé de l'ancien projet :** authentification par téléphone ou email, rôles, zones, commandes, avis sur les livreurs, vérification d'identité (carte d'identité + selfie, désormais pour les recrutements), suivi de position en temps réel.

**Ce qui est nouveau :**
- un modèle **Bloc** (point de stockage d'un quartier, avec ses admins et ses livreurs) ;
- un modèle de **stock** : produits, quantités par bloc, mouvements (réception, réservation, sortie) ;
- l'interface entreprise centrée sur les produits ;
- la **PWA** : application installable depuis la page d'accueil, avec un bouton « Télécharger l'application ».

**Points de rigueur :** les quantités de stock doivent être mises à jour de façon atomique (pas de survente ni de quantité faussée si deux commandes arrivent en même temps), les tâches lourdes (notifications, emails) passent en asynchrone, le suivi en temps réel s'appuie sur des WebSockets, et une API propre permettra plus tard des intégrations.

**Design :** palette de départ émeraude et orange, mode clair et sombre, interface en français, pensée mobile d'abord pour le client et le livreur.

---

## 10. Prochaines étapes

1. Générer la **maquette** de la plateforme (4 rôles + accueil PWA) et la faire valider par l'associé.
2. Valider le **nom** : vérifier la disponibilité du domaine et des comptes de réseaux sociaux, et l'absence de risque de confusion avec une marque existante.
3. Remplir et signer la **checklist de cadrage** (parts, rôles, décision, sortie).
4. Chiffrer le **budget réel du premier bloc** (motos, import, équipement, personnel, trois premiers mois).
5. Choisir le **quartier pilote** et fixer le nombre de livreurs du premier bloc.
6. Adapter les modèles et la base de code existante (Bloc, Produit, Stock).

---

## 11. Risques à garder en tête

- **Le capital et la logistique physique** : importer et dédouaner des motos, entretenir une flotte, gérer des accidents, des pannes ou des vols.
- **Les délais d'import** : ils peuvent décaler la date de lancement.
- **Le stock** : écarts entre le stock réel et le stock affiché, produits abîmés, perdus ou périmés (d'où le choix de produits non périssables au départ).
- **La concurrence**, locale ou internationale : à surveiller froidement, sans décider sous la pression de la crainte.
- **La relation entre associés** : plus l'argent engagé est important, plus l'accord écrit compte.
- **La charge d'une petite équipe** : tenir la plateforme et l'exploitation en parallèle demande de recruter tôt, comme prévu.

---

*Document vivant : à mettre à jour à mesure que les décisions sont prises.*
