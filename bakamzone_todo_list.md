# BAKAMZONE - Delivery Workflow & Smart-Drop Implementation Plan

## 1. Form & Client Views (`DemandeLivraison`)
- [x] **Django Form (`DemandeLivraisonForm`)**: Build form capturing arrival zone selection, package description, and recipient's WhatsApp number.
- [x] **Client Request Template (`creer_demande.html`)**: Implement Alpine.js geolocation trigger button to dynamically capture and populate `latitude_depart` and `longitude_depart` from the user's mobile browser.
- [x] **Automated Pricing Engine**: Implement Matrix Zone-to-Zone fare calculation (`zone_depart` -> `zone_arrivee`) during request creation.

## 2. WhatsApp Smart-Drop & Recipient PWA Flow
- [ ] **Ephemeral PWA Endpoint (`DestinataireGeoView`)**: Create secure public-facing view mapped to `/geo/verify/<uuid:token_pwa_destinataire>/` (no auth required).
- [ ] **Mobile-First Geolocation Interface (`destinataire_geo.html`)**: Design lightweight interface with a single-click GPS capture button updating `latitude_destinataire_reelle` and `longitude_destinataire_reelle`.
- [ ] **WhatsApp Notification Task (Celery)**: Dispatch initial WhatsApp message containing the PWA link upon driver order acceptance.

## 3. Asynchronous Escalation & Celery Worker
- [ ] **Timeout Monitor (`verifier_delai_reponse_destinataire`)**: Schedule a 3-minute delayed task to check if `position_destinataire_validee` is set to `True`.
- [ ] **Automatic Escalation Logic**: Transition `statut_destinataire` to `'alerte_assistant'` if the recipient fails to provide location within the 3-minute window.

## 4. Bloc Assistant Dashboard (`bloc_admin`)
- [ ] **Bloc Admin Dashboard View & Template**: Real-time HTMX-powered panel displaying active regional deliveries and pending alerts.
- [ ] **Assistant Manual Resolution Tooling**: Interfaces enabling human operators to trigger direct manual calls, update recipient positions, or flag recipients as unreachable.
