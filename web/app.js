"use strict";
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (x, d = 2) => (x === null || x === undefined || isNaN(x) ? "—" : Number(x).toLocaleString("es-AR", { minimumFractionDigits: d, maximumFractionDigits: d }));
const pct = (x, d = 2) => (x === null || x === undefined ? "—" : `${x > 0 ? "+" : ""}${num(x, d)}%`);
const NOMBRES = { acciones: "Acciones", cedears: "CEDEARs", ons: "ONs", soberanos: "Soberanos", pesos_tasas: "Pesos y tasas",
  tecnico: "Técnico", macro_dolar: "Macro / dólar", noticias: "Noticias", historiador: "Historiador",
  hechos_emisor: "Hechos del emisor", calificadoras: "Calificadoras", riesgo: "Riesgo", jefe: "Jefe" };

function toast(t) { const e = $("#toast"); e.textContent = t; e.classList.add("ver"); setTimeout(() => e.classList.remove("ver"), 2500); }
async function api(ruta, opt = {}) {
  const r = await fetch(`/api/${ruta}`, { headers: { "content-type": "application/json" }, ...opt });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || r.status);
  return r.json();
}
const put = (ruta, data) => api(ruta, { method: "PUT", body: JSON.stringify(data) });
const post = (ruta, data) => api(ruta, { method: "POST", body: JSON.stringify(data) });

// ---------- navegación ----------
document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll(".tabs button, .vista").forEach((x) => x.classList.remove("activa"));
  b.classList.add("activa"); $(`#v-${b.dataset.v}`).classList.add("activa"); window.scrollTo(0, 0);
}));

let ESTADO = {}, PROPS = [], USUARIO = { lista: [], cartera: [], ons: {}, capital: {} };

// ---------- propuestas ----------
function tarjeta(p) {
  const pl = p.plan, ok = p.decision === "pendiente";
  const sen = (p.senales || []).filter((s) => s.texto).map((s) =>
    `<div class="agente"><b>${esc(NOMBRES[s.agente] || s.agente)}</b><span>${esc(s.texto)}</span></div>`).join("");
  const seg = p.seguimiento || {};
  const estadoSeg = seg.estado === "pendiente" ? "Esperando entrada" : seg.estado === "abierta" ? `Abierta · ${num(seg.r_actual, 2)}R`
    : seg.r !== undefined ? `Cerrada (${seg.estado}) · ${num(seg.r_neto, 2)}R neto` : seg.estado;
  return `<div class="card">
    <div class="fila"><div><span class="tenue">${esc(p.fecha)} ${esc(p.hora)} · ${esc(p.sector || "")}</span>
      <div style="font-size:18px;font-weight:600">${esc(p.ticker)}</div></div>
      <span class="chip ${p.decision === "aprobada" ? "verde" : p.decision === "rechazada" ? "rojo" : ""}">${esc(p.decision)}</span></div>
    <p>${esc(p.resumen_jefe || "")} <span class="chip ${p.confianza === "alta" ? "verde" : "amar"}">confianza ${esc(p.confianza)}</span></p>
    <div class="grilla">
      <div class="met"><span>Compra límite</span><b>${num(pl.entrada)}</b></div>
      <div class="met"><span>Objetivo</span><b style="color:var(--verde)">${num(pl.objetivo)}</b></div>
      <div class="met"><span>Stop</span><b style="color:var(--rojo)">${num(pl.stop)}</b></div>
      <div class="met"><span>Tamaño · R neto</span><b>${num(pl.tamano_r, 1)}R · ${num(p.riesgo?.r_neto, 2)}</b></div>
    </div>
    <p class="tenue">${p.cantidad_sugerida ? `Cantidad sugerida: ${num(p.cantidad_sugerida, 0)} (≈ $${num(p.cantidad_sugerida * pl.entrada, 0)}). ` : ""}Arriesga ${num(pl.riesgo_pct, 1)}% para ganar ${num(pl.recompensa_pct, 1)}%. Vence ${esc(pl.vence)}. ${esc((p.riesgo?.avisos || []).join(" "))}</p>
    ${p.debate ? `<div class="debate"><b>Alcista:</b> ${esc(p.debate.alcista)}</div><div class="debate baj"><b>Bajista:</b> ${esc(p.debate.bajista)}</div>` : ""}
    <details><summary>Lo que dijo cada agente</summary>${sen || '<p class="tenue">Sin detalle.</p>'}</details>
    <p class="tenue">Seguimiento en prueba: ${esc(estadoSeg)}</p>
    ${ok ? `<div class="grilla" style="grid-template-columns:1fr 1fr"><button data-dec="rechazada" data-id="${esc(p.id)}">Rechazar</button>
      <button class="prim" data-dec="aprobada" data-id="${esc(p.id)}">Aprobar</button></div>
      <p class="tenue">Aprobar solo la anota: la orden la cargás vos en tu broker.</p>` : ""}
  </div>`;
}

