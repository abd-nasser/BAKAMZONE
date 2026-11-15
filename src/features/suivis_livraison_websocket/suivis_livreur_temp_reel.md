# Suivi du livreur en temps réel — BAKAMZONE

## Objectif

Permettre au client de voir sur une carte la position du livreur qui transporte sa commande, et au superviseur de flotte de suivre les courses des livreurs rattachés à son bloc. Les mises à jour arrivent régulièrement pendant la course. Le suivi démarre lorsque les coordonnées validées du destinataire sont disponibles au livreur assigné et s'arrête lorsque la livraison est terminée ou annulée.

Ce fichier décrit l'architecture et sert de point de reprise pour la branche `features/web_socket_livreur_deplacement`. Les fondations Channels, le partage GPS volontaire du livreur, la persistance à cadence limitée, la purge planifiée et les interfaces de suivi client/superviseur sont en place ; les tests intégrés et la validation terrain restent à effectuer.

## Explication simple (pour un enfant de 10 ans)

Imagine que le livreur porte une petite balise GPS :

1. Son téléphone demande la permission de connaître sa position.
2. Pendant la livraison, le téléphone envoie régulièrement sa position au serveur BAKAMZONE.
3. Le serveur vérifie que ce livreur est bien responsable de cette course.
4. Le serveur transmet la nouvelle position aux pages autorisées, sans qu'elles aient besoin d'être rechargées.
5. Le point du livreur bouge sur la carte du client et sur l'écran de supervision du bloc.
6. Dès que les coordonnées du destinataire sont disponibles au livreur assigné, le client reçoit une notification. Le suivi est alors activé ; la collecte GPS commence lorsque le livreur ouvre sa course et autorise la géolocalisation.
7. Quand la livraison est terminée ou annulée, le téléphone arrête d'envoyer sa position.

Le WebSocket est comme un téléphone ouvert entre le serveur et les pages autorisées : le client suit sa livraison, et le superviseur voit les courses de la flotte de son bloc. Chacun ne reçoit que les informations nécessaires à son rôle. Redis sert de relais pour distribuer ces messages, notamment lorsque le site fonctionne avec plusieurs processus.

## État actuel du code

- `Livreur` possède `latitude`, `longitude` et `position_suivi_mise_a_jour` pour conserver la position courante et appliquer la limite d'émission côté serveur.
- Le modèle `PositionLivreur` existe déjà dans `livreurs_app/models.py` et sa migration initiale. Il peut conserver des points horodatés dans `historique_positions`.
- Le serveur vérifie les coordonnées GPS, l'assignation, le statut de la course et la cadence avant d'enregistrer ou de diffuser une position.
- Le statut de course suit déjà les étapes `acceptee`, `en_cours`, `livree` et `annulee`.
- Le tableau de bord livreur permet de démarrer et d'arrêter volontairement le partage GPS ; le navigateur et le serveur limitent les émissions à une position au plus toutes les 15 secondes.
- À la première validation de la position du destinataire, le système programme une Web Push pour le client ; une actualisation ultérieure des coordonnées ne programme pas de notification supplémentaire.
- Le consumer enregistre la dernière position et un point historique au plus toutes les 60 secondes, puis diffuse l'événement au groupe privé de la course. Une tâche Celery Beat purge chaque jour à 02:00 UTC les points âgés de plus de 7 jours.
- Django Channels, `channels-redis` et Daphne sont ajoutés aux dépendances. `bakam_zone/asgi.py` expose l'application HTTP Django et le routage WebSocket protégé par l'authentification de session et une liste d'origines explicite.
- Redis est déjà configuré pour Celery (bases `/0` et `/1`) ; le channel layer Channels utilise `CHANNEL_REDIS_URL` ou, par défaut, Redis sur `/2`. Un Redis local doit fonctionner pour valider des échanges WebSocket réels.
- Le client suit une livraison depuis sa page de détail, accessible uniquement au propriétaire. Le superviseur dispose d'une carte multi-courses et d'un filtre texte ; le serveur ne transmet que les courses actives de son bloc dont le suivi GPS est activé.
- Les cartes n'affichent pas de position initiale provenant du profil du livreur : le marqueur n'apparaît qu'à la réception d'un point sur le WebSocket de cette course. Après 45 secondes sans nouveau point, ou après une coupure, la dernière position est signalée comme obsolète et le navigateur tente une reconnexion.
- Leaflet est chargé depuis jsDelivr et l'URL des tuiles est configurable avec `OPENSTREETMAP_TILE_URL`. La valeur par défaut utilise les tuiles publiques OpenStreetMap pour le développement ; la cible de production reste le service de tuiles auto-hébergé sur le KVM 4.
- La cible d'hébergement retenue est le KVM 4 (4 vCPU, 16 Go RAM, 200 Go NVMe, 16 To de bande passante mensuelle), à la place du KVM 2 qui est écarté. La souscription/migration est reportée jusqu'à ce que la feature soit prête pour les tests de production. Les tuiles OSM régionales seront préparées en phase de mise en production ; cette dépendance n'empêche pas le développement WebSocket local.

