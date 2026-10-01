self.addEventListener("push", (event) => {
  let payload = {
    title: "Donexto",
    body: "Nueva alerta de Donexto",
    url: "/",
    lang: "es",
    vibrate: [80, 40, 80, 40, 160],
  };

  try {
    if (event.data) {
      payload = { ...payload, ...event.data.json() };
    }
  } catch {
    if (event.data) payload.body = event.data.text();
  }

  const options = {
    body: payload.body,
    icon: "/brand/donexto-3d-2026.png",
    badge: "/brand/donexto-3d-2026.png",
    tag: payload.notificationId || payload.type || "donexto-alert",
    renotify: true,
    lang: payload.lang || "es",
    data: { url: payload.url || "/", lang: payload.lang || "es" },
    vibrate: Array.isArray(payload.vibrate) ? payload.vibrate : [80, 40, 80, 40, 160],
    actions: [{ action: "open", title: "Abrir Donexto" }],
  };

  event.waitUntil(
    (async () => {
      await self.registration.showNotification(payload.title || "Donexto", options);
      const windows = await clients.matchAll({
        type: "window",
        includeUncontrolled: true,
      });
      for (const client of windows) {
        client.postMessage({
          type: "donexto-alert",
          title: payload.title,
          body: payload.body,
          lang: payload.lang || "es",
        });
      }
    })(),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = new URL(event.notification.data?.url || "/", self.location.origin).href;

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
      for (const client of windows) {
        if (client.url.startsWith(self.location.origin) && "focus" in client) {
          client.navigate(target);
          return client.focus();
        }
      }
      return clients.openWindow ? clients.openWindow(target) : undefined;
    }),
  );
});