function pintarPropuestas() {
  const hoy = ESTADO.estado?.fecha;
  const activas = PROPS.filter((p) => p.fecha === hoy || p.seguimiento?.estado === "pendiente" || p.seguimiento?.estado === "abierta");
  $("#lista-propuestas").innerHTML = activas.length ? activas.map(tarjeta).join("") : '<div class="vacio">Sin propuestas por ahora. Elegir no operar también es una decisión de la mesa.</div>';
  const cerradas = PROPS.filter((p) => !activas.includes(p)).slice(0, 40);
  $("#registro").innerHTML = cerradas.length ? `<div class="tabla-scroll"><table><tr><th>Fecha</th><th>Ticker</th><th>Decisión</th><th>Resultado</th><th class="n">R neto</th></tr>
    ${cerradas.map((p) => `<tr><td>${esc(p.fecha)}</td><td>${esc(p.ticker)}</td><td>${esc(p.decision)}</td><td>${esc(p.seguimiento?.estado)}</td><td class="n">${num(p.seguimiento?.r_neto, 2)}</td></tr>`).join("")}</table></div>`
    : '<p class="tenue">Todavía no hay operaciones cerradas.</p>';
  const e = ESTADO.estado?.esperanza || {};
  $("#esperanza").innerHTML = e.casos ? `<span class="chip">${e.casos} cerradas</span><span class="chip">${num(e.aciertos_pct, 0)}% aciertos</span>
    <span class="chip ${e.esperanza_r > 0 ? "verde" : "rojo"}">Esperanza ${num(e.esperanza_r, 2)}R por operación</span>` : "";
  document.querySelectorAll("[data-dec]").forEach((b) => b.addEventListener("click", async () => {
    try { await post("decision", { id: b.dataset.id, decision: b.dataset.dec }); toast("Anotado"); await cargar(); } catch (e) { toast(`No se pudo: ${e.message}`); }
  }));
}

function pintarEstado() {
  const est = ESTADO.estado || {}, ind = est.indicadores || {}, rp = est.riesgo_pais || {};
  $("#sub").textContent = est.fecha ? `Última ronda ${est.fecha} ${est.hora}` : "Todavía no corrió ninguna ronda";
  const clima = est.clima || "—";
  $("#clima").innerHTML = `<span class="chip ${clima === "malo" ? "rojo" : clima === "bueno" ? "verde" : "amar"}">Clima ${esc(clima)}</span>
    <span class="chip">Riesgo país ${num(rp.valor, 0)}${est.riesgo_pais_ayer ? ` (ayer ${num(est.riesgo_pais_ayer, 0)})` : ""}</span>
    <span class="chip">MEP ${num(ind.mep_al30)}</span><span class="chip">CCL ${num(ind.ccl_al30)}</span>`;
  $("#alertas").innerHTML = (ESTADO.alertas || []).filter((a) => a.fecha === est.fecha)
    .map((a) => `<div class="card" style="border-color:var(--amar)">🔔 ${esc(a.hora)} — ${esc(a.texto)}</div>`).join("");
  const d = est.dolares || {};
  const mets = [["MEP (AL30)", num(ind.mep_al30)], ["CCL (AL30)", num(ind.ccl_al30)], ["Canje MEP/CCL", pct(ind.canje_pct)],
    ["GD30 vs AL30", pct(ind.spread_gd_al_30)], ["Brecha MEP", pct(ind.brecha_mep_pct)], ["Caución corta TNA", ind.caucion_tna == null ? "—" : num(ind.caucion_tna) + "%"],
    ["Oficial", num(d.oficial?.venta)], ["Reservas BCRA (M US$)", num(est.reservas?.valor, 0)]];
  $("#indicadores").innerHTML = mets.map(([a, b]) => `<div class="met"><span>${a}</span><b>${b}</b></div>`).join("");
  pintarSenales();
  pintarInformes();
  pintarOportunidades();
  $("#evaluados").innerHTML = (est.evaluados || []).map((e) => `<div class="card"><div class="fila"><b>${esc(e.ticker)}</b>
    <span class="chip ${e.riesgo.ok ? "verde" : "rojo"}">${e.riesgo.ok ? "Pasa" : "Rechazada"}</span></div>
    <p class="tenue">Entrada ${num(e.plan.entrada)} · stop ${num(e.plan.stop)} · objetivo ${num(e.plan.objetivo)} · ${num(e.riesgo.r_neto, 2)}R neto</p>
    ${e.riesgo.motivos.map((m) => `<p class="tenue">• ${esc(m)}</p>`).join("")}</div>`).join("") || '<p class="tenue">Nada pasó el filtro inicial en esta ronda.</p>';
  const c = ESTADO.consumo || { total: 0 }, tope = ESTADO.tope || 25000, u = (c.total / tope) * 100;
  $("#consumo").innerHTML = `<div class="card"><div class="fila"><b>${num(c.total, 0)} de ${num(tope, 0)}</b><span class="chip ${u >= 80 ? "rojo" : ""}">${num(u, 1)}%</span></div>
    <div class="barra-uso"><i style="width:${Math.min(100, u)}%"></i></div>
    <p class="tenue">Por tipo: ${Object.entries(c.por_tipo || {}).map(([k, v]) => `${esc(k)} ${v}`).join(" · ") || "—"}. Al 80% la mesa baja la frecuencia sola.</p></div>`;
}

