# Messagerie entre un client et l’assistant d’un bloc

## 1. L’idée, expliquée simplement

Imagine qu’un bloc est une petite agence de livraison.

- Le **client** est une personne qui a une question.
- L’**assistant du bloc** est la personne qui peut lui répondre.
- La **conversation** est le cahier dans lequel ils écrivent.
- Chaque **message** est une ligne écrite dans ce cahier.

Le client ouvre la page d’un bloc et appuie sur **« Contacter l’assistant »**.
Le site ouvre alors une conversation entre ce client et ce bloc. Le client écrit
un message, l’assistant le voit dans sa boîte de réception et peut répondre.
Les messages restent enregistrés dans la base de données, même si on ferme la
page.

> **Important :** ce n’est pas un robot d’intelligence artificielle. Le client
> parle à une personne qui possède un compte d’assistant opérationnel pour le
> bloc.

## 2. Le parcours complet

1. Un client connecté ouvre la page d’accueil ou son espace client.
2. Il choisit un bloc dans la liste. La page détail du bloc lui montre ses
   zones et ses livreurs actifs.
3. Si le bloc possède un assistant actif, le bouton **« Contacter l’assistant »**
   apparaît.
4. Le client appuie sur le bouton. Le navigateur envoie une requête `POST`
   protégée par le jeton CSRF.
5. Le serveur vérifie que le bloc est actif et qu’un assistant de ce bloc est
   actif.
6. Le serveur trouve ou crée une conversation pour cette paire
   **client + bloc**. S’il en existe déjà une, elle est réutilisée.
7. Le client arrive sur la page du chat et peut envoyer un message de
   2 000 caractères maximum.
8. L’assistant ouvre **« Messages des clients »** depuis son tableau de bord.
   Il ne voit que les conversations de son propre bloc.
9. Le client et l’assistant peuvent répondre dans la même conversation.
   Le message envoyé est enregistré avec son auteur et sa date.
10. Le fil du chat se rafraîchit automatiquement toutes les 5 secondes. La liste
    des conversations de l’assistant se rafraîchit toutes les 15 secondes.

Si aucun assistant actif n’existe pour le bloc, le client reste sur la page du
bloc et voit un message expliquant que le support n’est pas disponible.

## 3. Les objets enregistrés en base

Les modèles sont dans [`src/clients_app/models.py`](./src/clients_app/models.py).
Une migration crée leurs tables :
[`0002_supportconversation_supportmessage_and_more.py`](./src/clients_app/migrations/0002_supportconversation_supportmessage_and_more.py).

### `Client`

Le profil du client. Il est lié à un compte utilisateur Django par `user`.
La messagerie utilise ce profil pour savoir à qui appartient une conversation.

### `SupportConversation`

Représente le cahier d’échange :

| Champ | À quoi il sert |
|---|---|
| `client` | Le profil client participant. |
| `bloc` | Le bloc dont l’assistant répond. |
| `created_at` | La date de création de la conversation. |
| `updated_at` | La date de la dernière activité. Elle sert à trier la boîte de réception. |

Une contrainte unique sur `(client, bloc)` empêche de créer plusieurs
conversations de support pour le même client et le même bloc. Le modèle trie les
conversations de la plus récente à la plus ancienne.

### `SupportMessage`

Représente une ligne du cahier :

| Champ | À quoi il sert |
|---|---|
| `conversation` | La conversation à laquelle le message appartient. |
| `sender` | Le compte qui a écrit le message : client ou assistant. |
| `content` | Le texte du message, limité à 2 000 caractères. |
| `created_at` | La date et l’heure d’envoi. |

Les messages sont triés du plus ancien au plus récent pour être lus dans l’ordre.

### Relations, en une phrase

Un client peut avoir plusieurs conversations, une conversation appartient à un
bloc et à un client, et une conversation contient plusieurs messages. Chaque
message appartient à un seul utilisateur expéditeur.

## 4. Les vues : qui fait quoi ?

Les vues client se trouvent dans
[`src/clients_app/views.py`](./src/clients_app/views.py).
Les vues de l’assistant sont dans
[`src/admins_app/views.py`](./src/admins_app/views.py).

### `ClientRequiredMixin`

Avant de laisser passer, vérifie que la personne :

1. est connectée ;
2. possède le rôle `client` ;
3. possède réellement un profil `Client`.

Ce contrôle est utilisé pour le détail d’un bloc et pour démarrer une
conversation.

### `ClientBlocDetailView`

Affiche un seul bloc actif. Elle prépare également :

- les zones rattachées au bloc ;
- ses livreurs actifs ;
- la présence ou non d’un assistant actif.

Le template correspondant est
[`src/templates/clients_templates/bloc_detail.html`](./src/templates/clients_templates/bloc_detail.html).

### `StartBlocSupportChatView`

Reçoit le clic sur **« Contacter l’assistant »**. Cette action est un `POST`,
pas un simple lien `GET`, car elle peut créer une conversation.

La vue vérifie le bloc et la présence d’un assistant actif, puis utilise
`get_or_create(client=..., bloc=...)`. Cette méthode signifie : « retrouve le
cahier de ce client pour ce bloc ; s’il n’existe pas, crée-le ». Enfin, elle
redirige le client vers le chat.

### `SupportChatView`

Affiche une conversation et reçoit les messages envoyés.

- Un client ne peut ouvrir que ses propres conversations.
- Un assistant doit avoir un profil `AdminBloc` actif avec le poste
  `assistant`. Il ne peut ouvrir que les conversations de son bloc.
