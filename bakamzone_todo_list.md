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