## Architecture cible

```text
Téléphone du livreur
  └─ Géolocalisation du navigateur (permission explicite)
       └─ WebSocket sécurisé : position + identifiant de course
            └─ ASGI → AuthMiddlewareStack → route WebSocket
                 └─ Consumer Django Channels
                      ├─ vérifie l'utilisateur, le rôle et le périmètre autorisé
                      ├─ valide et enregistre la position
                      └─ publie dans le groupe de cette course via Redis
                           ├─ WebSocket du client propriétaire de la demande
                           └─ WebSocket du superviseur actif du bloc concerné
                                └─ met à jour le marqueur et l'heure sur la carte
```

### Composants

1. **Navigateur du livreur**
   - Utilise l'API Geolocation du navigateur (par exemple `watchPosition`) après accord du livreur.
   - N'envoie des positions que pendant une course active qui lui est assignée et après que les coordonnées validées du destinataire sont disponibles au livreur.
   - Envoie la position au plus toutes les 15 secondes ; la géolocalisation mobile reste soumise à l'autorisation et aux capacités du navigateur.
   - Envoie actuellement la latitude et la longitude ; le message n'accepte pas d'autres champs et le serveur établit l'heure de réception.
   - Ferme le suivi à la fin ou à l'annulation de la course, à la déconnexion ou à la perte d'autorisation.

2. **Django Channels et ASGI**
   - `channels`, `channels-redis` et Daphne sont ajoutés avec des versions épinglées compatibles avec le projet.
   - L'application ASGI combine HTTP et WebSocket ; le routage WebSocket est enregistré dans `bakam_zone/routing.py`.
   - Utiliser `AuthMiddlewareStack` afin que le consommateur connaisse la session utilisateur, avec une validation par les origines explicites de `WEBSOCKET_ALLOWED_ORIGINS`.
   - Route dédiée implémentée : `/ws/livraisons/<int:demande_id>/suivi/`.

3. **Consommateur WebSocket**
   - À la connexion, refuse les utilisateurs non authentifiés et contrôle l'accès à la course.
   - Le livreur ne peut publier que pour une course qui lui est assignée et active, après validation des coordonnées du destinataire.
   - Le client ne peut écouter que sa propre demande.
   - Un superviseur de flotte ne peut écouter que les demandes dont le livreur assigné appartient à son bloc, et seulement si son compte a `role="bloc_admin"` avec un profil `AdminBloc` actif dont `poste="superviseur_flotte"`. Le périmètre du bloc est vérifié côté serveur à l'ouverture du WebSocket et pendant la diffusion.
   - Les autres assistants et administrateurs ne reçoivent pas les positions, sauf ajout ultérieur d'une règle métier explicite.
   - Vérifie le type de message et les limites des coordonnées (latitude de -90 à 90, longitude de -180 à 180), puis applique une limite serveur de 15 secondes.
   - Enregistre la dernière position sur `Livreur.latitude` / `Livreur.longitude` et son heure de réception.
   - Ajoute au plus un point à `PositionLivreur` toutes les 60 secondes ; `livreurs_app.tasks.purger_historique_positions_task` supprime chaque jour les points plus anciens que 7 jours.
   - Diffuse un événement minimal `position` au groupe de la course, jamais à tous les utilisateurs.
   - Format du message entrant : `{"type":"position","latitude":12.3,"longitude":-1.5}` ; l'heure diffusée est celle du serveur, pas une heure fournie par le navigateur.

   5. **Interfaces cartographiques**
      - La page de suivi client est accessible uniquement au propriétaire de la demande et n'ouvre le WebSocket que pour une course active, un livreur actif et des coordonnées de destinataire validées.
      - Le tableau superviseur réunit les courses GPS actives du bloc associé à son compte ; le filtre recherche le livreur, le client et les zones.
      - Le navigateur affiche l'heure fournie par le serveur, marque la position comme obsolète après 45 secondes sans nouvelle donnée et tente une reconnexion avec délai progressif.
      - Aucun point sauvegardé sur le profil du livreur n'est utilisé au chargement : une position antérieure à la course ou à la connexion n'est jamais présentée comme actuelle.
      - Le service de tuiles public sert uniquement de valeur de développement configurable ; avant la production, configurer `OPENSTREETMAP_TILE_URL` vers le service régional auto-hébergé et tenir compte des conditions d'utilisation des tuiles OpenStreetMap.

