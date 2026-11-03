# Architecture du Système de Notifications PWA — BAKAMZONE

Ce document détaille l'architecture complète, le fonctionnement et la mise en œuvre des notifications Push sur mobile pour la PWA BAKAMZONE (en particulier pour la messagerie entre un client et l'assistant d'un bloc).

---

## 1. L'explication pour un enfant de 10 ans 🧒🎈

> *Imagine que ton téléphone est une petite maison fermée à clé, et que tu es tranquillement en train de dormir ou de jouer à un jeu.*

1. **Le gardien secret (Le Service Worker)** :
   Devant ta maison, il y a un petit gardien très discret mais infatigable. Même quand ta maison est éteinte et que la porte est fermée à double tour, ce gardien reste assis sur le paillasson et écoute.

2. **L'adresse et le cadenas magique (L'abonnement Push & VAPID)** :
   Le premier jour, le gardien donne à la poste une adresse spéciale pour ta maison, ainsi qu'un cadenas magique en deux morceaux. Le quartier général de BAKAMZONE garde la clé secrète. Personne d'autre ne peut envoyer de lettres sous le nom de BAKAMZONE car seule leur clé correspond au cadenas !

3. **Le nouveau message** :
   Quand le client ou l'assistant écrit un message, le quartier général prépare une petite lettre, la verrouille avec le cadenas magique, et la donne au grand facteur d'Internet (les serveurs de Google pour Android ou d'Apple pour iPhone).

4. **La sonnette (La notification native)** :
   Le facteur court déposer la lettre au petit gardien sur le paillasson. Le gardien vérifie que c'est bien BAKAMZONE, puis il appuie sur la sonnette de la maison : **« Ding Dong ! 🔔 Vous avez reçu un message de l'assistant de Tampouy ! »**. L'écran du téléphone s'allume avec la bannière et le son.

5. **Le clic magique** :
   Dès que tu touches la notification avec ton doigt, le gardien ouvre immédiatement la porte pile sur la page de la conversation avec la bonne personne !

---

## 2. Guide technique pour Développeurs & Copilote IA 💻🤖

### Vue d'ensemble de l'architecture

Le système repose sur le standard officiel W3C **Web Push API** combiné au protocole **VAPID** (*Voluntary Application Server Identification* - RFC 8292). Il s'exécute de façon totalement découplée grâce à des workers asynchrones Celery.

```text
[ Client / Assistant ]
         │ (Écrit un message)
         ▼
[ SupportChatView.post() ] ──> Enregistre SupportMessage en Base
         │
         ▼ (Non-bloquant)
[ Celery Task: envoyer_notification_webpush_task.delay() ]
         │
         ├──> Récupère les abonnements WebPushSubscription du destinataire
         ├──> Prépare le payload JSON chiffré (AES-128-GCM) avec pywebpush & VAPID
         └──> Requête HTTPS vers le Push Service (ex: fcm.googleapis.com ou push.apple.com)
                                    │
                                    ▼
                     [ Mobile OS Notification Service ]
                                    │
                                    ▼
                     [ Service Worker (sw.js) : push event ]
                                    │
                                    ▼
                     [ self.registration.showNotification() ]
                                    │ (Clic de l'utilisateur)
                                    ▼
                     [ clients.openWindow(conversation_url) ]
```

---

### A. Les composants clés

#### 1. Manifest PWA (`manifest.json`)
* Déclare la configuration de l'application web installable :
  * `name`, `short_name`: "BAKAMZONE"
  * `start_url`: "/"
  * `display`: `"standalone"` (obligatoire pour masquer l'interface du navigateur)
  * `theme_color`: `"#059669"` (Émeraude BAKAMZONE)
  * `background_color`: `"#FFFFFF"`
  * `icons`: 192x192 et 512x512 PNG avec propriété `purpose: "any maskable"`.
* **Important pour iOS** : Safari sur iPhone (iOS 16.4+) exige impérativement que la PWA soit ajoutée à l'écran d'accueil (`standalone`) pour activer les Web Push Notifications.

#### 2. Le Service Worker (`sw.js`)
* Fichier JavaScript servi avec le bon scope (ex: `/sw.js` ou servi via une vue Django dédiée pour être à la racine `/`).
* Écoute deux événements essentiels :
  * `push` : reçoit le payload chiffré, le désérialise en JSON et déclenche `self.registration.showNotification(title, options)`.
  * `notificationclick` : intercepte le clic sur la bannière système, ferme la notification et navigue vers l'URL fournie (`event.notification.data.url`).

#### 3. Le Modèle Django `WebPushSubscription`
Stocké dans une application Django dédiée (ex: `notifications_app` ou rattaché aux utilisateurs) :
* `user`: Clé étrangère vers `settings.AUTH_USER_MODEL` (un utilisateur peut posséder plusieurs appareils : mobile pro, tablette, etc.).
* `endpoint`: URL absolue unique fournie par le service push du navigateur.
* `p256dh`: Clé publique de chiffrement du client (clé d'échange Diffie-Hellman P-256).
* `auth`: Secret d'authentification partagé.
* `created_at` / `updated_at`: Horodatages de création et de rafraîchissement.

#### 4. Clés VAPID (Sécurité & Authentification du serveur)
* Paire de clés cryptographiques asymétriques :
  * `VAPID_PUBLIC_KEY`: transmise au navigateur client pour initialiser la souscription via `pushManager.subscribe()`.
  * `VAPID_PRIVATE_KEY`: conservée secrète côté Django (`settings.py` / `.env`).
  * `VAPID_CLAIMS`: dictionnaire contenant au minimum `"sub": "mailto:support@bakamzone.com"`.

#### 5. Tâche Celery d'envoi (`envoyer_notification_webpush_task`)
* Reçoit l'identifiant du destinataire (`user_id`), le titre, le message, et l'URL cible.
* Interroge les `WebPushSubscription` de l'utilisateur.
* Pour chaque abonnement, appelle `pywebpush.webpush()` avec gestion des erreurs :
  * Si le serveur distant renvoie un code **HTTP 410 (Gone)** ou **404 (Not Found)**, cela signifie que l'utilisateur a désinstallé la PWA ou révoqué la permission : l'abonnement obsolète est alors automatiquement supprimé de la base de données.
  * Si une erreur réseau temporaire survient, relance automatique avec backoff Celery.

---

### B. Intégration dans le flux Support Chat

Dans [`src/clients_app/views.py`](file:///D:/SAAS_PROJECT/BAKAMZONE/src/clients_app/views.py), au sein de la méthode `post()` de `SupportChatView` :

1. Enregistrement classique du `SupportMessage`.
2. Mise en file de la tâche :
   ```python
   notifier_nouveau_message_support_task.delay(message.pk)
   ```
3. Cette tâche choisit les destinataires selon l'auteur :
   * Si l'auteur est le **client**, chaque assistant actif du bloc est notifié.
   * Si l'auteur est l'**assistant**, le client de la conversation est notifié.
4. La tâche d'envoi lit les abonnements actifs du destinataire, construit le payload et le signe avec la clé privée VAPID :
   ```python
   envoyer_notification_webpush_task.delay(
       user_id=destinataire_user_id,
       title=titre,
       body=apercu_texte,
       target_url=chat_url,
   )
   ```
   `destinataire_user_id`, `apercu_texte` et `chat_url` représentent les valeurs calculées par la tâche à partir du message.
5. Si le broker Celery est indisponible pendant l'envoi du message, le message reste enregistré et l'échec de mise en file est journalisé.

Routes actuelles : `GET /sw.js`, `POST /notifications/pwa/subscribe/`,
`POST /notifications/pwa/unsubscribe/` et `GET /notifications/pwa/vapid-key/`.
L'inscription et la suppression exigent une session authentifiée et un jeton CSRF.

---

### C. Gestion des cas particuliers et compatibilité mobile

| Plateforme | Comportement & Exigences |
|---|---|
| **Android (Chrome, Edge, Firefox, Brave)** | Fonctionne directement dans le navigateur ou une fois la PWA installée. |
| **iOS / iPadOS (Safari 16.4+)** | Nécessite que l'utilisateur installe la PWA sur son écran d'accueil (« Partager » > « Sur l'écran d'accueil »). Les Web Push sont inactives dans les onglets classiques Safari sur iPhone. |
| **Sécurité (HTTPS)** | Le protocole HTTPS est **strictement obligatoire** pour l'enregistrement du Service Worker et l'API Push, à l'exception du développement local (`localhost` / `127.0.0.1`). |
| **Fallback WhatsApp** | En cas d'absence d'abonnement Push actif ou de délai de lecture prolongé, le système peut utiliser la tâche existante `send_whatsapp_notification_task` pour avertir l'utilisateur sur son numéro WhatsApp. |

---

### D. Checklist pour Copilot / Développeur

- [x] Déclarer `pywebpush` dans `requirements.txt`.
- [x] Créer `notifications_app`, son modèle et sa migration.
- [x] Lire les clés VAPID `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` et `VAPID_ADMIN_EMAIL` depuis l'environnement.
- [x] Créer les routes d'inscription, de désinscription et de lecture de la clé publique VAPID.
- [x] Créer la tâche Celery d'envoi et supprimer les abonnements qui répondent HTTP 404 ou 410.
- [x] Déclarer le manifeste, les icônes, le service worker racine et le prompt d'activation dans `base.html`.
- [x] Déclencher les notifications de messagerie client/assistant.
- [ ] Configurer les clés VAPID, Redis/Celery et HTTPS puis valider un envoi sur un appareil réel.

L'installation de `pywebpush` n'a pas pu être faite dans l'environnement de développement
actuel, qui utilise une build free-threaded de Python 3.13 non prise en charge par la
dépendance CFFI/Cryptography. Installer les dépendances dans un environnement CPython
standard avant de démarrer le worker ou de tester l'envoi réel.
