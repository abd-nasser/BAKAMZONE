(() => {
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

    const config = JSON.parse(configElement.textContent);
    const deliveries = config.deliveries || [];
    if (!deliveries.length) {
        return;
    }

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

    const markers = new Map();
    const states = new Map();
    const staleAfterMs = 45000;
    const isFleetView = document.getElementById("delivery-tracking-filter") !== null;

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

    function deliveryIsVisible(deliveryId) {
        if (!isFleetView) {
            return true;
        }
        const card = document.querySelector(
            `.delivery-tracking-card[data-delivery-id="${deliveryId}"]`,
        );
        return Boolean(card && card.hidden === false);
    }

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

    function connect(delivery) {
        const state = {
            connected: false,
            retryDelayMs: 2000,
            socket: null,
            retryTimer: null,
        };
        states.set(delivery.id, state);

        function openSocket() {
            updateStatus(delivery, "Connexion au suivi en temps réel…");
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
