(() => {
    // 1. Configuration de la page et initialisation de la carte
    // Ces éléments sont fournis par le template. Sans eux, cette page n'affiche pas de suivi.
    const configElement = document.getElementById("delivery-tracking-config");
    const mapElement = document.getElementById("delivery-tracking-map");

    if (!configElement || !mapElement) {
        return;
    }

    const mapError = document.getElementById("delivery-map-error");
    if (!window.L) {
        if (mapError) {
            mapError.hidden = false;
            mapError.textContent = "La bibliothèque cartographique n’a pas pu être chargée.";
        }
        console.error("Leaflet n’a pas pu être chargé.");
        return;
    }

    // La configuration JSON contient notamment les livraisons à suivre, leurs libellés,
    // ainsi que le chemin WebSocket et l'URL des tuiles de carte.
    const config = JSON.parse(configElement.textContent);
    const deliveries = config.deliveries || [];
    if (!deliveries.length) {
        return;
    }

    // La carte démarre centrée sur Ouagadougou. Elle sera recentrée sur la première
    // position de livreur reçue.
    const map = L.map(mapElement).setView([12.3714, -1.5197], 12);
    const tileLayer = L.tileLayer(config.tile_url, {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    });
    tileLayer.on("tileerror", () => {
        if (mapError) {
            mapError.hidden = false;
            mapError.textContent = "Le fond de carte est indisponible ; les positions en direct continuent d’être reçues.";
        }
    });
    tileLayer.addTo(map);

    // Les Maps sont indexées par l'identifiant de livraison :
    // - markers conserve le marqueur Leaflet à déplacer à chaque nouvelle position ;
    // - states conserve l'état du WebSocket et l'heure de la dernière position reçue.
    const markers = new Map();
    const states = new Map();
    // Une position qui n'a pas été actualisée dans ce délai est signalée comme obsolète.
    const staleAfterMs = 45000;
    // La page superviseur possède un filtre et plusieurs cartes de livraison ;
    // la page client ne suit qu'une seule livraison.
    const isFleetView = document.getElementById("delivery-tracking-filter") !== null;

    // Met à jour le texte d'état et l'heure de réception dans la carte de livraison.
    function updateStatus(delivery, message, updatedAt = null) {
        const statusId = isFleetView
            ? `delivery-status-${delivery.id}`
            : "delivery-tracking-status";
        const updatedId = isFleetView
            ? `delivery-updated-${delivery.id}`
            : "delivery-tracking-updated";
        const status = document.getElementById(statusId);
        const updated = document.getElementById(updatedId);

        if (status) {
            status.textContent = message;
        }
        if (updated) {
            updated.textContent = updatedAt
                ? `Dernière position reçue : ${updatedAt.toLocaleTimeString()}`
                : "";
        }
    }

    // Sur la vue superviseur, un marqueur doit suivre la visibilité de sa carte filtrée.
    function deliveryIsVisible(deliveryId) {
        if (!isFleetView) {
            return true;
        }
        const card = document.querySelector(
            `.delivery-tracking-card[data-delivery-id="${deliveryId}"]`,
        );
        return Boolean(card && card.hidden === false);
    }

    // Change l'apparence du marqueur pour distinguer une position récente d'une ancienne.
    function setMarkerStale(deliveryId, stale) {
        const marker = markers.get(deliveryId);
        if (marker) {
            marker.setStyle({
                color: stale ? "#6b7280" : "#047857",
                fillColor: stale ? "#9ca3af" : "#059669",
                opacity: deliveryIsVisible(deliveryId) ? 1 : 0,
                fillOpacity: deliveryIsVisible(deliveryId) ? 0.9 : 0,
            });
        }
    }

    // Vérifie et affiche une position envoyée par le serveur pour cette livraison.
    // Les coordonnées et la date sont validées avant de toucher à la carte.
    function handlePosition(delivery, data) {
        if (data.type !== "position") {
            return;
        }
        const latitude = Number(data.latitude);
        const longitude = Number(data.longitude);
        const timestamp = new Date(data.timestamp);
        if (
            data.latitude === null
            || data.longitude === null
            || !Number.isFinite(latitude)
            || latitude < -90
            || latitude > 90
            || !Number.isFinite(longitude)
            || longitude < -180
            || longitude > 180
            || Number.isNaN(timestamp.getTime())
        ) {
            console.warn("Position de livraison invalide reçue.");
            return;
        }

        // Crée le marqueur lors du premier message, puis déplace le même marqueur
        // pour les messages suivants afin d'éviter d'en accumuler sur la carte.
        let marker = markers.get(delivery.id);
        if (!marker) {
            const popup = document.createElement("span");
            popup.textContent = `${delivery.label} — ${delivery.livreur || "Livreur"}`;
            marker = L.circleMarker([latitude, longitude], {
                radius: 9,
                color: "#047857",
                fillColor: "#059669",
                fillOpacity: deliveryIsVisible(delivery.id) ? 0.9 : 0,
                opacity: deliveryIsVisible(delivery.id) ? 1 : 0,
                weight: 3,
            }).bindPopup(popup).addTo(map);
            markers.set(delivery.id, marker);
            if (markers.size === 1) {
                map.setView([latitude, longitude], 15);
            }
        } else {
            marker.setLatLng([latitude, longitude]);
            setMarkerStale(delivery.id, false);
        }

        const state = states.get(delivery.id);
        if (state) {
            state.lastPositionAt = timestamp;
            state.connected = true;
        }
        updateStatus(delivery, "Position en direct reçue.", timestamp);
    }

    // 2. Connexion temps réel pour une livraison
    // Chaque livraison a son propre WebSocket et son propre état de reconnexion.
    function connect(delivery) {
        const state = {
            connected: false,
            // Le délai de reconnexion augmente progressivement en cas d'échec,
            // jusqu'à 30 secondes, afin d'éviter des tentatives trop fréquentes.
            retryDelayMs: 2000,
            socket: null,
            retryTimer: null,
            // Date de la dernière position utilisée pour déterminer si le marqueur vieillit.
            lastPositionAt: null,
        };
        states.set(delivery.id, state);

        // Ouvre le WebSocket et installe les réactions aux événements du navigateur.
        function openSocket() {
            updateStatus(delivery, "Connexion au suivi en temps réel…");
            // Utilise le même protocole que la page : ws en HTTP, wss en HTTPS.
            const url = new URL(delivery.ws_path, window.location.href);
            url.protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
            const socket = new WebSocket(url);
            state.socket = socket;

            socket.addEventListener("open", () => {
                state.connected = true;
                state.retryDelayMs = 2000;
                updateStatus(delivery, markers.has(delivery.id)
                    ? "Connecté — dernière position conservée comme obsolète, attente de la suivante."
                    : "Connecté — en attente de la première position.");
            });

            socket.addEventListener("message", (event) => {
                try {
                    handlePosition(delivery, JSON.parse(event.data));
                } catch (error) {
                    console.warn("Message de suivi illisible.", error);
                }
            });

            socket.addEventListener("close", (event) => {
                state.connected = false;
                setMarkerStale(delivery.id, true);
                // 4401/4403 signifient que le serveur refuse désormais l'accès :
                // dans ce cas, reconnecter ne ferait que répéter un refus.
                if (event.code === 4401 || event.code === 4403) {
                    updateStatus(
                        delivery,
                        "Suivi fermé — accès retiré ou livraison terminée.",
                    );
                    return;
                }
                updateStatus(
                    delivery,
                    markers.has(delivery.id)
                        ? "Connexion coupée — dernière position obsolète."
                        : "Connexion coupée — aucune position reçue.",
                );
                scheduleReconnect();
            });

            socket.addEventListener("error", () => socket.close());
        }

        // Planifie une nouvelle tentative avec un délai croissant.
        // Le contrôle du timer empêche de créer plusieurs tentatives simultanées.
        function scheduleReconnect() {
            if (state.retryTimer || !document.documentElement.isConnected) {
                return;
            }
            const delay = state.retryDelayMs;
            state.retryDelayMs = Math.min(state.retryDelayMs * 2, 30000);
            state.retryTimer = window.setTimeout(() => {
                state.retryTimer = null;
                openSocket();
            }, delay);
        }

        openSocket();
    }

    deliveries.forEach(connect);

    // 3. Filtrage des livraisons (vue superviseur)
    // Le filtre masque les cartes qui ne correspondent pas et rend aussi leurs
    // marqueurs invisibles, sans fermer leurs connexions WebSocket.
    const filter = document.getElementById("delivery-tracking-filter");
    if (filter) {
        filter.addEventListener("input", () => {
            const query = filter.value.trim().toLocaleLowerCase();
            document.querySelectorAll(".delivery-tracking-card").forEach((card) => {
                const matches = card.dataset.searchText
                    .toLocaleLowerCase()
                    .includes(query);
                card.hidden = !matches;
                const marker = markers.get(Number(card.dataset.deliveryId));
                if (marker) {
                    marker.setStyle({
                        opacity: matches ? 1 : 0,
                        fillOpacity: matches ? 0.9 : 0,
                    });
                }
            });
        });
    }

    // 4. Détection des positions devenues obsolètes
    // Le serveur peut rester connecté sans envoyer de nouvelle position ; on vérifie
    // donc périodiquement l'âge du dernier point reçu pour chaque livraison.
    window.setInterval(() => {
        const now = Date.now();
        deliveries.forEach((delivery) => {
            const state = states.get(delivery.id);
            if (!state || !state.lastPositionAt) {
                return;
            }
            const age = now - state.lastPositionAt.getTime();
            if (age <= staleAfterMs) {
                return;
            }
            setMarkerStale(delivery.id, true);
            updateStatus(
                delivery,
                `Position obsolète — dernière réception à ${state.lastPositionAt.toLocaleTimeString()}.`,
                state.lastPositionAt,
            );
        });
    }, 10000);

    window.setTimeout(() => map.invalidateSize(), 100);
})();