let PLAZO = "corto";
function pintarOportunidades() {
  const ops = (ESTADO.estado?.oportunidades || {})[PLAZO] || [];
  const col = { verde: "verde", amarillo: "amar", rojo: "rojo" };
  $("#oportunidades").innerHTML = ops.length ? ops.map((o) => `<div class="card">
    <div class="fila"><div><b style="font-size:17px">${esc(o.ticker)}</b> <span class="tenue">${esc(o.setup)}</span></div>
    <span class="chip ${col[o.semaforo]}">${o.semaforo === "verde" ? "Pasa Riesgo" : o.semaforo === "amarillo" ? "Con cuidado" : "Riesgo la frena"}</span></div>
    <p style="margin:6px 0">${esc(o.motivo)}</p>
    <div class="grilla"><div class="met"><span>Compra límite</span><b>${num(o.plan.entrada)}</b></div>
      <div class="met"><span>Objetivo</span><b style="color:var(--verde)">${num(o.plan.objetivo)} (${pct(o.plan.recompensa_pct, 1)})</b></div>
      <div class="met"><span>Stop</span><b style="color:var(--rojo)">${num(o.plan.stop)} (−${num(o.plan.riesgo_pct, 1)}%)</b></div>
      <div class="met"><span>Gana/arriesga neto</span><b>${num(o.r_neto, 2)}R</b></div></div>
    <p class="tenue">${esc(o.historia)}. Vence ${esc(o.plan.vence)}.</p>
    ${[...(o.riesgo.motivos || []), ...(o.riesgo.avisos || [])].map((m) => `<p class="tenue">• ${esc(m)}</p>`).join("")}
  </div>`).join("") : '<div class="vacio">Nada cerca de una entrada en este plazo por ahora.</div>';
}
document.querySelectorAll("#ops-plazo button").forEach((b) => b.addEventListener("click", () => {
  PLAZO = b.dataset.plazo; document.querySelectorAll("#ops-plazo button").forEach((x) => x.classList.toggle("prim", x === b)); pintarOportunidades();
}));

function pintarInformes() {
  const inf = ESTADO.estado?.informes || {};
  const orden = ["acciones", "cedears", "bonos", "ons", "letras", "licitaciones", "pesos", "tecnico"];
  const html = orden.filter((k) => inf[k]).map((k, i) => { const x = inf[k];
    const lectura = x.lectura_ia || x.lectura_ia_previa;
    return `<details class="card" ${i === 0 ? "open" : ""}><summary><b>${esc(x.titulo)}</b></summary>
      ${lectura ? `<p>${esc(lectura)}</p>` : ""}<p class="tenue">${esc(x.resumen)}</p>
      <div class="tabla-scroll"><table><tr>${x.columnas.map((c, j) => `<th class="${j ? "n" : ""}">${esc(c)}</th>`).join("")}</tr>
      ${x.filas.map((f) => `<tr>${f.map((v, j) => `<td class="${j ? "n" : ""}">${esc(v)}</td>`).join("")}</tr>`).join("")}</table></div>
      ${x.nota ? `<p class="tenue">${esc(x.nota)}</p>` : ""}</details>`; }).join("");
  $("#informes").innerHTML = html || '<p class="tenue">Los informes aparecen después de la próxima ronda.</p>';
}

function pintarSenales() {
  const f = ($("#filtro-senales").value || "").toLowerCase();
  const ss = (ESTADO.estado?.senales || []).filter((s) => !f || s.ticker.toLowerCase().includes(f) || (NOMBRES[s.agente] || "").toLowerCase().includes(f));
  $("#senales").innerHTML = ss.length ? ss.map((s) => `<div class="agente"><b>${esc(NOMBRES[s.agente] || s.agente)}</b>
    <span><span class="chip ${s.direccion > 0 ? "verde" : s.direccion < 0 ? "rojo" : ""}">${esc(s.ticker)}</span> ${esc(s.texto)}</span></div>`).join("") : '<p class="tenue">Sin señales.</p>';
}
$("#filtro-senales").addEventListener("input", pintarSenales);