4. **Redis, channel layer et déploiement**
   - Le channel layer `channels_redis` lit `CHANNEL_REDIS_URL` ; sa valeur locale par défaut utilise Redis `/2`, séparé du broker Celery (`/0`) et du backend de résultats (`/1`).
   - Daphne est le serveur ASGI retenu. Redis et Daphne doivent être démarrés pour les tests de connexion réels ; le serveur WSGI seul ne transporte pas les connexions WebSocket.
   - En production, utiliser HTTPS/WSS et configurer le proxy (Nginx) pour transmettre correctement les en-têtes `Upgrade` et `Connection`.

5. **Interface client et superviseur de flotte**
   - N'ouvre le WebSocket que pour une demande appartenant au client connecté et encore active.
   - Le tableau de bord du superviseur affiche les courses actives des livreurs de son bloc, sans exposer les courses d'autres blocs.
   - Affiche le marqueur du livreur, sa dernière mise à jour et un état explicite si les données sont anciennes ou si la connexion est perdue.
   - Se reconnecte avec temporisation raisonnable après une coupure, sans créer plusieurs connexions simultanées.
   - Utiliser Leaflet pour afficher une cartographie basée sur OpenStreetMap.
   - La carte client suit uniquement sa livraison active, avec position du livreur et heure de dernière mise à jour.
   - La carte du superviseur affiche plusieurs courses actives des livreurs de son bloc, avec liste et filtres ; sélectionner un élément de la liste permet de centrer la carte sur le livreur correspondant.
   - Les deux vues affichent l'état hors ligne/obsolète et n'exposent jamais des courses d'un autre bloc ou client.
   - En phase de mise en production, auto-héberger les tuiles OSM pour Ouagadougou et ses environs sur le KVM 4 retenu (4 vCPU, 16 Go RAM, 200 Go NVMe, 16 To de bande passante mensuelle), et ne pas utiliser le KVM 2 pour cette cible.
   - Après souscription/migration, mesurer l'espace disque libre et la mémoire disponible avec Django, Redis et les autres services avant de dimensionner les données et le serveur de tuiles. Ne pas supposer que les ressources totales du VPS sont entièrement disponibles pour la cartographie.
   - Choisir une stack de serveur de tuiles et un format de données régionaux compatibles avec Leaflet ; le serveur public de tuiles OSM n'est pas utilisé comme solution de production. Ce travail est différé et ne bloque pas le développement WebSocket.

## Parcours fonctionnel

1. Le client crée une demande ; aucun suivi du livreur n'est alors diffusé.
2. Un livreur autorisé accepte la demande.
3. Le destinataire transmet ses coordonnées GPS par la PWA ou l'assistant les saisit après validation.
4. Quand ces coordonnées sont validées et disponibles au livreur assigné, le système avertit le client par Web Push (si un abonnement actif existe) et active le suivi. La collecte GPS démarre lorsque le livreur ouvre sa course et autorise la géolocalisation. La notification est déclenchée à la mise à disposition des coordonnées, jamais à chaque mise à jour GPS.
5. Le livreur ouvre l'écran de course et autorise la géolocalisation ; son téléphone envoie sa position au plus toutes les 15 secondes.
6. Le serveur vérifie l'identité, l'assignation, le statut, le bloc et les coordonnées ; il met à jour la position courante et diffuse les mises à jour.
7. Un point historique est conservé toutes les 60 secondes au plus ; les points âgés de plus de 7 jours sont purgés automatiquement.
8. Le client propriétaire voit la position de son livreur ; le superviseur actif du bloc voit les courses suivies de sa flotte. Les deux voient l'heure de mise à jour sur la carte.
9. Le suivi cesse dès que la course est `livree` ou `annulee`. Les clients non concernés ne reçoivent aucun point.
10. Si le réseau coupe, la page indique que le suivi est momentanément indisponible ; elle ne présente pas une ancienne position comme si elle était actuelle.