- Les autres rôles sont refusés.
- Le serveur choisit lui-même l’expéditeur à partir de la session connectée.
  Il ne fait pas confiance à un identifiant d’expéditeur envoyé par le
  navigateur.
- Le formulaire valide le message avant son enregistrement.
- Une requête HTMX reçoit seulement le morceau de page contenant les messages ;
  une soumission normale redirige vers le chat.

### `AssistantSupportInboxView`

Affiche la liste des conversations du bloc de l’assistant connecté. La liste
est triée par dernière activité et montre le dernier message. Elle réutilise
`AdminBlocPostDashboardView`, qui vérifie le rôle d’administrateur de bloc, le
poste attendu et l’état actif du profil.

## 5. Les routes et les pages

Les routes client sont déclarées dans
[`src/clients_app/urls.py`](./src/clients_app/urls.py), puis incluses sous le
préfixe `/clients/` dans `bakam_zone/urls.py`.

| Nom Django | URL obtenue | Fonction |
|---|---|---|
| `clients_app:detail-bloc` | `/clients/blocs/<id>/` | Détail d’un bloc pour un client. |
| `clients_app:demarrer-chat-assistant` | `/clients/blocs/<id>/support/` | Démarre ou retrouve une conversation (`POST`). |
| `clients_app:chat-assistant` | `/clients/support/conversations/<id>/` | Affiche le chat (`GET`) ou enregistre un message (`POST`). |
| `admins_app:tableau-de-bord-assistant-messages` | `/admins/tableau-de-bord/assistant/messages/` | Boîte de réception de l’assistant du bloc. |

La page complète du chat est
[`src/templates/clients_templates/support_chat.html`](./src/templates/clients_templates/support_chat.html).
Les bulles et le rafraîchissement du fil sont dans
[`src/templates/partials/clients/support_chat_messages.html`](./src/templates/partials/clients/support_chat_messages.html).
La boîte de réception et son morceau HTMX se trouvent dans
[`src/templates/admins_templates/assistant_support_inbox.html`](./src/templates/admins_templates/assistant_support_inbox.html)
et
[`src/templates/partials/admins/assistant_support_conversations.html`](./src/templates/partials/admins/assistant_support_conversations.html).

`SupportMessageForm`, dans
[`src/clients_app/forms.py`](./src/clients_app/forms.py), affiche la zone de
texte et impose une longueur maximale de 2 000 caractères.

## 6. Comment reproduire cette fonctionnalité

Voici l’ordre conseillé pour refaire le système dans une autre application
Django :

1. **Vérifier les modèles existants.** Il faut un compte utilisateur, un profil
   client, un bloc et un profil d’assistant rattaché à un bloc. Ici, l’assistant
   est un `AdminBloc` dont `poste="assistant"` et `actif=True`.
2. **Créer les modèles.** Ajouter une conversation liée au client et au bloc,
   puis des messages liés à la conversation et à l’utilisateur expéditeur.
3. **Empêcher les doublons.** Ajouter une contrainte unique sur le client et le
   bloc pour garder un seul fil de support par paire.
4. **Créer et appliquer la migration.** Depuis la racine du dépôt, avec
   l’environnement Python du projet :

   ```powershell
   .\bakam_env\Scripts\python.exe src\manage.py makemigrations clients_app
   .\bakam_env\Scripts\python.exe src\manage.py migrate
   ```

5. **Créer le formulaire de message.** Il ne doit accepter que le texte ; la vue
   ajoute elle-même la conversation et l’expéditeur.
6. **Ajouter une vue de détail du bloc** qui vérifie le profil client et
   rassemble zones, livreurs et disponibilité de l’assistant.
7. **Ajouter une vue `POST` pour démarrer le chat.** Vérifier l’assistant,
   réutiliser ou créer la conversation, puis rediriger vers son URL.
8. **Ajouter la vue de chat.** Filtrer les conversations selon le rôle :
   propriétaire pour un client, bloc de rattachement pour un assistant actif.
   Enregistrer les messages validés et rafraîchir la date d’activité.
9. **Ajouter la boîte de réception** en filtrant toujours par le bloc de
   l’assistant connecté.
10. **Créer les routes et les templates**, puis poser les liens depuis les
    endroits de l’application où le client voit les blocs.
11. **Tester les permissions et le parcours.** Vérifier qu’un client peut parler,
    qu’un assistant peut répondre, qu’un autre client ne peut pas lire le fil,
    qu’un assistant d’un autre bloc ne peut pas l’ouvrir et que les comptes
    inactifs sont refusés.

## 7. Vérifications réalisées dans ce projet

Les tests ciblés couvrent le détail du bloc, la disponibilité de l’assistant,
la création et la réutilisation de la conversation, l’échange de messages et
les restrictions d’accès. Les tests de la page d’accueil vérifient également
que les liens de détail sont visibles seulement pour les clients.

Commandes de vérification utilisées :

```powershell
.\bakam_env\Scripts\python.exe src\manage.py test clients_app.tests.ClientBlocDetailAndSupportChatTests clients_app.tests.ClientDashboardViewTests admins_app.tests.AssistantOperationnelDashboardTests
.\bakam_env\Scripts\python.exe src\manage.py test home_app.tests.HomeBlockLinksTests
.\bakam_env\Scripts\python.exe src\manage.py makemigrations --check --dry-run
.\bakam_env\Scripts\python.exe src\manage.py check
```

La messagerie utilise des requêtes HTTP périodiques HTMX. Elle ne nécessite pas
de WebSocket, mais le navigateur demande régulièrement les nouveaux messages.
