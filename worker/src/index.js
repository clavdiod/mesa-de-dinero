import { asistente } from "./asistente.js";
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
const ESCRIBIBLES_WEB = new Set(["usuario/lista", "usuario/cartera", "usuario/ons", "usuario/capital", "usuario/operaciones", "usuario/decisiones_cartera"]);

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
const DIAS_SESION = 365; // y se renueva sola cada día que entrás: en la práctica no vence
const enc = new TextEncoder();
async function firmar(env, texto) {
  const k = await crypto.subtle.importKey("raw", enc.encode(`${env.INGESTA_TOKEN}|${claveWeb(env)}`),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = await crypto.subtle.sign("HMAC", k, enc.encode(texto));
  return btoa(String.fromCharCode(...new Uint8Array(sig))).replace(/[+/=]/g, (c) => ({ "+": "-", "/": "_", "=": "" }[c]));
}
function leerCookie(req, nombre) {
  const m = (req.headers.get("cookie") || "").match(new RegExp(`(?:^|; )${nombre}=([^;]+)`));
  return m ? m[1] : null;
}
// Clave de la web: WEB_CLAVE si existe; si no, la misma MESA_INGESTA_TOKEN del archivo de claves.
const claveWeb = (env) => env.WEB_CLAVE || env.INGESTA_TOKEN;

async function sesionValida(req, env) {
  if (!claveWeb(env) || !env.INGESTA_TOKEN) return false;
  const c = leerCookie(req, "mesa_sesion");
  if (!c) return false;
  const [vence, sig] = c.split(".");
  if (!vence || !sig || Number(vence) < Date.now()) return false;
  return iguales(sig, await firmar(env, vence));
}

// Si la sesión tiene más de un día, devuelve una cookie nueva por otros 365 días (renovación automática).
async function cookieSesionNueva(req, env) {
  const c = leerCookie(req, "mesa_sesion");
  if (!c || !(await sesionValida(req, env))) return null;
  const vence = Number(c.split(".")[0]);
  if (vence - Date.now() > (DIAS_SESION - 1) * 864e5) return null;
  const nuevo = String(Date.now() + DIAS_SESION * 864e5);
  return `mesa_sesion=${nuevo}.${await firmar(env, nuevo)}; Path=/; Max-Age=${DIAS_SESION * 86400}; HttpOnly; Secure; SameSite=Strict`;
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
  if (!claveWeb(env) || !intento || !iguales(String(intento).trim(), claveWeb(env))) {
    await env.MESA.put(clave, String(fallos + 1), { expirationTtl: 900 });
    return nope("Clave incorrecta", 401);
  }
  await env.MESA.delete(clave);
  const vence = String(Date.now() + DIAS_SESION * 864e5);
  const valor = `${vence}.${await firmar(env, vence)}`;
  const h = new Headers(JSON_H);
  h.append("set-cookie", `mesa_sesion=${valor}; Path=/; Max-Age=${DIAS_SESION * 86400}; HttpOnly; Secure; SameSite=Strict`);
  h.append("set-cookie", await cookieDesbloqueo(env));  // la clave completa también desbloquea
  return new Response(JSON.stringify({ ok: true }), { headers: h });
}

// ---- bloqueo con huella / cara (WebAuthn, passkey del celular) ----
// Si hay una passkey registrada, además de la sesión hace falta un "desbloqueo" que dura 10 minutos y se renueva
// solo mientras la app está abierta. Con la clave completa también se desbloquea.
const MIN_DESBLOQUEO = 10;
const b64u = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/[+/=]/g, (c) => ({ "+": "-", "/": "_", "=": "" }[c]));
const desB64u = (s) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((s.length + 3) % 4)), (c) => c.charCodeAt(0));
async function cookieDesbloqueo(env) {
  const vence = String(Date.now() + MIN_DESBLOQUEO * 60000);
  return `mesa_desbloqueo=${vence}.${await firmar(env, "desb|" + vence)}; Path=/; Max-Age=${MIN_DESBLOQUEO * 60}; HttpOnly; Secure; SameSite=Strict`;
}
async function desbloqueado(req, env) {
  if (env.MODO_LOCAL === "1" && !env.PROBAR_BLOQUEO) return true;
  const keys = await leer(env, "auth/passkeys", []);
  if (!keys.length) return true;
  const c = leerCookie(req, "mesa_desbloqueo");
  if (!c) return false;
  const [vence, sig] = c.split(".");
  return !!vence && Number(vence) > Date.now() && iguales(sig, await firmar(env, "desb|" + vence));
}
function derARaw(der) {  // firma ECDSA en DER -> r||s de 32 bytes cada uno (lo que pide WebCrypto)
  let i = 2; if (der[1] & 0x80) i += der[1] & 0x7f;
  const leerInt = () => { i++; const len = der[i++]; let v = der.slice(i, i + len); i += len;
    while (v.length > 32 && v[0] === 0) v = v.slice(1); const out = new Uint8Array(32); out.set(v, 32 - v.length); return out; };
  const r = leerInt(), s2 = leerInt(); const raw = new Uint8Array(64); raw.set(r); raw.set(s2, 32); return raw;
}
async function retoNuevo(env) {
  const r = b64u(crypto.getRandomValues(new Uint8Array(32)));
  await env.MESA.put(`auth/reto/${r}`, "1", { expirationTtl: 300 });
  return r;
}
async function retoValido(env, cd, tipo, origen) {
  if (cd.type !== tipo || cd.origin !== origen || !cd.challenge) return false;
  const k = `auth/reto/${cd.challenge}`;
  if (!(await env.MESA.get(k))) return false;
  await env.MESA.delete(k);
  return true;
}
async function passkeyApi(req, env, url, p) {
  const keys = await leer(env, "auth/passkeys", []);
  if (p === "/api/passkey/estado") return json({ activa: keys.length > 0, cantidad: keys.length });
  if (p === "/api/passkey/reto" && req.method === "POST")
    return json({ reto: await retoNuevo(env), rpId: url.hostname, ids: keys.map((k) => k.id) });
  if (p === "/api/passkey/registrar" && req.method === "POST") {
    if (keys.length && !(await desbloqueado(req, env))) return nope("bloqueada", 423);
    const b = await req.json();
    const cd = JSON.parse(new TextDecoder().decode(desB64u(b.clientDataJSON)));
    if (!(await retoValido(env, cd, "webauthn.create", url.origin))) return nope("reto inválido", 400);
    if (![-7, -257].includes(b.alg) || !b.id || !b.spki) return nope("tipo de llave no soportado", 400);
    keys.push({ id: b.id, spki: b.spki, alg: b.alg, nombre: String(b.nombre || "celular").slice(0, 40), creada: `${hoyBA()} ${horaBA()}` });
    await guardar(env, "auth/passkeys", keys);
    return new Response(JSON.stringify({ ok: true }), { headers: { ...JSON_H, "set-cookie": await cookieDesbloqueo(env) } });
  }
  if (p === "/api/passkey/verificar" && req.method === "POST") {
    const b = await req.json();
    const k = keys.find((x) => x.id === b.id);
    if (!k) return nope("llave desconocida", 400);
    const cdBytes = desB64u(b.clientDataJSON), auth = desB64u(b.authenticatorData);
    const cd = JSON.parse(new TextDecoder().decode(cdBytes));
    if (!(await retoValido(env, cd, "webauthn.get", url.origin))) return nope("reto inválido", 400);
    const rpHash = new Uint8Array(await crypto.subtle.digest("SHA-256", enc.encode(url.hostname)));
    if (!rpHash.every((v, i) => v === auth[i])) return nope("sitio inválido", 400);
    if ((auth[32] & 0x05) !== 0x05) return nope("falta la huella o la cara", 400);  // presencia + verificación del usuario
    const hashCd = new Uint8Array(await crypto.subtle.digest("SHA-256", cdBytes));
    const datos = new Uint8Array(auth.length + 32); datos.set(auth); datos.set(hashCd, auth.length);
    const ec = k.alg === -7;
    const llave = await crypto.subtle.importKey("spki", desB64u(k.spki), ec ? { name: "ECDSA", namedCurve: "P-256" } : { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
    const firma = desB64u(b.signature);
    const ok = await crypto.subtle.verify(ec ? { name: "ECDSA", hash: "SHA-256" } : "RSASSA-PKCS1-v1_5", llave, ec ? derARaw(firma) : firma, datos);
    if (!ok) return nope("no se pudo verificar", 401);
    return new Response(JSON.stringify({ ok: true }), { headers: { ...JSON_H, "set-cookie": await cookieDesbloqueo(env) } });
  }
  if (p === "/api/passkey/borrar" && req.method === "POST") {
    if (!(await desbloqueado(req, env))) return nope("bloqueada", 423);
    await guardar(env, "auth/passkeys", []);
    return json({ ok: true });
  }
  return nope("no existe", 404);
}

// Texto del aviso push (sin desbloqueo: es lo mismo que ya se ve en la pantalla bloqueada del celular)
async function textoAviso(env) {
  const [estado, alertas, props] = await Promise.all([leer(env, "ui/estado", {}), leer(env, "ui/alertas", []), leer(env, "registro/propuestas", [])]);
  const nuevas = estado.nuevas || [], p = props.find((x) => nuevas.includes(x.id)), a = alertas[0];
  const n = (x) => Number(x).toLocaleString("es-AR", { maximumFractionDigits: 2 });
  if (p) return { importante: true, titulo: `🗳️ Comité: comprar ${p.ticker} con límite ${n(p.plan.entrada)}`,
    cuerpo: `Objetivo ${n(p.plan.objetivo)} · stop ${n(p.plan.stop)}${p.ruedas ? ` · plazo ${p.ruedas} ruedas` : ""}. ${nuevas.length > 1 ? `(+${nuevas.length - 1} más) ` : ""}Entrá para ver los votos y decidir.` };
  if (a) { const imp = /salir|stop|balance|cancel/i.test(a.texto); return { importante: imp, titulo: `${imp ? "⚠️ " : ""}${a.ticker}`, cuerpo: a.texto }; }
  return { importante: false, titulo: "Mesa de dinero", cuerpo: "Hay novedades en la mesa." };
}

async function docA3(url) {
  let u;
    try { u = new URL(url.searchParams.get("u") || ""); } catch (_) { return nope("documento inválido", 400); }
    if (u.protocol !== "https:" || u.hostname !== "mercadoabierto.sharepoint.com") return nope("solo documentos de A3", 400);
    u.searchParams.set("download", "1");
    // SharePoint redirige y pide la cookie FedAuth que da en el primer paso: se siguen las redirecciones a mano con esa cookie
    let r, destino = u.toString();
    const galletas = {};
    for (let i = 0; i < 6; i++) {
      const cookie = Object.entries(galletas).map(([k, v]) => `${k}=${v}`).join("; ");
      r = await fetch(destino, { headers: { "user-agent": "Mozilla/5.0", ...(cookie ? { cookie } : {}) }, redirect: "manual" });
      const sc = r.headers.getSetCookie ? r.headers.getSetCookie() : [r.headers.get("set-cookie")].filter(Boolean);
      for (const c of sc) { const [kv] = c.split(";"); const j = kv.indexOf("="); if (j > 0) galletas[kv.slice(0, j).trim()] = kv.slice(j + 1); }
      if (![301, 302, 303, 307, 308].includes(r.status)) break;
      const loc = r.headers.get("location") || "";
      const sig = new URL(loc, destino);
      if (sig.hostname !== "mercadoabierto.sharepoint.com") return nope("A3 pidió iniciar sesión: el documento no es público", 502);
      destino = sig.toString();
    }
    if (!r.ok || !(r.headers.get("content-type") || "").includes("pdf")) return nope(`A3 no devolvió el PDF (${r.status})`, 502);
    const nombre = (url.searchParams.get("n") || "documento").replace(/[^\w .\-áéíóúñÁÉÍÓÚÑ]/g, "").slice(0, 80) || "documento";
    return new Response(r.body, { headers: { "content-type": r.headers.get("content-type") || "application/pdf",
      "content-disposition": `inline; filename="${nombre}.pdf"`, "cache-control": "private, max-age=86400" } });
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

  if (p === "/api/doc" && esActions(req, env)) return docA3(url);  // (para probar desde Actions)

  // ---- Navegador ----
  if (p === "/api/login" && req.method === "POST") return login(req, env);
  if (p === "/api/salir" && req.method === "POST") {
    const h = new Headers(JSON_H);
    h.append("set-cookie", "mesa_sesion=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Strict");
    h.append("set-cookie", "mesa_desbloqueo=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Strict");
    return new Response("{}", { headers: h });
  }
  if (!(await esUsuario(req, env))) return nope("sin acceso", 403);
  if (p.startsWith("/api/passkey/")) return passkeyApi(req, env, url, p);
  if (p === "/api/aviso") return json(await textoAviso(env));
  if (!(await desbloqueado(req, env))) return nope("bloqueada", 423);

  if (p === "/api/estado") {
    const renovar = await cookieSesionNueva(req, env);
    const [estado, cierre, alertas, consumo] = await Promise.all([
      leer(env, "ui/estado", {}), leer(env, "ui/cierre", {}), leer(env, "ui/alertas", []),
      leer(env, `consumo/${hoyBA().slice(0, 7)}`, { total: 0 }),
    ]);
    const r = json({ estado, cierre, alertas, consumo, tope: Number(env.TOPE_IOL || 25000) });
    if (renovar) r.headers.append("set-cookie", renovar);
    if ((await leer(env, "auth/passkeys", [])).length) r.headers.append("set-cookie", await cookieDesbloqueo(env));  // mientras la app está abierta no se bloquea
    return r;
  }
  // documentos públicos de A3/MAE (SharePoint): se sirven desde acá para que el celular los abra directo
  if (p === "/api/doc") return docA3(url);
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
    const [tabla, pend, params, cal, ensenanza, ensenanza_ws, ensenanza_cripto, jefe] = await Promise.all([
      leer(env, "ranking/tabla", []), leer(env, "capacitacion/pendientes", []),
      leer(env, "params/agentes", {}), leer(env, "calificadoras/historial", []), leer(env, "ranking/ensenanza", {}),
      leer(env, "ranking/ensenanza_ws", {}), leer(env, "ranking/ensenanza_cripto", {}), leer(env, "jefe/modelo", {}),
    ]);
    return json({ tabla, pendientes: pend, params, calificadoras: cal.slice(0, 30), ensenanza, ensenanza_ws, ensenanza_cripto,
      jefe: { activo: jefe.activo, motivo: jefe.motivo, prueba: jefe.prueba, aprendio: jefe.lo_que_aprendio, casos: jefe.casos } });
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
    const lote = await leer(env, `cache/lote/${t.slice(0, 1) || "_"}`, {});
    return json(lote[t] || (await leer(env, `cache/diario/${t}`, [])));
  }
  if (p === "/api/analizar" && req.method === "POST") {
    // Sin token de GitHub: se anota el pedido y la próxima ronda (≤5 min en horario de mercado) lo corre completo.
    await guardar(env, "ui/pedido_analisis", { pedido: `${hoyBA()} ${horaBA()}` });
    if (!env.GITHUB_TOKEN || !env.GITHUB_REPO)
      return json({ ok: true, modo: "proxima_ronda", mensaje: "Pedido anotado: corre en la próxima ronda (hasta 5 minutos, en horario de mercado)." });
    const r = await fetch(`https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/ronda.yml/dispatches`, {
      method: "POST",
      headers: { authorization: `Bearer ${env.GITHUB_TOKEN}`, accept: "application/vnd.github+json", "user-agent": "mesa-de-dinero" },
      body: JSON.stringify({ ref: "main", inputs: { forzar: "true" } }),
    });
    return json({ ok: true, modo: r.ok ? "inmediato" : "proxima_ronda",
      mensaje: r.ok ? "Ronda pedida: en 2-3 minutos se actualiza." : "Pedido anotado: corre en la próxima ronda." });
  }
  if (p === "/api/debate") {
    const t = (url.searchParams.get("t") || "").toUpperCase().replace(/[^A-Z0-9.]/g, "");
    const deb = await leer(env, "ui/debates", {});
    const pedido = await leer(env, "ui/pedido_debate", { tickers: [] });
    return json({ expediente: deb[t] || null, disponibles: Object.keys(deb).sort(), pedido: (pedido.tickers || []).includes(t) });
  }
  if (p === "/api/debate/pedir" && req.method === "POST") {
    const t = String((await req.json()).ticker || "").toUpperCase().replace(/[^A-Z0-9.]/g, "").slice(0, 12);
    if (!t) return nope("falta ticker", 400);
    const pedido = await leer(env, "ui/pedido_debate", { tickers: [] });
    pedido.tickers = [...new Set([t, ...(pedido.tickers || [])])].slice(0, 5);
    await guardar(env, "ui/pedido_debate", pedido);
    let inmediato = false;
    if (env.GITHUB_TOKEN && env.GITHUB_REPO) {
      const r = await fetch(`https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/ronda.yml/dispatches`, {
        method: "POST",
        headers: { authorization: `Bearer ${env.GITHUB_TOKEN}`, accept: "application/vnd.github+json", "user-agent": "mesa-de-dinero" },
        body: JSON.stringify({ ref: "main", inputs: { forzar: "true" } }),
      });
      inmediato = r.ok;
    }
    return json({ ok: true, mensaje: inmediato ? `Debate de ${t} pedido: en 2-3 minutos está listo.` : `Debate de ${t} anotado: sale en la próxima ronda.` });
  }
  if (p === "/api/simulacion") {
    const [resumen, pos] = await Promise.all([leer(env, "sim/resumen", {}), leer(env, "sim/posiciones", [])]);
    return json({ resumen, posiciones: pos.slice(0, 150) });
  }
  if (p === "/api/panel") return json(await leer(env, "ui/panel", { titulos: {} }));
  if (p === "/api/asistente/estado") return json({ activo: Boolean(env.ANTHROPIC_API_KEY) });
  if (p === "/api/asistente" && req.method === "POST") {
    const r = await asistente(req, env);
    return json(r.cuerpo, r.status);
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

// ---- Reloj propio (Cloudflare Cron): dispara los procesos de GitHub Actions ----
// Respaldo más confiable que el cron de GitHub. Requiere GITHUB_TOKEN (permiso Actions: read/write).
async function disparar(env, workflow, inputs) {
  let estado = "sin_token";
  if (env.GITHUB_TOKEN && env.GITHUB_REPO) {
    try {
      const r = await fetch(`https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/${workflow}/dispatches`, {
        method: "POST",
        headers: { authorization: `Bearer ${env.GITHUB_TOKEN}`, accept: "application/vnd.github+json", "user-agent": "mesa-de-dinero" },
        body: JSON.stringify({ ref: "main", inputs }),
      });
      estado = r.ok ? "ok" : `${r.status} ${(await r.text()).slice(0, 160)}`;
    } catch (e) { estado = `error ${e.message}`; }
  }
  // bitácora del reloj SOLO si falla (KV gratis: ~1.000 escrituras por día, no gastarlas en "todo bien")
  if (estado !== "ok") {
    const log = (await env.MESA.get("reloj/log", "json")) || [];
    log.unshift({ t: new Date().toISOString(), wf: workflow, estado });
    await env.MESA.put("reloj/log", JSON.stringify(log.slice(0, 30)));
  }
  return estado;
}

async function reloj(evento, env) {
  const d = new Date(evento.scheduledTime);
  const hm = d.getUTCHours() * 60 + d.getUTCMinutes(), dia = d.getUTCDay();
  if (dia >= 1 && dia <= 5) {
    if (hm >= 13 * 60 + 30 && hm <= 20 * 60) await disparar(env, "ronda.yml", { forzar: "false" }); // 10:30-17:00 ART
    if (hm === 13 * 60) await disparar(env, "tareas.yml", { tarea: "calificadoras" });                  // 10:00 ART
    if (hm === 20 * 60 + 10) await disparar(env, "tareas.yml", { tarea: "diario" });                    // 17:10 ART
    if (dia === 5 && hm === 20 * 60 + 30) await disparar(env, "tareas.yml", { tarea: "semanal" });      // vie 17:30
    if (dia === 5 && hm === 20 * 60 + 45) await disparar(env, "tareas.yml", { tarea: "entrenar" });     // vie 17:45: re-entrena con la historia
  }
  if (d.getUTCDate() <= 3 && hm === 21 * 60) await disparar(env, "tareas.yml", { tarea: "mensual" });
}

export default {
  async scheduled(evento, env, ctx) {
    ctx.waitUntil(reloj(evento, env));
  },
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
