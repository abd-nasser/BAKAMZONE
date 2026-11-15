# Panier client et achats des produits des entreprises

## Objectif

Définir le panier client et le parcours d'achat des produits proposés par les entreprises partenaires, en réutilisant le catalogue et le workflow de livraison existants. Les modèles de base sont en place ; ce document suit les règles confirmées, les décisions restantes et les étapes d'implémentation.

## État actuel du projet

- Le catalogue client affiche les articles disponibles, non expirés et ayant du stock dans au moins un bloc actif.
- `Article` porte l'entreprise propriétaire, les prix courant et promotionnel, la disponibilité globale et les informations du produit.
- `StockBloc` porte la quantité physique d'un article dans chaque bloc. Il n'existe pas encore de mécanisme de réservation de stock.
- `DemandeLivraison` est le workflow de livraison classique. Il porte un départ, une arrivée, un colis, un tarif, un livreur et des statuts de livraison ; ce n'est pas une commande de produits.
- Aujourd'hui, `DemandeLivraison.client` référence obligatoirement un profil `Client`, et la création classique est réservée aux comptes clients. Une entreprise n'a donc pas encore le modèle d'accès nécessaire pour créer cette demande comme un client.
- `panier_app` est activée et contient les modèles `Panier`, `ArticlePanier`, `Commande` et `LigneCommande`, ainsi que leur migration initiale.
- La configuration Django contient déjà des variables d'environnement `LIGDICASH_API_KEY` et `LIGDICASH_API_TOKEN`, mais aucun `paiement_app` ni flux de paiement LigdiCash n'est encore implémenté.
- Le checkout client crée maintenant une commande en attente de paiement et ses lignes figées après revalidation des produits, des prix et du stock. Le stock n'est toutefois pas encore réservé/décrémenté.
- Le paiement LigdiCash, la réservation du stock et le bloc de préparation restent à implémenter. Le solde brut entreprise est calculé à partir des lignes payées et un workflow manuel de demande de retrait est disponible ; aucun paiement automatique LigdiCash n'est déclenché.

## Règles métier confirmées

- Un panier appartient à un client et peut contenir des articles de plusieurs entreprises.
- Les lignes de panier référencent les articles ; l'entreprise propriétaire est obtenue depuis chaque article.
- La validation porte sur le panier entier et crée une commande produit unique, distincte d'une demande de livraison.
- Le client fournit sa position GPS au passage de la commande. Cette position sert à calculer la proximité et doit être conservée avec la commande, afin que l'adresse de livraison historique ne change pas si le client met à jour son profil.
- Le parcours cible prévoit un paiement en ligne via LigdiCash après validation du panier ; cette intégration n'est pas encore implémentée.
- Le modèle cible prévoit que les fonds soient reçus sur le compte LigdiCash de BAKAMZONE. Actuellement, le tableau de bord calcule le solde à partir du statut de paiement de la commande ; l'entreprise peut demander un retrait, traité manuellement par un administrateur.
- Une commande n'est considérée comme payée qu'après confirmation fiable du résultat LigdiCash, et non simplement après la redirection vers le paiement.
- Le bloc de préparation est choisi selon le nombre de lignes qu'il peut fournir, puis selon sa proximité avec la position GPS du client.
- Le stock en bloc est réservé au passage de commande, pas à l'ajout au panier.
- Une entreprise est notifiée après confirmation du paiement d'une commande contenant l'un de ses articles ; l'ajout au panier et la simple création d'une commande en attente de paiement ne déclenchent pas cette notification.
- Pour les articles commandés qui ne sont pas disponibles dans le bloc retenu, l'entreprise propriétaire confirme après la commande qu'elle peut les fournir, puis crée une demande de livraison classique à destination du client.
- Cette demande est liée à la commande. L'entreprise renseigne sa zone de départ et capture sa position GPS ; la position d'arrivée provient de la position capturée par le client au checkout.
- Le tarif de chaque demande utilise les tarifs de livraison intra-bloc ou inter-blocs déjà configurés, selon les zones de départ et d'arrivée.
- Au checkout, le client choisit sa zone de livraison et peut capturer sa position GPS exacte ; si la capture échoue, les coordonnées de la zone sélectionnée sont utilisées.
- Si aucun bloc ne possède de ligne commandée, aucun bloc n'est retenu et toutes les lignes sont affectées aux entreprises propriétaires.
- Pour la première étape de checkout, les frais de livraison sont différés et ne sont pas inclus au montant des produits.
- Si le GPS du navigateur est indisponible, la zone de livraison choisie sert de repli à condition qu'elle ait des coordonnées ; la commande est refusée si ni la capture GPS ni la zone ne fournissent de coordonnées.
- Le checkout bloque la commande si une ligne dépasse le stock disponible au moment de la vérification. Pour un article en bloc, le stock vérifié est le total des quantités dans les blocs actifs ; pour un article hors bloc, il s'agit de `Article.quantite_disponible`.

