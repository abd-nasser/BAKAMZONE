# Workflow d'une demande de livraison — Client, livreur et Smart-Drop

Ce document décrit le flux actuellement implémenté dans BAKAMZONE : création d'une demande par le client, traitement dans l'espace livreur, notification WhatsApp au destinataire, puis collecte de sa position GPS avec un lien public protégé par UUID.

## 1. Création de la demande par le client

Le client peut créer une livraison depuis le formulaire général ou depuis le profil d'un livreur :

- Formulaire général : `demande_livraison_app:creer-demande`, rendu par `CreerDemandeLivraisonView`.
- Commande directe depuis un profil : `clients_app:profil-livreur`, en `POST` sur `LivreurProfilViewByClient`. La demande est alors préassignée au livreur choisi.

Dans les deux cas, `DemandeLivraisonForm` valide les zones de départ et d'arrivée, les coordonnées du départ, le numéro WhatsApp et la description éventuelle. Si le navigateur n'a pas transmis de GPS de départ, le formulaire reprend les coordonnées configurées sur la zone. Le tarif est recalculé côté serveur ; le tarif affiché dynamiquement à l'écran n'est pas la source de vérité.

À l'enregistrement, `DemandeLivraison` reçoit notamment :

- un identifiant numérique Django (`pk`), affiché comme numéro de course, par exemple `#42` ;
- un `statut` initial égal à `en_attente` ;
- le destinataire et son numéro WhatsApp ;
- un `token_pwa_destinataire` généré avec `uuid.uuid4()`.

Le token est distinct du numéro de course : `#42` sert à identifier la course pour l'équipe, tandis que le token UUID est la clé incluse dans le lien privé de partage GPS.

## 2. Affichage dans l'espace livreur

Le tableau de bord `LivreurProfilViewByLivreur` est accessible aux livreurs authentifiés qui ont un profil actif.

La liste des demandes en attente contient :

1. les demandes préassignées au livreur ;
2. les demandes sans livreur dont la zone de départ appartient au bloc de ce livreur.

Chaque carte présente le trajet, le prix, le numéro WhatsApp du destinataire et les informations du colis. Le formulaire d'acceptation et celui de refus envoient des requêtes `POST` protégées par CSRF.

Routes des actions :

- `livreurs_app:accepter-demande` — `POST /livreurs/demande/<pk>/accepter/` ;
- `livreurs_app:refuser-demande` — `POST /livreurs/demande/<pk>/refuser/`.

## 3. Acceptation ou refus

### Accepter

`AccepterDemandeLivraisonView` ne traite que les demandes `en_attente` qui sont préassignées au livreur courant ou ouvertes dans son bloc. Une mise à jour conditionnelle en base attribue la demande et passe son statut à `acceptee`, fixe `date_acceptation` et maintient `statut_destinataire` à `en_attente`. Cette opération atomique évite qu'une demande ouverte soit attribuée simultanément à deux livreurs.

Après l'enregistrement, la vue programme `envoyer_notification_smartdrop_destinataire_task` dans Celery en lui transmettant l'identifiant numérique de la demande et l'URL de base du site. Si Redis/Celery ne permet pas de mettre la tâche en file, la course demeure acceptée et le livreur reçoit un message lui demandant de prévenir l'assistance ; le système ne prétend pas que le WhatsApp a été envoyé.

### Refuser

`RefuserDemandeLivraisonView` libère la demande uniquement lorsqu'elle est préassignée au livreur courant. Elle revient alors dans les demandes ouvertes du bloc. Un livreur ne peut pas retirer une attribution faite à un autre livreur.

## 4. Envoi de la notification WhatsApp

La tâche `envoyer_notification_smartdrop_destinataire_task` reçoit le `demande_id` (la clé primaire numérique), puis récupère l'objet avec l'équivalent de :

```python
DemandeLivraison.objects.get(pk=demande_id)
```

Elle construit un message contenant le numéro de course, le nom du livreur et une URL de la forme :

```text
https://<domaine-du-site>/geo/verify/<token_pwa_destinataire>/
```

Le contrôle des trois minutes est programmé avec Celery (`countdown=180`). Si `WHATSAPP_PHONE_NUMBER_ID` et `WHATSAPP_ACCESS_TOKEN` sont configurés, la tâche transmet le message à `send_whatsapp_notification_task`, qui appelle l'API WhatsApp Cloud. Les erreurs réseau, délais dépassés, réponses HTTP 429 et erreurs serveur temporaires sont réessayés selon la politique Celery configurée.

Si les identifiants WhatsApp ne sont pas configurés, le code reste en mode développement : le lien n'est pas envoyé au destinataire. La tâche d'escalade est néanmoins programmée. Pour un envoi réel, il faut configurer les identifiants WhatsApp, le broker Redis, lancer un worker Celery et utiliser l'URL publique HTTPS du site. L'API est appelée avec un message texte libre ; les règles de fenêtre de conversation ou de modèles approuvés par Meta peuvent donc s'appliquer.