## Décisions métier retenues

- **Cartographie :** Leaflet avec des tuiles OpenStreetMap auto-hébergées.
- **Couverture initiale :** Ouagadougou et environs pour le pilote ; ne pas importer le monde entier.
- **Hébergement visé :** KVM 4 pour Django/Nginx et le service de tuiles, annoncé à 4 vCPU, 16 Go RAM, 200 Go NVMe et 16 To de bande passante mensuelle ; le KVM 2 est écarté. La souscription ou migration est reportée jusqu'à la préparation des tests de production. Mesurer les ressources libres après déploiement.
- **Vue client :** une carte limitée à la livraison active du client, montrant le livreur et l'heure de sa dernière position.
- **Vue superviseur :** une carte multi-courses limitée aux livreurs de son bloc, avec une liste et des filtres pour sélectionner une course.
- **Déclencheur :** coordonnées GPS du destinataire validées et rendues disponibles au livreur assigné, sur une demande active. Le suivi ne démarre donc pas automatiquement au simple moment de l'acceptation.
- **Notification client :** programmer une Web Push indiquant que les coordonnées de localisation du destinataire sont disponibles pour le livreur assigné. Elle est déclenchée à leur mise à disposition et ne dépend pas d'un accusé de réception manuel du livreur ; l'envoi effectif nécessite un abonnement Push actif. Les mises à jour GPS ne déclenchent pas de nouvelles notifications.
- **Lecteurs autorisés :** client propriétaire de la demande et superviseur de flotte actif du bloc du livreur.
- **Arrêt :** dès que la course passe à `livree` ou `annulee`, ou que le livreur n'est plus assigné à la course.
- **Cadence :** position transmise au plus toutes les 15 secondes ; un point d'historique enregistré toutes les 60 secondes au plus.
- **Rétention :** purge automatique des points de `PositionLivreur` de plus de 7 jours.

## Sécurité, vie privée et résilience

- Ne jamais accepter l'identifiant du livreur comme preuve d'identité : utiliser la session authentifiée et vérifier l'assignation en base.
- Vérifier l'origine et l'authentification WebSocket ; protéger chaque message reçu, pas seulement la connexion initiale.
- Ne pas diffuser les positions globalement : limiter l'accès au client propriétaire et au superviseur actif du bloc auquel le livreur est rattaché.
- Revalider le poste actif et le bloc du superviseur au moment de rejoindre le groupe ; ne jamais faire confiance à un identifiant de bloc envoyé par le navigateur.
- Collecter la position uniquement pendant une livraison active, avec l'accord du livreur. Arrêter explicitement le suivi à la fin de course.
- Limiter la cadence à une position au plus toutes les 15 secondes et l'historique à un point toutes les 60 secondes ; ne pas créer un point historique pour chaque événement réseau.
- Gérer les autorisations GPS refusées, les coordonnées invalides, les pertes de réseau, les reconnexions et les données devenues trop anciennes.
- Purger automatiquement les positions historiques âgées de plus de 7 jours.
- Un WebSocket ne garantit pas le fonctionnement en arrière-plan sur tous les téléphones : le navigateur ou le système peut suspendre la géolocalisation. L'interface doit afficher la dernière heure connue et signaler une position obsolète.

## Checklist de réalisation

