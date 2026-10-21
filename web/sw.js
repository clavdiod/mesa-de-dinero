// Service worker: recibe el aviso (sin contenido) y pide al Worker qué hay de nuevo.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("push", (event) => {
  event.waitUntil((async () => {
    let titulo = "Mesa de dinero", cuerpo = "Hay novedades en la mesa.";
    let importante = false;
    try {
      const [r, rp] = await Promise.all([fetch("/api/estado", { credentials: "include" }), fetch("/api/propuestas", { credentials: "include" })]);
      const d = await r.json(), props = await rp.json();
      const nuevas = d.estado?.nuevas || [];
      const alerta = (d.alertas || [])[0];
      const p = (props || []).find((x) => nuevas.includes(x.id));
      const n = (x) => Number(x).toLocaleString("es-AR", { maximumFractionDigits: 2 });
      if (p) {
        importante = true;
        titulo = `🔔 Comprar ${p.ticker} con límite ${n(p.plan.entrada)}`;
        cuerpo = `Objetivo ${n(p.plan.objetivo)} · stop ${n(p.plan.stop)}${p.cantidad_sugerida ? ` · ${p.cantidad_sugerida} unidades` : ""}. ` +
                 `${nuevas.length > 1 ? `(+${nuevas.length - 1} más) ` : ""}Entrá para ver el debate y decidir.`;
      } else if (alerta) {
        importante = /salir|stop|balance|cancel/i.test(alerta.texto);
        titulo = `${importante ? "⚠️ " : ""}${alerta.ticker}`; cuerpo = alerta.texto;
      }
    } catch (_) { /* sin sesión: aviso genérico */ }
    await self.registration.showNotification(titulo, { body: cuerpo, icon: "icono-192.png", badge: "icono-192.png", tag: "mesa",
      renotify: true, requireInteraction: importante, vibrate: [200, 100, 200] });
  })());
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(self.clients.matchAll({ type: "window" }).then((ws) => (ws[0] ? ws[0].focus() : self.clients.openWindow("/"))));
});
