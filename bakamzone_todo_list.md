# BAKAMZONE - Delivery Workflow & Smart-Drop Implementation Plan

## 1. Form & Client Views (`DemandeLivraison`)
- [x] **Django Form (`DemandeLivraisonForm`)**: Build form capturing arrival zone selection, package description, and recipient's WhatsApp number.
- [x] **Client Request Template (`creer_demande.html`)**: Implement Alpine.js geolocation trigger button to dynamically capture and populate `latitude_depart` and `longitude_depart` from the user's mobile browser.
- [x] **Automated Pricing Engine**: Implement Matrix Zone-to-Zone fare calculation (`zone_depart` -> `zone_arrivee`) during request creation.

## 2. WhatsApp Smart-Drop & Recipient PWA Flow
- [x] **Recipient PWA Endpoint (`DestinataireGeoView`)**: Public UUID route `/geo/verify/<uuid:token_pwa_destinataire>/` resolves the request and accepts validated GPS coordinates without login. The token currently has no expiry.
- [x] **Mobile-First Geolocation Interface (`destinataire_geo.html`)**: Single-click browser GPS capture saves `latitude_destinataire_reelle` and `longitude_destinataire_reelle`.
- [x] **WhatsApp Notification Task (Celery)**: Queue the Smart-Drop link after a driver accepts a delivery. A real send requires Meta credentials, Redis/Celery and a public HTTPS site URL.

## 3. Asynchronous Escalation & Celery Worker
- [x] **Timeout Monitor (`verifier_delai_reponse_destinataire_task`)**: Schedule a 3-minute delayed task to check if `position_destinataire_validee` is set to `True`.
- [x] **Automatic Escalation Logic**: Transition `statut_destinataire` to `'alerte_assistant'` if the recipient fails to provide location within the 3-minute window.

## 4. Bloc Assistant Dashboard (`bloc_admin`)
- [x] **Bloc Admin Dashboard View & Template**: HTMX-refreshing panel displaying active deliveries involving the assistant's block and pending recipient alerts.
- [x] **Assistant Manual Resolution Tooling**: Direct phone-call link, validated manual GPS entry, and action to flag alerted recipients as unreachable.

## 5. Client Bloc Detail & Support Chat
- [x] **Client Bloc Detail View**: Authenticated clients can inspect an active bloc's zones and active delivery drivers, with links to driver profiles.
- [x] **Homepage Bloc Links**: Bloc cards link to their detail page for client accounts only; visitors and other roles keep the existing presentation.
- [x] **Persistent Bloc Support Chat**: Clients can open one conversation per bloc with its active operational assistant; messages are stored and refreshed through HTMX.
- [x] **Assistant Support Inbox**: Active assistants can list conversations for their own bloc and reply; conversation access is restricted to that client and the bloc's active assistant.
- [x] **Validation**: Targeted client, assistant, and homepage tests pass; Django system checks and migration checks pass. The full suite still reports three unrelated `entreprise_app` URL reversal errors for `entreprise_app:detail`.

## 6. Notifications Push PWA & Messagerie Support
- [x] **Manifest PWA & Service Worker**: `manifest.json`, icônes PNG, service worker racine (`/sw.js`) avec gestion des événements `push` et `notificationclick`, et activation explicite des notifications depuis le template maître.
- [x] **Modèle Django de Souscription WebPush**: Modèle et migration des abonnements (`endpoint`, `p256dh`, `auth`, `user`), avec API authentifiée d'inscription/suppression et endpoint public de clé VAPID.
- [x] **Tâche Celery & Déclenchement Asynchrone**: Envoi Web Push VAPID depuis le flux de messagerie, suppression des abonnements HTTP 410/404 et signalement des erreurs de configuration ou d'envoi.
- [x] **Validation**: 20 tests ciblés de notifications et de messagerie réussis ; `manage.py check`, `makemigrations --check --dry-run`, vérification syntaxique JavaScript et `git diff --check` réussis. L'envoi réel reste à vérifier avec les clés VAPID, un broker Celery et un navigateur/appareil HTTPS configurés.