// ---------- Mi lista, cartera, capital ----------
function pintarUsuario() {
  const precios = ESTADO.estado?.precios || {};
  const color = (v) => (v > 0 ? "verde" : v < 0 ? "rojo" : "");
  $("#mi-lista").innerHTML = USUARIO.lista.length ? USUARIO.lista.map((x, i) => {
    const q = precios[x.ticker] || {}, dist = q.ultimo && x.precio ? (q.ultimo / x.precio - 1) * 100 : null;
    return `<div class="item"><div class="item-cab"><b>${esc(x.ticker)}</b>
        <span class="item-precio">${num(q.ultimo)} <span class="chip ${color(q.variacion)}">${pct(q.variacion)}</span></span>
        <button class="quitar" data-quitar-lista="${i}" aria-label="Quitar ${esc(x.ticker)}">✕</button></div>
      <div class="item-det">${x.precio ? `Tu precio ${num(x.precio)} · ${dist === null ? "sin cotización" : Math.abs(dist) < 0.3 ? "<b>¡en tu precio!</b>" : `está ${num(Math.abs(dist), 1)}% ${dist > 0 ? "arriba" : "abajo"}`}` : "Sin precio objetivo"}${x.nota ? ` · ${esc(x.nota)}` : ""}</div></div>`;
  }).join("") : '<p class="tenue">Agregá tickers para que la mesa los siga.</p>';
  $("#cartera").innerHTML = USUARIO.cartera.length ? USUARIO.cartera.map((x, i) => {
    const u = precios[x.ticker]?.ultimo, r = u && x.precio ? (u / x.precio - 1) * 100 : null;
    return `<div class="item"><div class="item-cab"><b>${esc(x.ticker)}</b>
        <span class="item-precio">${num(u)}${r === null ? "" : ` <span class="chip ${color(r)}">${pct(r)}</span>`}</span>
        <button class="quitar" data-quitar-cartera="${i}" aria-label="Quitar ${esc(x.ticker)}">✕</button></div>
      <div class="item-det">${num(x.cantidad, 0)} nominales · compra ${num(x.precio)}${u ? "" : " · sin cotización en la ronda"}</div></div>`;
  }).join("") : '<p class="tenue">Sin posiciones cargadas.</p>';
  const cap = USUARIO.capital || {};
  $("#capital-info").textContent = cap.monto_ars ? `1R = ${num(cap.monto_ars * (cap.riesgo_pct || 1) / 100, 0)} pesos de pérdida máxima por operación.` : "Si no lo cargás, se usa el de la configuración.";
  document.querySelectorAll("[data-quitar-lista]").forEach((b) => b.onclick = async () => { USUARIO.lista.splice(+b.dataset.quitarLista, 1); await put("usuario/lista", USUARIO.lista); pintarUsuario(); });
  document.querySelectorAll("[data-quitar-cartera]").forEach((b) => b.onclick = async () => { USUARIO.cartera.splice(+b.dataset.quitarCartera, 1); await put("usuario/cartera", USUARIO.cartera); pintarUsuario(); pintarCalendario(); });
  pintarCalendario();
}
const leerForm = (f) => Object.fromEntries(new FormData(f).entries());
const aNum = (s) => {
  if (s === "" || s === undefined || s === null) return null;
  const t = String(s).trim();
  // "1.234,56" (formato argentino) o "103.9" / "1234.5" (punto decimal)
  const v = t.includes(",") ? Number(t.replace(/\./g, "").replace(",", ".")) : Number(t);
  return isNaN(v) ? null : v;
};
$("#form-lista").addEventListener("submit", async (ev) => {
  ev.preventDefault(); const d = leerForm(ev.target); const t = d.ticker.trim().toUpperCase();
  if (USUARIO.lista.some((x) => x.ticker === t)) return toast("Ya está en la lista");
  USUARIO.lista.push({ ticker: t, precio: aNum(d.precio), nota: d.nota }); await put("usuario/lista", USUARIO.lista); ev.target.reset(); pintarUsuario(); toast("Agregado: entra en la próxima ronda");
});
$("#form-cartera").addEventListener("submit", async (ev) => {
  ev.preventDefault(); const d = leerForm(ev.target);
  USUARIO.cartera.push({ ticker: d.ticker.trim().toUpperCase(), cantidad: aNum(d.cantidad), precio: aNum(d.precio) });
  await put("usuario/cartera", USUARIO.cartera); ev.target.reset(); pintarUsuario(); toast("Cartera actualizada");
});
$("#form-capital").addEventListener("submit", async (ev) => {
  ev.preventDefault(); const d = leerForm(ev.target);
  USUARIO.capital = { monto_ars: aNum(d.monto_ars), riesgo_pct: aNum(d.riesgo_pct) || 1 }; await put("usuario/capital", USUARIO.capital); pintarUsuario(); toast("Guardado");
});

