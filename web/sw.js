// Service worker: recibe el aviso (sin contenido) y pide al Worker qué hay de nuevo.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("push", (event) => {
  event.waitUntil((async () => {
    let titulo = "Mesa de dinero", cuerpo = "Hay novedades en la mesa.";
    let importante = false, tag = "mesa", silencioso = false;
    try {
      const a = await (await fetch("/api/aviso", { credentials: "include" })).json();
      if (a.titulo) { titulo = a.titulo; cuerpo = a.cuerpo; importante = !!a.importante; tag = a.tag || "mesa"; silencioso = !!a.silencioso; }
    } catch (_) { /* sin sesión: aviso genérico */ }
    // 17/11: el parte "sin cambios" de cada ronda no suena ni vibra y reemplaza al anterior (no se apilan)
    await self.registration.showNotification(titulo, { body: cuerpo, icon: "icono-192.png", badge: "icono-192.png", tag,
      renotify: !silencioso, silent: silencioso, requireInteraction: importante, ...(silencioso ? {} : { vibrate: [200, 100, 200] }) });
  })());
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(self.clients.matchAll({ type: "window" }).then((ws) => (ws[0] ? ws[0].focus() : self.clients.openWindow("/"))));
});

// 19/11: si el navegador renueva o da de baja la suscripción, se pide una nueva y se registra sola (sin abrir la app)
self.addEventListener("pushsubscriptionchange", (event) => {
  event.waitUntil((async () => {
    try {
      const { clave } = await (await fetch("/api/push/clave", { credentials: "include" })).json();
      const pad = "=".repeat((4 - (clave.length % 4)) % 4), raw = atob((clave + pad).replace(/-/g, "+").replace(/_/g, "/"));
      const sub = await self.registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: Uint8Array.from(raw, (c) => c.charCodeAt(0)) });
      await fetch("/api/push/suscribir", { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(sub.toJSON()) });
    } catch (_) { /* se reintenta al abrir la app */ }
  })());
});