## 7. Suivi du livreur en temps réel (Django Channels & WebSocket)
- [x] **Fondations déjà présentes**: coordonnées courantes `Livreur.latitude` / `longitude` et modèle historique `PositionLivreur` avec migration.
- [x] **Cadrage métier et vie privée**: suivi activé lorsque les coordonnées GPS validées du destinataire sont disponibles au livreur assigné ; collecte GPS après ouverture de la course et accord du livreur. Web Push au client à la mise à disposition, sans notification à chaque point GPS. Arrêt à livraison, annulation ou désassignation. Accès réservé au client propriétaire et au superviseur de flotte actif du bloc. Position envoyée toutes les 15 s au plus, historique toutes les 60 s au plus, purge des positions historiques après 7 jours.
- [x] **Décision cartographique et UX**: Leaflet avec cartographie OpenStreetMap ; carte client limitée à sa livraison active ; vue superviseur multi-courses du bloc avec liste et filtres.
- [x] **Choix d'hébergement des tuiles**: auto-héberger les tuiles OpenStreetMap pour Ouagadougou et ses environs sur le KVM 4 ; le KVM 2 est écarté.
- [x] **Caractéristiques nominales de la cible relevées**: KVM 4 avec 4 vCPU, 16 Go RAM, 200 Go NVMe et 16 To de bande passante mensuelle.
- [ ] **Tuiles cartographiques (phase de mise en production)**: après choix de la date de souscription au KVM 4, mesurer les ressources libres, choisir/configurer la stack OSM régionale et tester le service. Cette tâche ne bloque pas le développement WebSocket local.
- [x] **Dépendances et infrastructure Channels**: ajouter Django Channels, channels-redis et Daphne ; configurer le channel layer Redis sur la base `/2` et exposer une application ASGI avec authentification de session et validation d'origine. Le service Redis local doit être lancé pour tester les connexions réelles.
- [x] **Routes et permissions WebSocket de suivi**: ajouter les consumers/URL de suivi et limiter le livreur à sa course active, chaque client à ses propres demandes, et le superviseur actif (`role="bloc_admin"` / `poste="superviseur_flotte"`) aux courses de son bloc.
- [x] **Émission de position côté livreur**: à la première validation des coordonnées du destinataire, programmer une Web Push au client une seule fois ; le livreur démarre le GPS explicitement et transmet sa position au plus toutes les 15 s pendant une course active.
- [x] **Consommateur, historique et diffusion**: le serveur valide les coordonnées et le livreur émetteur, met à jour la position courante, conserve au plus un point historique toutes les 60 s et diffuse uniquement au groupe de la course.
- [x] **Purge de l'historique GPS**: tâche Celery Beat quotidienne à 02:00 UTC pour supprimer les positions de plus de 7 jours ; le service Celery Beat doit tourner en plus du worker.
- [x] **Interfaces de suivi client et superviseur**: Leaflet sur le détail d'une livraison côté client et carte multi-courses du bloc côté superviseur ; WebSocket, horodatage, reconnexion, état obsolète et filtre de liste.
- [x] **Tests ciblés locaux**: migration de renommage appliquée ; tests de livraison, tableau client, tableau superviseur et flux livreur (56 tests) passés, avec couverture des permissions WebSocket, coordonnées invalides, courses terminées et révocation du superviseur.
- [ ] **Validation d'infrastructure et terrain**: tester avec Redis/Daphne réels, coupures et reconnexions réseau, proxy HTTPS/WSS et téléphones. La vérification locale ne remplace pas ces essais de déploiement.
- **Hébergement de production**: KVM 4 retenu comme cible, KVM 2 écarté ; souscription/migration reportée jusqu'à ce que le développement de la feature soit prêt pour les tests de production.
- Référence d'architecture, parcours, sécurité et état initial: [`suivis_livreur_temp_reel.md`](./suivis_livreur_temp_reel.md).