// ---------- ONs: calendario y simulador ----------
function flujo(on, nominales, desde) {
  return (on.flujos || []).filter((f) => f.fecha > desde).map((f) => {
    const i = nominales * f.interes / 100, a = nominales * f.amortizacion / 100; return { fecha: f.fecha, interes: i, amortizacion: a, total: i + a };
  });
}
function tir(precio100, fl, hoy) {
  if (!fl.length) return null;
  const pts = fl.map((f) => [(new Date(f.fecha) - new Date(hoy)) / 864e5 / 365, f.total]);
  const vpn = (r) => pts.reduce((s, [t, c]) => s + c / Math.pow(1 + r, t), 0) - precio100;
  let lo = -0.9, hi = 5; if (vpn(lo) * vpn(hi) > 0) return null;
  for (let k = 0; k < 200; k++) { const m = (lo + hi) / 2; if (vpn(lo) * vpn(m) <= 0) hi = m; else lo = m; }
  return ((lo + hi) / 2) * 100;
}
const HOY = () => new Date().toLocaleDateString("en-CA", { timeZone: "America/Argentina/Buenos_Aires" });

function pintarCalendario() {
  const filas = [];
  for (const pos of USUARIO.cartera) { const on = USUARIO.ons[pos.ticker]; if (!on) continue;
    for (const f of flujo(on, pos.cantidad, HOY())) filas.push({ ...f, ticker: pos.ticker, moneda: on.moneda }); }
  filas.sort((a, b) => a.fecha.localeCompare(b.fecha));
  const porMes = {}; for (const f of filas) { const m = f.fecha.slice(0, 7); porMes[m] = (porMes[m] || 0) + f.total; }
  const dias = (f) => Math.round((new Date(f) - new Date(HOY())) / 864e5);
  $("#calendario").innerHTML = filas.length ? `<div class="tiras">${Object.entries(porMes).slice(0, 6).map(([m, v]) => `<span class="chip">${m}: ${num(v)}</span>`).join("")}</div>
    <div class="tabla-scroll"><table><tr><th>Fecha</th><th>ON</th><th class="n">Interés</th><th class="n">Amort.</th><th class="n">Total</th><th class="n">Faltan</th></tr>
    ${filas.slice(0, 40).map((f) => `<tr><td>${f.fecha}</td><td>${esc(f.ticker)} <span class="tenue">${esc(f.moneda || "")}</span></td><td class="n">${num(f.interes)}</td><td class="n">${num(f.amortizacion)}</td><td class="n"><b>${num(f.total)}</b></td><td class="n">${dias(f.fecha)} d</td></tr>`).join("")}</table></div>`
    : '<p class="tenue">Cargá en Cartera las ONs que tenés y sus flujos abajo para ver el calendario.</p>';
  $("#sim-on").innerHTML = Object.keys(USUARIO.ons).map((k) => `<option>${esc(k)}</option>`).join("") || "<option value=''>Primero cargá una ON abajo</option>";
  const sel = $("#sim-on").value; const p = ESTADO.estado?.precios?.[sel]?.ultimo; if (p && !$("#form-sim").precio.value) $("#form-sim").precio.value = p;
}
$("#sim-on").addEventListener("change", () => { const p = ESTADO.estado?.precios?.[$("#sim-on").value]?.ultimo; if (p) $("#form-sim").precio.value = p; });
$("#form-sim").addEventListener("submit", (ev) => {
  ev.preventDefault(); const d = leerForm(ev.target), on = USUARIO.ons[d.on]; if (!on) return toast("Elegí una ON");
  const precio = aNum(d.precio), lam = on.lamina_minima || 1; let nom = aNum(d.nominales);
  if (!nom) { const cap = aNum(d.capital); if (!cap) return toast("Completá capital o nominales"); nom = Math.floor(cap / (precio / 100) / lam) * lam; }
  const costo = nom * precio / 100, fl = flujo(on, nom, HOY()), total = fl.reduce((s, f) => s + f.total, 0), t = tir(precio, flujo(on, 100, HOY()), HOY());
  $("#sim-resultado").innerHTML = `<div class="card"><div class="grilla">
    <div class="met"><span>Nominales</span><b>${num(nom, 0)}</b></div><div class="met"><span>Invertís</span><b>${num(costo)}</b></div>
    <div class="met"><span>Cobrás en total</span><b>${num(total)}</b></div><div class="met"><span>Ganancia · TIR</span><b>${num(total - costo)} · ${t === null ? "—" : num(t) + "%"}</b></div></div>
    <div class="tabla-scroll"><table><tr><th>Fecha</th><th class="n">Interés</th><th class="n">Amortización</th><th class="n">Total</th></tr>
    ${fl.map((f) => `<tr><td>${f.fecha}</td><td class="n">${num(f.interes)}</td><td class="n">${num(f.amortizacion)}</td><td class="n"><b>${num(f.total)}</b></td></tr>`).join("")}</table></div>
    <p class="tenue">En ${esc(on.moneda || "la moneda de la ON")}. Lámina mínima ${num(lam, 0)}. No incluye comisiones ni impuestos.</p></div>`;
});
$("#form-on").addEventListener("submit", async (ev) => {
  ev.preventDefault(); const d = leerForm(ev.target); const flujos = [];
  for (const linea of d.flujos.split("\n").map((l) => l.trim()).filter(Boolean)) {
    const [fecha, i, a] = linea.split(",").map((x) => x.trim());
    if (!/^\d{4}-\d{2}-\d{2}$/.test(fecha)) return toast(`Fecha inválida: ${fecha}`);
    flujos.push({ fecha, interes: Number(i) || 0, amortizacion: Number(a) || 0 });
  }
  const amort = flujos.reduce((s, f) => s + f.amortizacion, 0);
  if (Math.abs(amort - 100) > 0.01) return toast(`La amortización suma ${amort}%, debería sumar 100%`);
  USUARIO.ons[d.ticker.trim().toUpperCase()] = { emisor: d.emisor, moneda: d.moneda, lamina_minima: aNum(d.lamina) || 1, flujos };
  await put("usuario/ons", USUARIO.ons); ev.target.reset(); pintarCalendario(); toast("ON guardada");
});