## 5. Comment le token retrouve la demande

L'URL publique est branchée dans `bakam_zone/urls.py` :

```text
geo/verify/<uuid:token_pwa_destinataire>/
```

Django convertit le segment de route en UUID et le transmet à `DestinataireGeoView`. Les deux méthodes de cette vue recherchent ensuite la demande par la colonne token, et non par le `pk` :

```python
get_object_or_404(
    DemandeLivraison.objects.select_related(...),
    token_pwa_destinataire=token_pwa_destinataire,
)
```

Ainsi :

- `/geo/verify/` est la route d'accès du destinataire ;
- le UUID dans cette route est `token_pwa_destinataire` ;
- le token sélectionne l'unique ligne grâce à la contrainte `unique=True` et à l'index du modèle ;
- si le UUID ne correspond à aucune demande, Django renvoie une réponse 404.

Le destinataire n'a pas besoin de compte. Le token agit comme un secret de lien : quiconque possède l'URL peut consulter la page et transmettre une position. Il faut donc éviter de publier le lien, de le placer dans des journaux ou de le partager hors de la conversation destinée au destinataire.

**Limite actuelle :** malgré la description de « lien éphémère » dans certains commentaires, le token n'a pas de date d'expiration, n'est pas à usage unique et ne fait pas l'objet d'une rotation après utilisation. Sa seule protection est son caractère UUID imprévisible et sa confidentialité. Une expiration/révocation nécessite un mécanisme dédié avant de qualifier le lien de véritablement temporaire.

## 6. Partage et enregistrement GPS

`DestinataireGeoView.get()` affiche `destinataire_geo.html`. L'interface mobile demande l'autorisation de géolocalisation au navigateur. Au clic, Alpine.js lit `navigator.geolocation`, renseigne les champs `latitude` et `longitude` à six décimales, puis soumet le formulaire en HTMX ou en POST classique.

`DestinataireGeoView.post()` :

1. retrouve la demande avec `token_pwa_destinataire` ;
2. lit les coordonnées du formulaire ;
3. vérifie que latitude et longitude sont numériques, finies et dans les limites géographiques (`-90..90` et `-180..180`) ;
4. enregistre `latitude_destinataire_reelle`, `longitude_destinataire_reelle`, `position_destinataire_validee=True` et `statut_destinataire='position_recue'` ;
5. affiche une confirmation au destinataire.

Le tableau du livreur affiche alors l'état « Position destinataire reçue » et un lien Google Maps vers les coordonnées exactes. L'interface permet au destinataire de renvoyer sa position s'il a changé de lieu.

## 7. Délai de réponse et progression de la course

Après 180 secondes, `verifier_delai_reponse_destinataire_task` recharge la demande par son `pk`. Si aucune position n'a été validée et que le statut destinataire est encore `en_attente`, la tâche le passe à `alerte_assistant`. Si la position a été reçue, elle ne déclenche pas l'alerte.

Le livreur peut ensuite faire progresser sa course depuis son tableau de bord :

- `acceptee` → `en_cours` quand le colis est récupéré ;
- `en_cours` → `livree` lorsque le colis est remis.

La dernière transition enregistre `date_livraison` et incrémente le compteur de livraisons du livreur.

**Limite de périmètre :** l'escalade implémentée change le statut en `alerte_assistant` et est visible dans l'espace livreur. Le tableau de bord dédié de l'assistant, son appel manuel et le traitement d'un destinataire injoignable restent à développer. Le statut `injoignable` existe dans le modèle mais n'est pas encore piloté par cette tâche.

## 8. Composants concernés

- Modèle et états : `src/demande_livraison_app/models.py`
- Formulaire et validation métier : `src/demande_livraison_app/forms.py`
- Création et vue GPS destinataire : `src/demande_livraison_app/views.py`
- URL de création : `src/demande_livraison_app/urls.py`
- URL publique GPS : `src/bakam_zone/urls.py`
- Tableau de bord et actions livreur : `src/livreurs_app/views.py`, `src/livreurs_app/urls.py`
- Tâches WhatsApp et délai : `src/bakam_zone/tasks.py`
- Page GPS : `src/templates/demande_livraison_templates/destinataire_geo.html`
- Suivi dans l'espace livreur : `src/templates/livreurs_templates/livreur_dashboard.html`

## 9. Vérifications automatisées

Les tests ciblés couvrent l'affichage des demandes du bloc, l'acceptation, le refus, la protection contre une course d'un autre bloc, l'échec de mise en file Celery, le traitement des coordonnées GPS et l'appel HTTP WhatsApp simulé. Le dernier lancement documenté a réussi avec 35 tests sur `livreurs_app.tests`, `bakam_zone.tests` et `demande_livraison_app.tests`. Les tests ne valident pas un envoi réel vers Meta ni la disponibilité d'un worker/Redis de production.
