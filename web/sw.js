// Service worker: recibe el aviso (sin contenido) y pide al Worker qué hay de nuevo.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("push", (event) => {
  event.waitUntil((async () => {
    let titulo = "Mesa de dinero", cuerpo = "Hay novedades en la mesa.";
    try {
      const r = await fetch("/api/estado", { credentials: "include" });
      const d = await r.json();
      const nuevas = d.estado?.nuevas || [];
      const alerta = (d.alertas || [])[0];
      if (nuevas.length) { titulo = `${nuevas.length} propuesta(s) para aprobar`; cuerpo = "Entrá para ver el plan y el debate."; }
      else if (alerta) { titulo = `Alerta: ${alerta.ticker}`; cuerpo = alerta.texto; }
    } catch (_) { /* sin sesión de Access: aviso genérico */ }
    await self.registration.showNotification(titulo, { body: cuerpo, icon: "icono-192.png", badge: "icono-192.png", tag: "mesa" });
  })());
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(self.clients.matchAll({ type: "window" }).then((ws) => (ws[0] ? ws[0].focus() : self.clients.openWindow("/"))));
});
