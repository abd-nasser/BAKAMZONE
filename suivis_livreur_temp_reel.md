# Suivi du livreur en temps réel — BAKAMZONE

## Objectif

Permettre au client de voir sur une carte la position du livreur qui transporte sa commande, et au superviseur de flotte de suivre les courses des livreurs rattachés à son bloc. Les mises à jour arrivent régulièrement pendant la course. Le suivi commence après l'acceptation de la demande et s'arrête lorsque la livraison est terminée ou annulée.

Ce fichier décrit l'architecture cible et sert de point de reprise pour la branche `features/web_socket_livreur_deplacement`. Il distingue ce qui existe déjà de ce qui reste à développer : **le suivi temps réel par WebSocket n'est pas encore implémenté**.

## Explication simple (pour un enfant de 10 ans)

Imagine que le livreur porte une petite balise GPS :

1. Son téléphone demande la permission de connaître sa position.
2. Pendant la livraison, le téléphone envoie régulièrement sa position au serveur BAKAMZONE.
3. Le serveur vérifie que ce livreur est bien responsable de cette course.
4. Le serveur transmet la nouvelle position aux pages autorisées, sans qu'elles aient besoin d'être rechargées.
5. Le point du livreur bouge sur la carte du client et sur l'écran de supervision du bloc.
6. Quand la course est terminée, le téléphone arrête d'envoyer sa position.

Le WebSocket est comme un téléphone ouvert entre le serveur et les pages autorisées : le client suit sa livraison, et le superviseur voit les courses de la flotte de son bloc. Chacun ne reçoit que les informations nécessaires à son rôle. Redis sert de relais pour distribuer ces messages, notamment lorsque le site fonctionne avec plusieurs processus.

## État actuel du code

- `Livreur` possède déjà `latitude` et `longitude` pour conserver une position courante.
- Le modèle `PositionLivreur` existe déjà dans `livreurs_app/models.py` et sa migration initiale. Il peut conserver des points horodatés dans `historique_positions`.
- Le statut de course suit déjà les étapes `acceptee`, `en_cours`, `livree` et `annulee`.
- Le navigateur du livreur n'envoie pas encore de positions pendant la course et aucune vue ne les diffuse au client.
- `bakam_zone/asgi.py` expose actuellement le routage ASGI Django standard. Django Channels, son routage WebSocket et son consommateur restent à ajouter.
- Redis est déjà configuré comme broker Celery ; le channel layer Channels reste à configurer séparément.
- Aucune bibliothèque ou fournisseur cartographique n'est encore choisi pour afficher le trajet.

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
   - N'envoie des positions que pendant une course active qui lui est assignée.
   - Envoie des coordonnées et, si nécessaire, la précision GPS ; le serveur établit l'heure de réception.
   - Ferme le suivi à la fin ou à l'annulation de la course, à la déconnexion ou à la perte d'autorisation.

2. **Django Channels et ASGI**
   - Ajouter `channels` et `channels-redis` avec des versions compatibles avec le Django du projet.
   - Remplacer l'application ASGI standard par un routage qui combine HTTP et WebSocket.
   - Utiliser `AuthMiddlewareStack` afin que le consommateur connaisse la session utilisateur.
   - Exposer une route dédiée, par exemple `/ws/livraisons/<id>/suivi/`.

3. **Consommateur WebSocket**
   - À la connexion, refuse les utilisateurs non authentifiés et contrôle l'accès à la course.
   - Le livreur ne peut publier que pour une course qui lui est assignée et active.
   - Le client ne peut écouter que sa propre demande.
   - Un superviseur de flotte ne peut écouter que les demandes dont le livreur assigné appartient à son bloc, et seulement si son compte a `role="bloc_admin"` avec un profil `AdminBloc` actif dont `poste="superviseur_flotte"`. Le périmètre du bloc est vérifié côté serveur à l'ouverture du WebSocket et pendant la diffusion.
   - Les autres assistants et administrateurs ne reçoivent pas les positions, sauf ajout ultérieur d'une règle métier explicite.
   - Vérifie le format et les limites des coordonnées (latitude de -90 à 90, longitude de -180 à 180).
   - Enregistre la dernière position sur `Livreur.latitude` / `Livreur.longitude` et ajoute un point à `PositionLivreur` selon la politique de fréquence/rétention définie.
   - Diffuse un événement minimal, par exemple `position_livreur`, au groupe de la course, jamais à tous les utilisateurs.

4. **Redis, channel layer et déploiement**
   - Configurer `channels_redis` pour le channel layer. Prévoir une base Redis distincte de celles du broker Celery (actuellement `/0`) et du backend de résultats (actuellement `/1`), par exemple `/2`.
   - Servir le projet avec un serveur ASGI en développement et en production ; le serveur WSGI seul ne transporte pas les connexions WebSocket.
   - En production, utiliser HTTPS/WSS et configurer le proxy (Nginx) pour transmettre correctement les en-têtes `Upgrade` et `Connection`.