## Architecture cible proposée

### Panier

- `Panier` appartient à un client et représente son panier actif.
- `ArticlePanier` lie le panier à un `Article` et porte la quantité souhaitée.
- Un client ne peut avoir qu'un panier actif à la fois et le même article ne peut apparaître qu'une fois dans ce panier ; sa quantité est portée par cette ligne.
- La méthode `Panier.total_panier()` calcule le montant indicatif avec le prix courant/promotionnel des articles.
- Le prix affiché dans le panier est indicatif : le prix effectif est recalculé et vérifié lors de la validation.
- Après validation, le panier commandé est conservé pour l'historique et un nouveau panier actif est disponible au client.

### Commande et lignes

- `Commande` est créée pour le panier entier et reste liée au client et au panier validé.
- `LigneCommande` conserve un instantané des informations nécessaires à l'historique : article, entreprise, libellé, quantité et prix unitaire appliqué. Le prix/nom d'un article modifié plus tard ne doit pas modifier une commande passée.
- La commande porte également la position GPS validée à la commande, les montants calculés, son statut global et son état de paiement LigdiCash.
- La commande et son paiement distinguent l'attente de paiement, le paiement réussi, l'échec et l'annulation. Le solde entreprise ne doit augmenter qu'après confirmation du paiement réussi.
- Les lignes doivent pouvoir être suivies séparément selon leur source de préparation : stock du bloc ou approvisionnement/livraison par l'entreprise.

### Paiement et soldes entreprise

- À la validation du panier, calculer et figer le total de commande avec `total_panier()`, créer la commande en attente de paiement, puis rediriger le client vers le template de paiement.
- `paiement_app` gère l'initialisation du paiement LigdiCash et le retour/notification serveur de son résultat. Le résultat doit être vérifié avant de marquer la commande payée et de créditer les soldes entreprise.
- Le tableau de bord entreprise présente le montant brut des lignes des commandes dont le paiement est `reussi`. Le calcul utilise les quantités et prix unitaires figés de chaque `LigneCommande`, attribuée à une seule entreprise ; une commande multi-entreprises ne crédite donc que les lignes propres à chaque entreprise.
- L'entreprise peut demander un retrait à tout moment. Le montant en attente ou approuvé est réservé et déduit du solde disponible ; un retrait payé est également déduit, tandis qu'un retrait rejeté libère le montant.
- L'administration approuve, rejette ou marque un retrait comme payé via les actions Django Admin. Le versement est manuel et hors plateforme, sans transfert automatique ni canal de paiement enregistré ; le contact du responsable entreprise est disponible dans son profil.
- Le tableau de bord distingue le total des ventes payées, les ventes payées du mois courant, les retraits réservés/payés et le solde disponible. Le retrait de fin de mois reste manuel, à la demande de l'entreprise ou selon le traitement administratif.
- La règle actuelle crédite le montant brut sans commission BAKAMZONE. Le seul critère de crédit est `statut_paiement="reussi"` ; une commande annulée dont le paiement reste marqué réussi reste donc incluse. Les remboursements ne sont pas encore gérés et doivent être traités explicitement avant tout retrait.
- Les opérations de paiement, crédits de solde et retraits doivent être traçables et idempotentes pour éviter les doubles crédits si une notification LigdiCash est répétée.