- [x] Cadrage métier et vie privée : le suivi est activé lorsque les coordonnées GPS validées du destinataire sont disponibles au livreur assigné ; la collecte commence lorsque le livreur ouvre sa course et autorise la géolocalisation. Le client reçoit une Web Push à la mise à disposition ; arrêt à livraison/annulation ou désassignation. Le client propriétaire et le superviseur actif du bloc sont autorisés. Cadence GPS maximale 15 s, historique toutes les 60 s au plus, purge après 7 jours.
- [x] Choix de la cartographie et des vues : Leaflet + OpenStreetMap ; vue client limitée à sa livraison active ; vue superviseur multi-courses avec liste/filtres pour son bloc.
- [x] Choix d'hébergement cartographique : tuiles OSM auto-hébergées pour Ouagadougou et environs sur le KVM 4 ; KVM 2 écarté.
- [x] Caractéristiques nominales annoncées de la cible : 4 vCPU, 16 Go RAM, 200 Go NVMe, 16 To de bande passante mensuelle.
- [ ] Production cartographique (différée) : après souscription/migration, mesurer les ressources libres (RAM/disque et charge CPU), puis sélectionner/configurer la stack régionale de tuiles et tester le rendu/chargement. Non bloquant pour le développement local.
- [x] Dépendances et infrastructure Channels : `channels==4.3.2`, `channels-redis==4.3.0`, `daphne==4.2.3` ; application ASGI HTTP/WebSocket, authentification de session, origines explicites via `WEBSOCKET_ALLOWED_ORIGINS` ; channel layer Redis `/2` par défaut, configurable par `CHANNEL_REDIS_URL`.
- [x] Route et autorisations WebSocket : connexion réservée au livreur actif assigné, au client propriétaire et au superviseur actif du bloc ; courses acceptées/en cours uniquement, après validation des coordonnées du destinataire.
- [x] Ajouter le démarrage/arrêt explicite du partage GPS côté livreur ; envoi depuis le navigateur et limitation serveur à un point toutes les 15 secondes au plus.
- [x] Programmer une Web Push au client à la première validation des coordonnées du destinataire ; ne pas répéter lors d'une actualisation ultérieure.
- [x] Valider les messages entrants, vérifier le livreur assigné et l'état actif, enregistrer la position courante, historiser au plus une fois par minute et diffuser au groupe privé de la course.
- [x] Purger automatiquement les points `PositionLivreur` âgés de plus de 7 jours par Celery Beat ; le processus Beat doit être actif en production.
- [x] Ajouter les vues cartographiques client et superviseur de flotte, l'état de connexion, l'heure de mise à jour, les états obsolètes et la reconnexion.
- [x] Tests ciblés locaux après la migration du renommage : 49 tests de livraison, client et superviseur, puis 7 tests du workflow livreur réussis. Couverture des droits, des positions invalides, des courses terminées et de la révocation d'un superviseur.
- [ ] Tester les échanges avec Redis/Daphne réels, les coupures et reconnexions réseau, le proxy HTTPS/WSS et des téléphones réels.

## Repères pour Agy et reprise du travail

- **Branche :** `features/web_socket_livreur_deplacement`.
- **État :** fondations ASGI/Channels, contrôle d'accès, partage GPS volontaire côté livreur, validation et diffusion par course, position courante et historique à cadence limitée, purge quotidienne de rétention et interfaces client/superviseur en place. Les tests ciblés locaux passent ; la validation d'infrastructure et de terrain reste à faire.
- **Décisions cadrées :** déclenchement lorsque les coordonnées du destinataire sont validées et disponibles au livreur, notification Web Push au client, lecteurs limités au client propriétaire et au superviseur actif du bloc, arrêt à livraison/annulation/désassignation, émission toutes les 15 s, historique toutes les 60 s et purge après 7 jours.
- **Prochaine étape :** tester les échanges derrière Redis/Daphne et HTTPS/WSS, puis valider le parcours sur téléphones. La migration de renommage `statut_destinataire` vers `statut_position_destinataire` est appliquée et les anciennes références applicatives ont été alignées. Pour activer la purge planifiée, démarrer Celery Beat (`celery -A bakam_zone beat`) en plus du worker ; la souscription au KVM 4 et les tuiles OSM auto-hébergées restent reportées jusqu'à la préparation des tests de production.
- Utiliser la checklist ci-dessus comme état détaillé du travail et mettre à jour les cases au fur et à mesure. Reporter dans `parcour.md` les étapes effectivement terminées et leurs tests ; ne pas marquer comme terminé un simple choix d'architecture.
- Garder ce document à jour si les routes, les permissions, le format des événements ou la politique de rétention changent.