// ---------- ranking ----------
async function pintarRanking() {
  const r = await api("ranking");
  $("#ranking").innerHTML = r.tabla.length ? `<div class="tabla-scroll"><table><tr><th>Agente</th><th>Nivel</th><th class="n">Casos</th><th class="n">Aciertos</th><th class="n">Esperanza</th><th class="n">Peso</th></tr>
    ${r.tabla.map((f) => `<tr><td>${esc(NOMBRES[f.agente] || f.agente)}</td><td><span class="chip ${f.nivel === "titular" ? "verde" : f.nivel === "banco" ? "rojo" : f.nivel === "a_prueba" ? "amar" : ""}">${esc(f.nivel.replace("_", " "))}</span></td>
    <td class="n">${f.casos}</td><td class="n">${num(f.aciertos_pct, 0)}%</td><td class="n">${pct(f.esperanza_pct)}</td><td class="n">${num(f.peso, 1)}</td></tr>`).join("")}</table></div>`
    : '<p class="tenue">El ranking arranca cuando los agentes juntan casos (se arma cada viernes).</p>';
  const pend = r.pendientes.filter((p) => p.estado === "pendiente");
  $("#capacitacion").innerHTML = pend.length ? pend.map((p) => `<div class="card"><b>${esc(NOMBRES[p.agente])}</b>
    <p class="tenue">Antes: ${esc(JSON.stringify(p.antes))}<br>Después: ${esc(JSON.stringify(p.despues))}</p>
    <p>Con datos que no usó para ajustarse: ${pct(p.fuera_de_muestra.antes_pct)} → ${pct(p.fuera_de_muestra.despues_pct)} por señal (${p.fuera_de_muestra.casos_despues} casos).</p>
    <div class="grilla" style="grid-template-columns:1fr 1fr"><button data-cap="${esc(p.agente)}" data-ok="0">Rechazar</button><button class="prim" data-cap="${esc(p.agente)}" data-ok="1">Aprobar cambio</button></div></div>`).join("")
    : '<p class="tenue">No hay cambios pendientes. La capacitación corre el primer día hábil de cada mes.</p>';
  document.querySelectorAll("[data-cap]").forEach((b) => b.onclick = async () => { await post("capacitacion", { agente: b.dataset.cap, aprobar: b.dataset.ok === "1" }); toast("Listo"); pintarRanking(); });
  $("#calificadoras").innerHTML = r.calificadoras.length ? r.calificadoras.map((c) => `<p>• ${esc(c.fecha)} — ${esc(c.agencia)} ${esc(c.emisor)}: ${esc(c.antes)} → ${esc(c.despues)} ${esc(c.perspectiva || "")}</p>`).join("")
    : '<p class="tenue">Sin cambios de nota registrados.</p>';
}

// ---------- consultor gratis ----------
let PANEL = null;
async function panel() { if (!PANEL) PANEL = await api("panel"); return PANEL; }
const MESES = { E: 1, F: 2, M: 3, A: 4, Y: 5, J: 6, L: 7, G: 8, S: 9, O: 10, N: 11, D: 12 };
function vtoLetra(tk) { const m = tk.match(/^[STX](\d{2})([EFMAYJLGSOND])(\d)$/); if (!m) return null;
  const d = new Date(2020 + +m[3], MESES[m[2]] - 1, +m[1]); return isNaN(d) ? null : d; }
const media = (a, n) => a.length >= n ? a.slice(-n).reduce((x, y) => x + y, 0) / n : null;
function rsi(c, n = 14) { if (c.length < n + 1) return null; let s = 0, b = 0;
  for (let i = c.length - n; i < c.length; i++) { const d = c[i] - c[i - 1]; if (d > 0) s += d; else b -= d; }
  return b === 0 ? 100 : 100 - 100 / (1 + s / b); }