### Stock et choix du bloc

- Au checkout, recalculer la disponibilité et le prix, puis choisir le bloc actif qui possède le plus de lignes commandées ; en cas d'égalité, retenir le plus proche de la position GPS du client.
- Réserver dans ce bloc uniquement les quantités réellement disponibles pour les lignes concernées. La réservation doit être transactionnelle et protégée contre deux commandes concurrentes qui tentent de prendre le même stock.
- Les lignes absentes du stock du bloc sont affectées à l'entreprise propriétaire, qui doit initier une demande de livraison classique.
- La commande demeure unique même si son contenu est préparé depuis plusieurs sources. Les demandes de livraison associées sont des opérations distinctes liées à cette commande.
- Si aucun bloc ne possède de ligne commandée, aucun bloc n'est retenu et toutes les lignes sont affectées aux entreprises propriétaires.
- Le comportement en cas de rupture entre l'affichage du panier et le checkout doit être explicite : empêcher la confirmation des lignes indisponibles ou proposer leur retrait avant de confirmer. Aucune substitution automatique n'est prévue à ce stade.

### Demandes de livraison d'entreprise

- Une demande de livraison créée pour une ligne de commande doit conserver un lien vers la commande et préciser les lignes/quantités concernées.
- Après validation de la commande, l'entreprise confirme sa capacité à fournir les lignes qui lui sont affectées. Après confirmation, elle renseigne sa zone de départ, capture ses coordonnées GPS et crée la demande ; les coordonnées client de la commande sont reprises comme destination.
- Le tarif est calculé par la règle existante : intra-bloc si les zones de départ et d'arrivée sont dans le même bloc, inter-blocs sinon.
- Après capture GPS du client, la zone d'arrivée proposée est confirmée par le client. Le GPS demeure la destination précise ; le modèle `Zone` ne contient que des coordonnées ponctuelles.
- Le workflow de livraison existant exige actuellement un profil `Client` et ne permet pas directement à un compte entreprise de créer une demande. L'implémentation devra étendre proprement l'identification de l'émetteur et ses permissions, sans confondre entreprise et client.
- Le modèle `Zone` contient des coordonnées ponctuelles, mais pas de limites géographiques ; la règle qui déduit `zone_arrivee` à partir de la position GPS du client doit donc être définie.

## Workflow cible

1. Le client ajoute, modifie ou retire des articles dans son panier. Aucune quantité de stock n'est réservée et aucune entreprise n'est notifiée à ce stade.
2. Au checkout, le client autorise et capture sa position GPS.
3. Le système vérifie de nouveau la disponibilité, les quantités, les articles non expirés et les prix courants.
4. Le système choisit le bloc qui couvre le plus de lignes, départage les égalités selon la proximité du client, réserve les quantités disponibles et affecte les lignes restantes aux entreprises propriétaires.
5. **Implémenté partiellement :** le système revalide les articles, bloque la commande si le stock est insuffisant, fige les prix et crée la commande en attente de paiement avec les coordonnées GPS et la zone choisie. Le total initial correspond aux produits uniquement ; les frais sont différés. Le client est redirigé vers le détail de commande, pas encore vers un paiement LigdiCash.
6. Après confirmation fiable de la réussite du paiement, le paiement passe à l'état réussi, la commande est confirmée, les soldes dus sont attribués aux entreprises concernées et celles-ci sont notifiées.
7. Chaque entreprise concernée confirme les lignes qu'elle peut fournir. Elle crée ensuite une demande de livraison classique liée à la commande, avec sa zone/position de départ et les coordonnées GPS du client comme destination ; le tarif existant intra/inter-blocs est appliqué.
8. La commande suit la préparation du bloc et les demandes de livraison associées jusqu'à la réception. Le tableau de bord entreprise présente ses ventes payées et le solde récupérable à la demande ou en fin de mois.
9. Annulation, échec de paiement, échec de préparation ou échec de livraison doivent faire évoluer la commande, les réservations, les paiements et les soldes sans perdre l'historique.

