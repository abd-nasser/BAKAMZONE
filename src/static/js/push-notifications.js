(() => {
  const button = document.getElementById("pwa-push-button");
  const status = document.getElementById("pwa-push-status");
  if (!button || !status) return;

  const report = (message) => {
    status.textContent = message;
  };

  const decodeApplicationServerKey = (key) => {
    const padding = "=".repeat((4 - (key.length % 4)) % 4);
    const base64 = (key + padding).replace(/-/g, "+").replace(/_/g, "/");
    return Uint8Array.from(atob(base64), (character) => character.charCodeAt(0));
  };

  const saveSubscription = async (subscription) => {
    const response = await fetch("/notifications/pwa/subscribe/", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": button.dataset.csrfToken,
      },
      body: JSON.stringify(subscription.toJSON()),
    });

    if (!response.ok) {
      const result = await response.json();
      throw new Error(result.error || "Impossible d'enregistrer cet appareil.");
    }
  };

  const enableNotifications = async () => {
    if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) {
      throw new Error("Les notifications Push ne sont pas prises en charge par ce navigateur.");
    }

    const registration = await navigator.serviceWorker.register("/sw.js", { scope: "/" });
    let subscription = await registration.pushManager.getSubscription();
    let applicationServerKey;

    if (!subscription) {
      const keyResponse = await fetch("/notifications/pwa/vapid-key/", {
        credentials: "same-origin",
      });
      const keyResult = await keyResponse.json();
      if (!keyResponse.ok || !keyResult.public_key) {
        throw new Error(keyResult.error || "La clé publique Push n'est pas configurée.");
      }
      applicationServerKey = decodeApplicationServerKey(keyResult.public_key);
    }

    if (Notification.permission === "denied") {
      throw new Error("Les notifications sont bloquées dans les réglages du navigateur.");
    }
    if (Notification.permission !== "granted") {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        throw new Error("L'autorisation d'envoyer des notifications a été refusée.");
      }
    }

    if (!subscription) {
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey,
      });
    }

    await saveSubscription(subscription);
    button.textContent = "Notifications activées";
    report("Les notifications sont activées sur cet appareil.");
  };

  button.addEventListener("click", async () => {
    button.disabled = true;
    report("Activation des notifications en cours…");
    try {
      await enableNotifications();
    } catch (error) {
      report(error.message || "Impossible d'activer les notifications.");
    } finally {
      button.disabled = false;
    }
  });

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch((error) => {
      report(`Service worker indisponible : ${error.message}`);
    });
  }
})();