$("#form-precio").addEventListener("submit", async (ev) => {
  ev.preventDefault(); const tk = ev.target.ticker.value.trim().toUpperCase(); const box = $("#eval-precio");
  box.innerHTML = '<p class="tenue">Calculando…</p>';
  try {
    const [p, hist] = await Promise.all([panel(), api(`historico?t=${encodeURIComponent(tk)}`)]);
    const t = p.titulos?.[tk];
    if (!t) { box.innerHTML = `<p class="tenue">No encontré ${esc(tk)} en la última ronda (${esc(p.fecha)} ${esc(p.hora)}).</p>`; return; }
    const [ult, varDia, compra, venta] = t;
    if (!hist.length) { box.innerHTML = `<div class="card"><b>${esc(tk)}</b> ${num(ult)} (${pct(varDia)})<p class="tenue">Todavía no tengo historial de ${esc(tk)} para comparar. Agregalo a Mi lista y en unos días la mesa lo carga.</p></div>`; return; }
    const c = hist.map((v) => v.cierre).concat([ult]);
    const m20 = media(c, 20), m50 = media(c, 50), r = rsi(c);
    const u60 = hist.slice(-60), min60 = Math.min(...u60.map((v) => v.minimo)), max60 = Math.max(...u60.map((v) => v.maximo));
    const pos = (ult - min60) / (max60 - min60 || 1) * 100;
    const spread = compra && venta ? (venta / compra - 1) * 100 : null;
    let veredicto = "Neutral", color = "amar", porque = [];
    if ((r !== null && r < 35 && pos < 30) || (m20 && ult < m20 * 0.97 && pos < 35)) { veredicto = "Precio bajo: zona de compra"; color = "verde"; }
    else if ((r !== null && r > 70) || pos > 85) { veredicto = "Precio alto: mejor esperar"; color = "rojo"; }
    porque.push(`Está en el ${num(pos, 0)}% del rango de 60 ruedas (${num(min60)} a ${num(max60)}).`);
    if (m20) porque.push(`${ult > m20 ? "Arriba" : "Abajo"} de su media de 20 ruedas (${num(m20)}).`);
    if (m50) porque.push(`${ult > m50 ? "Arriba" : "Abajo"} de su media de 50 ruedas (${num(m50)}): tendencia ${ult > m50 ? "alcista" : "bajista"}.`);
    if (r !== null) porque.push(`RSI ${num(r, 0)} (${r < 30 ? "sobrevendido" : r > 70 ? "sobrecomprado" : "normal"}).`);
    if (spread !== null) porque.push(`Spread compra/venta ${num(spread)}%${spread > 1 ? ": poco líquido, usá orden límite" : ""}.`);
    box.innerHTML = `<div class="card"><div class="fila"><b style="font-size:17px">${esc(tk)} ${num(ult)}</b><span class="chip ${color}">${veredicto}</span></div>
      ${porque.map((x) => `<p class="tenue">• ${esc(x)}</p>`).join("")}
      <p class="tenue">Precio de la ronda ${esc(p.fecha)} ${esc(p.hora)}. Es una lectura técnica, no una recomendación.</p></div>`;
  } catch (e) { box.innerHTML = `<p class="tenue">No se pudo: ${esc(e.message)}</p>`; }
});
$("#form-letras").addEventListener("submit", async (ev) => {
  ev.preventDefault(); const mes = ev.target.mes.value; const box = $("#lista-letras");
  const p = await panel(); const hoy = new Date();
  const limite = mes ? new Date(+mes.slice(0, 4), +mes.slice(5, 7), 0) : null;
  const filas = Object.entries(p.titulos || {}).filter(([, x]) => x[4] === "letras").map(([tk, x]) => ({ tk, v: vtoLetra(tk), x }))
    .filter((f) => f.v && f.v > hoy && (!limite || f.v <= limite)).sort((a, b) => a.v - b.v);
  box.innerHTML = filas.length ? `<div class="tabla-scroll"><table><tr><th>Ticker</th><th>Vence</th><th class="n">Días</th><th class="n">Precio</th><th class="n">Día</th></tr>
    ${filas.map((f) => `<tr><td>${esc(f.tk)}</td><td>${f.v.toLocaleDateString("es-AR")}</td><td class="n">${Math.round((f.v - hoy) / 864e5)}</td><td class="n">${num(f.x[0], 3)}</td><td class="n">${pct(f.x[1])}</td></tr>`).join("")}</table></div>
    <p class="tenue">Para saber cuánto cobrás y la tasa de cada una, preguntame en el chat de Claude: lo calculo con IOL en vivo.</p>`
    : '<p class="tenue">No hay letras con precio que venzan antes de esa fecha.</p>';
});
api("asistente/estado").then((r) => { if (r.activo) { $("#asistente-ia").style.display = "block"; $("#asistente-gratis").style.display = "none"; } }).catch(() => {});

