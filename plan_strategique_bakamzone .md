# BAKAMZONE — Plan stratégique
**Document de synthèse : vision, modèle, organisation et plan de lancement.**  
*Version de travail, mise à jour avec l'associé.*

---

## 1. Origine du projet
BAKAMZONE remplace *Livrez-vous*, le projet initial de marketplace ouverte (mise en relation de livreurs indépendants et de clients). 

Le changement vient d'une proposition de l'associé : **monter une entreprise de livraison intégrée avec sa propre flotte**, plutôt qu'une plateforme tierce. Les deux modèles s'opposant (intérêts contradictoires entre marketplace ouverte et flotte propriétaire), le choix est tranché : **modèle intégré, sans mélange**.

Le constat de départ reste le même : plus de 90 % des livreurs et sociétés de livraison locaux n'ont ni site ni application ; leur seul canal est WhatsApp. Chaque soir, des ventes se perdent faute de trouver un livreur rapidement et sans incertitude.

---

## 2. Le concept
- **Une flotte propre de motos électriques**, fabriquées sur commande en Chine.
- **Des « blocs »** : un bloc par quartier, doté d'une équipe de 5 à 10 livreurs, du personnel technique sur place et des administrateurs du bloc.
- **Un système central** qui relie tous les blocs entre eux.
- **Du stockage de proximité** : les entreprises partenaires envoient leurs produits dans les blocs. Lorsqu'un client commande, le produit est expédié depuis le bloc le plus proche par un livreur de la flotte.
- **Une référence locale** : s'imposer comme le nom incontournable de la livraison en ville grâce à une qualité de service maîtrisée de bout en bout.

---

## 3. Les quatre rôles
| Rôle | Ce qu'il fait |
| :--- | :--- |
| **Client** | Parcourt le catalogue, commande avec sa position géolocalisée, paie (mobile money ou à la livraison), suit sa course en temps réel, note le livreur. |
| **Livreur** | Employé de la flotte rattaché à un bloc. Signale sa disponibilité, accepte les courses, valide chaque étape (récupéré, en route, livré). |
| **Admin de bloc** | Gère le stock du bloc (réception, quantités, alertes), prépare les commandes, assigne les livreurs, supervise son équipe locale. |
| **Entreprise partenaire** | Ajoute et gère ses articles et ses stocks par bloc, suit les ventes, les quantités restantes et l'état des commandes de l'envoi au bloc jusqu'à la livraison finale. |

*Cycle de vie d'un produit côté entreprise :* Envoyé au bloc ➔ Reçu et en stock ➔ Commandé ➔ En livraison ➔ Livré.

---

## 4. Zone et lancement
- **Lancement initial** : Un seul quartier au départ, avec un premier bloc pilote. En cas de succès, extension progressive, quartier par quartier.
- **Objectif de calendrier** : Janvier 2027 (à ajuster selon les délais d'import et d'installation pour ne pas précipiter les choses).
- **État d'avancement technique** : Redémarrage propre sur une base moderne (authentification, rôles, structures de blocs, d'articles et de stocks).

---

## 5. Modèle économique
- **Ce qui est posé** : Les entreprises partenaires paient un abonnement (basé sur des paliers de quotas d'articles et d'administrateurs) pour stocker leurs produits dans les blocs et utiliser la plateforme.
- **Ce qui reste à décider** : Les frais de livraison (côté client, inclus dans l'abonnement, ou formule mixte) et la tarification définitive une fois les coûts réels cernés (motos, personnel, entretien, stockage).

---

## 6. Différenciation
1. **Contrôle de la qualité** : Flotte, équipes et stocks appartiennent à l'entreprise (zéro dépendance envers des prestataires indépendants aléatoires).
2. **Rapidité par la proximité** : Le produit est déjà stocké dans le quartier du client, ce qui raccourcit drastiquement les délais.
3. **Visibilité complète** : Suivi en direct pour les partenaires de leurs stocks et commandes.
4. **Présence humaine locale** : Ancrage physique dans les quartiers avec un support réel.
5. **Connaissance fine du terrain.**

---

## 7. Vision et impact
Créer des emplois stables pour les jeunes (livreurs, techniciens, admins de bloc) dans un contexte où les postes traditionnels sont saturés. Approche prudente : commencer petit, prouver la viabilité du modèle, puis grandir.

---

## 8. Organisation et associés
Avant tout engagement financier lourd (import des motos, recrutements), un accord écrit doit acter :
- La répartition des parts.
- Les rôles opérationnels (technique / logistique physique et capital).
- Les règles de prise de décision en cas de désaccord et les conditions de sortie.
*(Une checklist de cadrage dédiée a été préparée pour formaliser ces points).*

---

## 9. Direction technique & Stack validée
* **Hébergement & Infra** : Conteneurisation **Docker**, serveur **Nginx** sur un VPS KVM 2 (Hostinger).
* **Stack Logicielle** : 
  - **Django** (Back-end et logique métier robuste).
  - **django-tailwind + DaisyUI** (Design system moderne, classes utilitaires).
  - **HTMX** (Interactivity dynamique et fluide sans la lourdeur d'une SPA type React).
  - **Alpine.js** (Gestion légère des états front-end et des micro-interactivités).

### Identité Visuelle & Mode Sombre/Clair :
- **Nom & Logo** : **BAKAM** en **émeraude** et **ZONE** en **orange** (rappelant les couleurs de la flotte).
- **Palette de couleurs** :
  - **Émeraude** (Vert principal) : Confiance, validation, sécurité, éco-responsabilité.
  - **Orange** (Accent / Alerte) : Énergie, actions rapides, alertes de stock.
- **Gestion du Mode Sombre / Clair** : Intégration native via **DaisyUI / Tailwind** (`data-theme`), permettant aux utilisateurs (notamment les livreurs en plein soleil ou de nuit) de basculer facilement d'un mode à l'autre.

### Approche Mobile-First PWA :
- Conçue en **Progressive Web App (PWA)** pour offrir une expérience plus fluide et agréable que du natif, sans les contraintes de validation des stores (App Store / Google Play).
- Bouton d'installation rapide (« Télécharger l'application ») directement depuis la page d'accueil.
- Interfaces optimisées en priorité pour les mobiles (clients et livreurs sur le terrain).

---

## 10. Prochaines étapes
1. Finaliser et valider la structure des modèles Django (`accounts_app`, `entreprises_app`, `articles_app`, `clients_app`, `livreurs_app`).
2. Valider le nom de la marque (disponibilité domaine et réseaux sociaux).
3. Remplir et signer la checklist de cadrage entre associés.
4. Chiffrer le budget prévisionnel du premier bloc (motos, import, équipement, personnel, fonds de roulement sur 3 mois).
5. Choisir le quartier pilote et fixer la taille initiale de la flotte.

---

## 11. Risques à garder en tête
- Gestion du capital et de la logistique physique (dédouanement des motos, pannes, vols, maintenance).
- Respect des délais d'importation.
- Fiabilité des stocks (écarts entre inventaire théorique et physique, choix initial de produits non périssables).
- Équilibre de la relation entre associés face aux investissements.
- Gestion de la charge de travail pour l'équipe restreinte au démarrage.