5. **Interface client et superviseur de flotte**
   - N'ouvre le WebSocket que pour une demande appartenant au client connecté et encore active.
   - Le tableau de bord du superviseur affiche les courses actives des livreurs de son bloc, sans exposer les courses d'autres blocs.
   - Affiche le marqueur du livreur, sa dernière mise à jour et un état explicite si les données sont anciennes ou si la connexion est perdue.
   - Se reconnecte avec temporisation raisonnable après une coupure, sans créer plusieurs connexions simultanées.
   - Choisir si les deux rôles partagent la même vue cartographique ou ont des interfaces distinctes. Le choix du fournisseur de carte reste à faire ; il ne faut pas présumer qu'une carte est déjà intégrée.

## Parcours fonctionnel

1. Le client crée une demande ; aucun suivi du livreur n'est alors diffusé.
2. Un livreur autorisé accepte la demande.
3. Lorsque la course devient active, le livreur ouvre son écran de course et autorise la géolocalisation.
4. Son téléphone envoie périodiquement la position au WebSocket de cette course.
5. Le serveur vérifie l'identité, l'assignation, le statut, le bloc et les coordonnées ; il sauvegarde puis diffuse la position.
6. Le client propriétaire voit la position de son livreur ; le superviseur actif du bloc voit les courses suivies de sa flotte. Les deux voient l'heure de mise à jour sur la carte.
7. Le suivi cesse dès que la course est `livree` ou `annulee`. Les clients non concernés ne reçoivent aucun point.
8. Si le réseau coupe, la page indique que le suivi est momentanément indisponible ; elle ne présente pas une ancienne position comme si elle était actuelle.

## Sécurité, vie privée et résilience

- Ne jamais accepter l'identifiant du livreur comme preuve d'identité : utiliser la session authentifiée et vérifier l'assignation en base.
- Vérifier l'origine et l'authentification WebSocket ; protéger chaque message reçu, pas seulement la connexion initiale.
- Ne pas diffuser les positions globalement : limiter l'accès au client propriétaire et au superviseur actif du bloc auquel le livreur est rattaché.
- Revalider le poste actif et le bloc du superviseur au moment de rejoindre le groupe ; ne jamais faire confiance à un identifiant de bloc envoyé par le navigateur.
- Collecter la position uniquement pendant une livraison active, avec l'accord du livreur. Arrêter explicitement le suivi à la fin de course.
- Limiter la cadence et la taille des messages ; ne pas créer un point historique pour chaque événement réseau sans politique de rétention.
- Gérer les autorisations GPS refusées, les coordonnées invalides, les pertes de réseau, les reconnexions et les données devenues trop anciennes.
- Documenter la durée de conservation des positions historiques et prévoir leur purge.
- Un WebSocket ne garantit pas le fonctionnement en arrière-plan sur tous les téléphones : le navigateur ou le système peut suspendre la géolocalisation. L'interface doit afficher la dernière heure connue et signaler une position obsolète.

## Checklist de réalisation

- [ ] Décider quand la course passe à l'état suivi (`acceptee` ou `en_cours`), confirmer les deux rôles lecteurs (client propriétaire et superviseur actif du bloc), et fixer la fréquence/rétention.
- [ ] Choisir et configurer le fournisseur de carte pour le tableau de bord client.
- [ ] Ajouter Channels, `channels-redis` et un serveur ASGI compatible ; configurer le channel layer Redis.
- [ ] Configurer le routage ASGI HTTP/WebSocket, les routes de suivi et l'authentification WebSocket.
- [ ] Implémenter le consommateur avec autorisation par demande : client propriétaire, superviseur actif du bloc et livreur assigné pour l'émission ; validation de coordonnées et gestion des états terminaux.
- [ ] Implémenter l'émission GPS depuis l'écran de course du livreur, avec démarrage/arrêt explicites.
- [ ] Persister la dernière position et l'historique suivant la politique décidée, puis diffuser au groupe de la course.
- [ ] Ajouter les vues cartographiques client et superviseur de flotte, l'état de connexion, l'heure de mise à jour et la reconnexion.
- [ ] Tester les droits client, superviseur du bon bloc et superviseur d'un autre bloc, la précision et cohérence des données, les courses terminées, les coupures réseau et Redis indisponible.
- [ ] Configurer le proxy et HTTPS/WSS, puis valider le parcours sur téléphones réels.

## Repères pour Agy et reprise du travail

- **Branche :** `features/web_socket_livreur_deplacement`.
- **Point de départ vérifié :** modèles de positions et coordonnées présents ; aucune diffusion temps réel ni configuration Channels en place.
- **Prochaine étape :** trancher les trois décisions métier du premier point de la checklist, puis mettre en place Channels, Redis et le routage ASGI.
- Utiliser la checklist ci-dessus comme état détaillé du travail et mettre à jour les cases au fur et à mesure. Reporter dans `parcour.md` les étapes effectivement terminées et leurs tests ; ne pas marquer comme terminé un simple choix d'architecture.
- Garder ce document à jour si les routes, les permissions, le format des événements ou la politique de rétention changent.
