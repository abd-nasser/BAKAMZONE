# Architecture & Implémentation du Suivi de Livraison (BAKAMZONE)

## 1. Infrastructure & Moteur Temps Réel
- **Django Channels & ASGI**
  - Basculement du serveur synchrone WSGI vers l'asynchrone ASGI
  - Routage des WebSockets (`/ws/livraisons/<id>/suivi/`)
- **Memurai (v8.2.10) sous Windows**
  - Remplacement de l'ancien Redis 3.0 (résolution de l'erreur `BZPOPMIN`)
  - Configuration du Channel Layer (`channels_redis.core.RedisChannelLayer`) sur le port `6379`

## 2. Sécurité & Logique Métier (Backend Django)
- **Modèle de données (`DemandeLivraison`)**
  - Workflow *Smart-Drop* via WhatsApp
  - Génération d'un token PWA unique (`token_pwa_destinataire`)
- **Double sécurité d'accès (`_get_access_role`)**
  - Contrôle strict des rôles lors du handshake (`connect`)
  - Filtrage des permissions lors de la diffusion au groupe
- **Condition "Traçable"**
  - Statut de course actif (`acceptee`, `en_cours`)
  - Validation obligatoire des coordonnées GPS du destinataire

## 3. Flux de Données & Data Mechanics (End-to-End)
- **Livreur vers Serveur**
  - API native de géolocalisation (`navigator.geolocation.watchPosition`)
  - Transmission des coordonnées au format `Decimal`
  - Throttling de 15 secondes (côté client et serveur) pour économiser la bande passante
- **Serveur vers Superviseur (Pub/Sub)**
  - Réception dans le Consumer (`receive_json`) et sauvegarde en base de données
  - Diffusion instantanée via `group_send` dans le groupe Redis (`livraison_<id>`)

## 4. Front-End & Expérience Utilisateur (PWA / Leaflet)
- **Injection Sécurisée (`json_script`)**
  - Passage de la configuration (`tracking_config`) via `<script type="application/json">`
  - Protection native contre les failles XSS
- **Cartographie Interactive (Leaflet.js)**
  - Affichage dynamique des marqueurs de la flotte (`isFleetView`)
  - Mise à jour fluide en temps réel sans rechargement de page (*no-refresh*)
- **Résilience & Gestion des coupures**
  - Reconnexion automatique avec *exponential backoff*
  - Marquage visuel de l'état obsolète (*stale*) en cas de perte de signal

## 5. Automatisation & Maintenance (Celery)
- **Tâches de fond (Celery & Celery Beat)**
  - Tâche périodique (`nettoyer_anciens_historiques_task`)
  - Planification hebdomadaire (`crontab`) pour purger les positions de plus de 7 jours