## Points à valider avant l'implémentation

1. **Frais de livraison :** ils ne sont pas inclus dans le total produits de la première étape. Il reste à choisir leur mode de calcul et leur inclusion au paiement LigdiCash, ainsi que leur répartition/versement aux livreurs.
2. **Stock entreprise :** comment vérifier qu'une entreprise peut réellement fournir une ligne absente du bloc, puisque le modèle actuel ne décrit pas son stock hors bloc ?
3. **Regroupement :** une entreprise crée-t-elle une demande par commande ou par colis ? Comment traiter plusieurs entreprises et plusieurs livreurs pour une commande ?
4. **Statuts et annulations :** quelles transitions de commande et de lignes sont permises lorsqu'une partie du panier est livrée, annulée ou en échec ?
5. **Expiration du paiement :** combien de temps une commande en attente de paiement conserve-t-elle ses réservations de stock avant leur libération ?
6. **GPS indisponible :** règle de repli définie pour le premier checkout : utiliser les coordonnées de la zone choisie ; refuser la commande si ces coordonnées sont absentes.
7. **Remboursements :** définir le traitement d'une commande annulée ou remboursée après un paiement réussi, ainsi que l'effet sur le solde entreprise ; le workflow de remboursement n'est pas encore implémenté.
8. **Retraits :** préciser le canal de versement, les informations de bénéficiaire, les validations requises et les éventuels frais/délais. Le traitement actuel est manuel et hors plateforme.

## Découpage après validation

1. Valider les points ouverts ci-dessus et finaliser le diagramme des entités, les statuts et les responsabilités client/entreprise/bloc/livreur.
2. Implémenter les modèles et migrations du panier, de la commande, des lignes figées, des réservations, du paiement et des soldes/retraits entreprise.
3. Ajouter les services transactionnels de panier, checkout, initialisation et confirmation LigdiCash, affectation des sources, crédits de solde et annulation.
4. Ajouter le template de paiement, le retour/notification serveur LigdiCash, les vues de solde/retrait entreprise, les permissions et notifications nécessaires.
5. Tester les prix figés, le stock concurrent, les paiements répétés/échoués, les crédits sans doublon, les permissions entreprise, les commandes multi-entreprises et les livraisons partielles.

## Statut

- **Cadrage :** en cours ; les règles métier confirmées sont listées ci-dessus, les points ouverts restent à valider.
- **Implémentation :** les modèles du panier et des commandes, l'affichage, l'ajout, la modification et le vidage du panier sont disponibles. Le checkout initial crée la commande en attente, fige les lignes, vérifie le stock et enregistre la zone et le GPS ; il ne réserve pas encore le stock et n'initialise aucun paiement. Une page entreprise permet de publier une course regroupant toutes les lignes hors bloc de cette entreprise dans une commande payée. L'entreprise choisit la zone de dispatch et capture séparément son GPS réel de collecte ; la destination vient du GPS de commande. Les entreprises différentes restent sur des courses séparées ; les frais ne sont pas encaissés. Le solde entreprise est calculé depuis les lignes dont la commande a le paiement `reussi`; le retrait se demande sur le solde et est traité manuellement par un administrateur.
- **Suivi :** tâche « Panier client & achats des produits des entreprises » dans [`bakamzone_todo_list.md`](./bakamzone_todo_list.md).
