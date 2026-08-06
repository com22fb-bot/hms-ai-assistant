self.addEventListener("push", (event) => {
  let payload = {
    title: "HMS AI Assistant",
    body: "Tienes un nuevo aviso.",
    url: "/",
  };

  try {
    if (event.data) {
      payload = { ...payload, ...event.data.json() };
    }
  } catch {
    if (event.data) payload.body = event.data.text();
  }

  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      icon: "/hms-import-robot.png",
      badge: "/hms-import-robot.png",
      tag: payload.notificationId || payload.type || "hms-notification",
      renotify: true,
      data: { url: payload.url || "/" },
      actions: [{ action: "open", title: "Abrir HMS" }],
    }),
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
