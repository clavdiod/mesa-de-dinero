// Service worker: recibe el aviso (sin contenido) y pide al Worker qué hay de nuevo.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("push", (event) => {
  event.waitUntil((async () => {
    let titulo = "Mesa de dinero", cuerpo = "Hay novedades en la mesa.";
    let importante = false;
    try {
      const a = await (await fetch("/api/aviso", { credentials: "include" })).json();
      if (a.titulo) { titulo = a.titulo; cuerpo = a.cuerpo; importante = !!a.importante; }
    } catch (_) { /* sin sesión: aviso genérico */ }
    await self.registration.showNotification(titulo, { body: cuerpo, icon: "icono-192.png", badge: "icono-192.png", tag: "mesa",
      renotify: true, requireInteraction: importante, vibrate: [200, 100, 200] });
  })());
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(self.clients.matchAll({ type: "window" }).then((ws) => (ws[0] ? ws[0].focus() : self.clients.openWindow("/"))));
});
