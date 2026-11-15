# Livraison des articles d'une commande par une entreprise

Ce document décrit le workflow actuellement implémenté pour qu'une entreprise demande un livreur pour les articles hors bloc d'une commande payée. Il couvre le cas où une commande contient plusieurs articles de la même entreprise, ainsi que le cas où elle regroupe plusieurs entreprises.

## Règle de regroupement

La course est créée **par commande et par entreprise** :

- Toutes les lignes de cette commande qui appartiennent à l'entreprise connectée et dont l'article est hors bloc (`Article.en_bloc=False`) sont regroupées dans une seule course.
- Les articles en bloc ne font pas partie de cette course.
- Les lignes appartenant à d'autres entreprises restent exclues. Chaque autre entreprise crée et suit sa propre course pour ses lignes éligibles.
- Une commande commune peut donc donner lieu à plusieurs courses, mais au maximum une course active par entreprise pour cette commande.

**Exemple :** la commande `CMD-123` contient deux articles hors bloc de l'entreprise A, un article en bloc de A et un article hors bloc de B. A peut créer une course contenant ses deux articles hors bloc ; l'article en bloc n'y figure pas. B voit uniquement sa propre ligne et peut créer sa course séparée. Le client et la destination sont communs, mais les colis et les responsabilités de préparation restent séparés par entreprise.

## Conditions pour qu'une commande apparaisse

Dans la page entreprise, une ligne est éligible lorsque toutes ces conditions sont réunies :

1. La ligne appartient à l'entreprise connectée (`LigneCommande.entreprise`).
2. L'article lié appartient aussi à cette entreprise (`Article.entreprise`). Cette vérification supplémentaire évite de se fier uniquement à l'instantané historique de la ligne.
3. L'article est hors bloc (`Article.en_bloc=False`).
4. Le statut de paiement de la commande est `reussi`.
5. La commande n'est pas annulée.

La page ne liste que les lignes qui satisfont ces critères. Elle ne rend donc pas visibles à l'entreprise les articles des autres vendeurs, ni les lignes hors critères.

## Parcours de l'entreprise

1. Le responsable connecté ouvre **Suivre les livraisons** depuis son tableau de bord. La page est réservée à un utilisateur dont le rôle est `entreprise` et qui possède un profil `Entreprise`.
2. La page regroupe les lignes éligibles par commande et affiche les articles, leurs quantités et la destination enregistrée lors du checkout client.
3. Pour chaque commande, l'entreprise choisit une **zone de départ** afin de sélectionner le bloc de dispatch, puis capture la position GPS réelle du point de collecte à l'aide du navigateur. Les deux coordonnées sont affichées et doivent être présentes avant l'envoi.
4. L'entreprise clique sur **Trouver un livreur**. La requête est envoyée en POST avec protection CSRF, la zone de dispatch et la position capturée.
5. Le serveur recherche de nouveau, en base, les lignes éligibles de cette commande pour cette entreprise. Les identifiants de lignes provenant du navigateur ne servent pas à décider quels articles sont inclus.
6. Dans une transaction, le serveur vérifie qu'une course existante ne couvre pas déjà une des lignes éligibles, puis crée une `DemandeLivraison` et lui associe toutes ces lignes.
7. La course apparaît dans les demandes disponibles des livreurs du bloc de la zone de départ.

Une commande sans ligne éligible pour l'entreprise produit une réponse 404 à la création de course. Un utilisateur d'une autre entreprise ne peut donc pas créer une course à partir de la commande du vendeur.

## Données de la course créée

La `DemandeLivraison` contient notamment :

| Information | Source |
|---|---|
| Client destinataire | Client associé à la commande |
| Articles et quantités du colis | Lignes de commande éligibles de l'entreprise |
| Description du colis | Noms et quantités des lignes regroupées, avec la référence de commande |
| Zone de départ | Choix fait par l'entreprise |
| Coordonnées GPS de départ | Position réelle capturée par l'entreprise au moment de publier la course |
| Zone d'arrivée | `Commande.zone_arrivee` |
| Coordonnées GPS d'arrivée | `Commande.latitude_livraison` et `Commande.longitude_livraison` |
| Téléphone WhatsApp destinataire | Téléphone du compte utilisateur du client |
| Prix de course | Calcul actuel selon que les zones de départ et d'arrivée sont dans le même bloc |
| Livreur initial | Aucun ; la demande est publiée en attente dans le pool correspondant au bloc de départ |

**À distinguer :** la zone sélectionnée par l'entreprise sert au dispatch des livreurs et au calcul du tarif ; elle ne représente pas l'adresse exacte de collecte. Les coordonnées GPS de départ sont capturées séparément sur place. Les coordonnées GPS de la commande représentent la destination du client.

## Suite du parcours livreur

La demande est créée avec le statut `en_attente`. Comme le client a déjà partagé son GPS au checkout, la création reporte ces coordonnées dans `latitude_destinataire_reelle` et `longitude_destinataire_reelle`, marque `position_destinataire_validee=True` et fixe `statut_destinataire="position_recue"`. Le tableau de bord livreur existant propose les demandes en attente du bloc de départ. Le livreur éligible peut accepter la course ; le workflow de livraison existant fait alors évoluer la demande (`acceptee`, puis `en_cours`, puis `livree`). Une course peut également être `annulee`.

La demande utilise le client de la commande comme destinataire afin de réutiliser le parcours existant de livraison et de notification. Le suivi visible à l'entreprise est celui de la course rattachée aux lignes de sa propre commande.

Lorsqu'une position destinataire est déjà validée, l'acceptation par le livreur conserve cet état et ne programme pas Smart-Drop ni le contrôle Celery après trois minutes. Ce contrôle n'escalade en `alerte_assistant` que si aucune position n'est validée et que le statut destinataire reste `en_attente`. Pour les demandes classiques sans GPS client validé, le parcours Smart-Drop habituel est conservé.

## Frais et limites actuelles

- Le tarif existant est calculé et stocké dans `DemandeLivraison.prix`, et affiché comme indicatif.
- La création de la course n'ajoute pas les frais au total de la commande et ne prélève ni n'encaisse ces frais.
- Il n'y a pas encore de validation dédiée de la disponibilité du stock au moment de publier la course.
- La position de départ est celle du navigateur utilisé pendant la création de la course ; il appartient à l'entreprise de lancer la capture au point réel de collecte. L'application ne vérifie pas que le GPS appartient au bloc de dispatch choisi.
- La prévention d'une deuxième demande repose sur la vérification des courses liées aux lignes avant création et sur la transaction de la vue. La contrainte existante du modèle porte sur la relation historique `ligne_commande` ; le regroupement complet des articles est porté par la relation multiple `lignes_commande`.
- Si une course est annulée, une nouvelle demande peut être publiée pour cette commande et cette entreprise.

## Fichiers de référence

- [Vue entreprise, filtrage et création de la course](./src/entreprise_app/views.py)
- [Formulaire de sélection de la zone de départ](./src/entreprise_app/forms.py)
- [Routes de la page et de création](./src/entreprise_app/urls.py)
- [Modèle `DemandeLivraison` et liens vers les lignes de commande](./src/demande_livraison_app/models.py)
- [Calcul indicatif du tarif](./src/demande_livraison_app/pricing.py)
- [Page entreprise des livraisons](./src/templates/entreprise_templates/entreprise_livraisons_articles.html)
- [Dispatch et acceptation côté livreur](./src/livreurs_app/views.py)
- [Test d'isolation entre entreprises et de regroupement des lignes](./src/entreprise_app/tests.py)