// ---------- asistente ----------
let CHAT = [];
try { CHAT = JSON.parse(localStorage.getItem("mesa_chat") || "[]"); } catch (_) { CHAT = []; }
const guardarChat = () => { try { localStorage.setItem("mesa_chat", JSON.stringify(CHAT.slice(-20))); } catch (_) {} };
function md(t) {
  // markdown mínimo y seguro: escapa todo y después aplica negritas, tablas y links
  const lineas = esc(t).split("\n"); let html = "", tabla = [];
  const cerrarTabla = () => { if (!tabla.length) return; const filas = tabla.filter((l) => !/^\|?\s*:?-{2,}/.test(l));
    html += `<div class="tabla-scroll"><table>${filas.map((l, i) => `<tr>${l.replace(/^\||\|$/g, "").split("|").map((c) => i ? `<td>${c.trim()}</td>` : `<th>${c.trim()}</th>`).join("")}</tr>`).join("")}</table></div>`; tabla = []; };
  for (const l of lineas) { if (/^\s*\|/.test(l)) { tabla.push(l.trim()); continue; } cerrarTabla(); html += l + "\n"; }
  cerrarTabla();
  return html.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
}
function pintarChat() {
  $("#chat").innerHTML = CHAT.map((m) => `<div class="msg ${m.rol}">${m.rol === "ia" ? md(m.texto) : esc(m.texto)}
    ${m.fuentes?.length ? `<p class="tenue">Fuentes: ${m.fuentes.map((f) => `<a href="${esc(f.url)}" target="_blank" rel="noopener">${esc(f.titulo || f.url)}</a>`).join(" · ")}</p>` : ""}</div>`).join("")
    || '<p class="vacio">Todavía no preguntaste nada.</p>';
}
$("#form-chat").addEventListener("submit", async (ev) => {
  ev.preventDefault(); const q = ev.target.pregunta.value.trim(); if (!q) return;
  const historial = CHAT.slice(-8).map((m) => ({ rol: m.rol, texto: m.texto }));
  CHAT.push({ rol: "yo", texto: q }); ev.target.reset(); pintarChat();
  const btn = ev.target.querySelector("button.prim"); btn.disabled = true; $("#chat-info").textContent = "Pensando y buscando datos… (puede tardar 20-60 segundos)";
  try { const r = await post("asistente", { pregunta: q, historial });
    CHAT.push({ rol: "ia", texto: r.respuesta, fuentes: r.fuentes }); $("#chat-info").textContent = `Te quedan ${r.restantes} preguntas hoy.`;
  } catch (e) { CHAT.push({ rol: "ia", texto: `No pude responder: ${e.message}` }); $("#chat-info").textContent = ""; }
  btn.disabled = false; guardarChat(); pintarChat(); window.scrollTo(0, document.body.scrollHeight);
});
$("#btn-chat-borrar").addEventListener("click", () => { CHAT = []; guardarChat(); pintarChat(); });
pintarChat();

// ---------- push ----------
$("#btn-push").addEventListener("click", async () => {
  try {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) return toast("Este navegador no soporta avisos");
    const { clave } = await api("push/clave"); if (!clave) return toast("Falta configurar la clave de avisos");
    const reg = await navigator.serviceWorker.ready;
    if ((await Notification.requestPermission()) !== "granted") return toast("Permiso de avisos denegado");
    const pad = "=".repeat((4 - (clave.length % 4)) % 4), raw = atob((clave + pad).replace(/-/g, "+").replace(/_/g, "/"));
    const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: Uint8Array.from(raw, (c) => c.charCodeAt(0)) });
    await post("push/suscribir", sub.toJSON()); toast("Avisos activados");
  } catch (e) { toast(`No se pudo: ${e.message}`); }
});
$("#btn-analizar").addEventListener("click", async () => {
  try { const r = await post("analizar", {}); toast(r.mensaje || "Ronda pedida"); } catch (e) { toast(`No se pudo: ${e.message}`); }
});

// ---------- carga ----------
async function cargar() {
  try {
    [ESTADO, PROPS, USUARIO.lista, USUARIO.cartera, USUARIO.ons, USUARIO.capital] = await Promise.all([
      api("estado"), api("propuestas"), api("usuario/lista"), api("usuario/cartera"), api("usuario/ons"), api("usuario/capital")]);
    pintarEstado(); pintarPropuestas(); pintarUsuario();
    $("#login").style.display = "none"; document.querySelector("main").style.display = "";
  } catch (e) {
    if (String(e.message).includes("sin acceso")) {
      $("#login").style.display = "block"; document.querySelector("main").style.display = "none";
      $("#sub").textContent = "Ingresá tu clave";
    } else $("#sub").textContent = `No se pudo cargar: ${e.message}`;
  }
}
$("#form-login").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  try { await post("login", { clave: ev.target.clave.value }); ev.target.reset(); await cargar(); pintarRanking().catch(() => {}); }
  catch (e) { toast(e.message); }
});
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js");
cargar(); pintarRanking().catch(() => {});
setInterval(() => { if (!document.hidden) cargar(); }, 60000);
document.addEventListener("visibilitychange", () => { if (!document.hidden) cargar(); });
