// Worker de la mesa: sirve la web y guarda los datos privados en Cloudflare KV.
//
// Seguridad:
// - Navegador: clave propia (secreto WEB_CLAVE) → cookie firmada por 30 días, con bloqueo tras 5 intentos.
//   (Si se activa Cloudflare Access, también acepta el email de EMAIL_PERMITIDO.)
// - /api/kv/* (GitHub Actions) exige el token secreto INGESTA_TOKEN.
// - Sin sesión, la API no devuelve ningún dato.

const JSON_H = { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" };
const json = (d, s = 200) => new Response(JSON.stringify(d), { status: s, headers: JSON_H });
const nope = (m, s = 403) => json({ error: m }, s);

// Claves que la web puede escribir (todo lo demás es de solo lectura para el navegador)
const ESCRIBIBLES_WEB = new Set(["usuario/lista", "usuario/cartera", "usuario/ons", "usuario/capital"]);

function iguales(a, b) {
  if (!a || !b || a.length !== b.length) return false;
  let r = 0;
  for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}

function esActions(req, env) {
  const h = req.headers.get("authorization") || "";
  return iguales(h, `Bearer ${env.INGESTA_TOKEN}`);
}

// ---- sesión propia (sin Cloudflare Access): clave WEB_CLAVE + cookie firmada ----
const DIAS_SESION = 30;
const enc = new TextEncoder();
async function firmar(env, texto) {
  const k = await crypto.subtle.importKey("raw", enc.encode(`${env.INGESTA_TOKEN}|${env.WEB_CLAVE}`),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", k, enc.encode(texto));
  return btoa(String.fromCharCode(...new Uint8Array(sig))).replace(/[+/=]/g, (c) => ({ "+": "-", "/": "_", "=": "" }[c]));
}
function leerCookie(req, nombre) {
  const m = (req.headers.get("cookie") || "").match(new RegExp(`(?:^|; )${nombre}=([^;]+)`));
  return m ? m[1] : null;
}
async function sesionValida(req, env) {
  if (!env.WEB_CLAVE || !env.INGESTA_TOKEN) return false;
  const c = leerCookie(req, "mesa_sesion");
  if (!c) return false;
  const [vence, sig] = c.split(".");
  if (!vence || !sig || Number(vence) < Date.now()) return false;
  return iguales(sig, await firmar(env, vence));
}

async function esUsuario(req, env) {
  if (env.MODO_LOCAL === "1") return true; // solo para probar con `wrangler dev`
  // Opción A: Cloudflare Access (si algún día se activa)
  const email = (req.headers.get("cf-access-authenticated-user-email") || "").toLowerCase();
  const permitidos = (env.EMAIL_PERMITIDO || "").toLowerCase().split(",").map((s) => s.trim()).filter(Boolean);
  if (email && permitidos.includes(email)) return true;
  // Opción B: clave propia
  return sesionValida(req, env);
}

async function login(req, env) {
  const ip = req.headers.get("cf-connecting-ip") || "x";
  const clave = `seg/fallos/${ip}`;
  const fallos = Number((await env.MESA.get(clave)) || 0);
  if (fallos >= 5) return nope("Demasiados intentos. Probá en 15 minutos.", 429);
  const { clave: intento } = await req.json().catch(() => ({}));
  if (!env.WEB_CLAVE || !intento || !iguales(String(intento), env.WEB_CLAVE)) {
    await env.MESA.put(clave, String(fallos + 1), { expirationTtl: 900 });
    return nope("Clave incorrecta", 401);
  }
  await env.MESA.delete(clave);
  const vence = String(Date.now() + DIAS_SESION * 864e5);
  const valor = `${vence}.${await firmar(env, vence)}`;
  return new Response(JSON.stringify({ ok: true }), { headers: { ...JSON_H,
    "set-cookie": `mesa_sesion=${valor}; Path=/; Max-Age=${DIAS_SESION * 86400}; HttpOnly; Secure; SameSite=Strict` } });
}

const leer = async (env, k, d = null) => (await env.MESA.get(k, "json")) ?? d;
const guardar = (env, k, v) => env.MESA.put(k, JSON.stringify(v));

function hoyBA() {
  return new Date().toLocaleDateString("en-CA", { timeZone: "America/Argentina/Buenos_Aires" });
}
function horaBA() {
  return new Date().toLocaleTimeString("es-AR", { timeZone: "America/Argentina/Buenos_Aires", hour: "2-digit", minute: "2-digit" });
}

async function api(req, env, url) {
  const p = url.pathname;

  // ---- GitHub Actions (token secreto) ----
  if (p.startsWith("/api/kv/") || p.startsWith("/api/kv-lista/")) {
    if (!esActions(req, env)) return nope("token inválido", 401);
    if (p.startsWith("/api/kv-lista/")) {
      const pref = decodeURIComponent(p.slice("/api/kv-lista/".length));
      const out = [];
      let cursor;
      do {
        const r = await env.MESA.list({ prefix: pref, cursor });
        out.push(...r.keys.map((k) => k.name));
        cursor = r.list_complete ? null : r.cursor;
      } while (cursor);
      return json(out);
    }
    const clave = decodeURIComponent(p.slice("/api/kv/".length));
    if (req.method === "GET") {
      const v = await env.MESA.get(clave);
      return v === null ? nope("no existe", 404) : new Response(v, { headers: JSON_H });
    }
    if (req.method === "PUT") {
      await env.MESA.put(clave, await req.text());
      return json({ ok: true });
    }
    return nope("método no permitido", 405);
  }

  // ---- Navegador ----
  if (p === "/api/login" && req.method === "POST") return login(req, env);
  if (p === "/api/salir" && req.method === "POST")
    return new Response("{}", { headers: { ...JSON_H, "set-cookie": "mesa_sesion=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Strict" } });
  if (!(await esUsuario(req, env))) return nope("sin acceso", 403);

  if (p === "/api/estado") {
    const [estado, cierre, alertas, consumo] = await Promise.all([
      leer(env, "ui/estado", {}), leer(env, "ui/cierre", {}), leer(env, "ui/alertas", []),
      leer(env, `consumo/${hoyBA().slice(0, 7)}`, { total: 0 }),
    ]);
    return json({ estado, cierre, alertas, consumo, tope: Number(env.TOPE_IOL || 25000) });
  }
  if (p === "/api/propuestas") {
    const [props, dec] = await Promise.all([leer(env, "registro/propuestas", []), leer(env, "usuario/decisiones", {})]);
    for (const x of props) if (dec[x.id]) x.decision = dec[x.id].decision;
    return json(props.slice(0, 200));
  }
  if (p === "/api/decision" && req.method === "POST") {
    const { id, decision } = await req.json();
    if (!id || !["aprobada", "rechazada"].includes(decision)) return nope("datos inválidos", 400);
    const dec = await leer(env, "usuario/decisiones", {});
    dec[id] = { decision, hora: `${hoyBA()} ${horaBA()}` };
    await guardar(env, "usuario/decisiones", dec);
    return json({ ok: true });
  }
  if (p.startsWith("/api/usuario/")) {
    const clave = "usuario/" + p.slice("/api/usuario/".length);
    if (req.method === "GET") return json(await leer(env, clave, clave.endsWith("capital") ? {} : clave.endsWith("ons") ? {} : []));
    if (req.method === "PUT" && ESCRIBIBLES_WEB.has(clave)) {
      const body = await req.text();
      if (body.length > 200000) return nope("demasiado grande", 413);
      JSON.parse(body); // valida
      await env.MESA.put(clave, body);
      return json({ ok: true });
    }
    return nope("no permitido", 405);
  }
  if (p === "/api/ranking") {
    const [tabla, pend, params, cal] = await Promise.all([
      leer(env, "ranking/tabla", []), leer(env, "capacitacion/pendientes", []),
      leer(env, "params/agentes", {}), leer(env, "calificadoras/historial", []),
    ]);
    return json({ tabla, pendientes: pend, params, calificadoras: cal.slice(0, 30) });
  }
  if (p === "/api/capacitacion" && req.method === "POST") {
    const { agente, aprobar } = await req.json();
    const pend = await leer(env, "capacitacion/pendientes", []);
    const item = pend.find((x) => x.agente === agente && x.estado === "pendiente");
    if (!item) return nope("no hay cambio pendiente", 404);
    item.estado = aprobar ? "aprobado" : "rechazado";
    if (aprobar) {
      const params = await leer(env, "params/agentes", {});
      params[agente] = { ...(params[agente] || {}), ...item.despues };
      await guardar(env, "params/agentes", params);
    }
    await guardar(env, "capacitacion/pendientes", pend);
    return json({ ok: true });
  }
  if (p === "/api/historico") {
    const t = (url.searchParams.get("t") || "").toUpperCase().replace(/[^A-Z0-9.]/g, "");
    return json(await leer(env, `cache/diario/${t}`, []));
  }
  if (p === "/api/analizar" && req.method === "POST") {
    if (!env.GITHUB_TOKEN || !env.GITHUB_REPO) return nope("falta configurar GITHUB_TOKEN/GITHUB_REPO", 501);
    const r = await fetch(`https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/ronda.yml/dispatches`, {
      method: "POST",
      headers: { authorization: `Bearer ${env.GITHUB_TOKEN}`, accept: "application/vnd.github+json", "user-agent": "mesa-de-dinero" },
      body: JSON.stringify({ ref: "main", inputs: { forzar: "true" } }),
    });
    return r.ok ? json({ ok: true }) : nope(`GitHub respondió ${r.status}`, 502);
  }
  if (p === "/api/push/clave") return json({ clave: env.VAPID_PUBLICA || null });
  if (p === "/api/push/suscribir" && req.method === "POST") {
    const sub = await req.json();
    if (!sub?.endpoint?.startsWith("https://")) return nope("suscripción inválida", 400);
    const subs = await leer(env, "push/suscripciones", []);
    if (!subs.some((s) => s.endpoint === sub.endpoint)) subs.push({ endpoint: sub.endpoint, alta: hoyBA() });
    await guardar(env, "push/suscripciones", subs.slice(-10));
    return json({ ok: true });
  }
  return nope("no encontrado", 404);
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (url.pathname.startsWith("/api/")) {
      try {
        return await api(req, env, url);
      } catch (e) {
        return nope(`error: ${e.message}`, 500);
      }
    }
    return env.ASSETS.fetch(req);
  },
};
