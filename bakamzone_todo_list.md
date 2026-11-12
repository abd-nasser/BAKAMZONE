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

## 7. Panier client & achats des produits des entreprises
- [ ] **Cadrage du panier et du workflow d'achat**: en cours dans [`panier_client.md`](./panier_client.md). Les règles confirmées couvrent le panier multi-entreprises, la commande unique, la position GPS au checkout avec confirmation de la zone proposée, le paiement en ligne de `total_panier()` via LigdiCash, le solde entreprise crédité après confirmation du paiement et récupérable à la demande ou en fin de mois, le choix du bloc couvrant le plus de lignes (puis le plus proche), et les demandes de livraison des entreprises vers le client pour les lignes absentes du bloc. Valider les frais, le stock entreprise, les statuts et l'accès entreprise au workflow classique avant l'implémentation.
- [ ] **Implémentation et validation du parcours d'achat**: en cours — panier HTMX/Alpine et première étape checkout implémentés : zone/GPS (repli sur les coordonnées de zone), création d'une commande en attente avec lignes/prix figés, contrôle de disponibilité/stock, détail de commande protégé. Restent à faire : réservation durable et affectation du stock/bloc, frais de livraison, paiement LigdiCash, livraisons entreprise et soldes.
