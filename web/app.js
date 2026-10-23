"use strict";
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (x, d = 2) => (x === null || x === undefined || isNaN(x) ? "—" : Number(x).toLocaleString("es-AR", { minimumFractionDigits: d, maximumFractionDigits: d }));
const pct = (x, d = 2) => (x === null || x === undefined ? "—" : `${x > 0 ? "+" : ""}${num(x, d)}%`);
const NOMBRES = { acciones: "Acciones", cedears: "CEDEARs", ons: "ONs", soberanos: "Soberanos", pesos_tasas: "Pesos y tasas",
  tecnico: "Técnico", fuerza_relativa: "Fuerza relativa", volumen_flujo: "Volumen y flujo", economista: "Economista", wallstreet: "Wall Street", cripto: "Cripto", adr: "Noche de Nueva York", panico: "Comprador de pánico", mundo: "Corresponsal (mundo)", ministro: "Ministro (política económica)", anticipo: "Anticipo (Nueva York)", anticipador: "Anticipador", macro_dolar: "Macro / dólar", noticias: "Noticias", historiador: "Historiador",
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
function irA(v) {
  document.querySelectorAll(".tabs button, .vista").forEach((x) => x.classList.remove("activa"));
  document.querySelector(`.tabs button[data-v="${v}"]`)?.classList.add("activa");
  $(`#v-${v}`).classList.add("activa"); window.scrollTo(0, 0);
}
document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => irA(b.dataset.v)));
$("#btn-ajustes").addEventListener("click", () => irA("ajustes"));
const fecha = (f) => (f ? `${f.slice(8, 10)}/${f.slice(5, 7)}` : "");
const fechaLarga = (f) => (f ? `${f.slice(8, 10)}/${f.slice(5, 7)}/${f.slice(2, 4)}` : "");
const MESES_TXT = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];
function mercadoAbierto() {
  const ba = new Date(new Date().toLocaleString("en-US", { timeZone: "America/Argentina/Buenos_Aires" }));
  const m = ba.getHours() * 60 + ba.getMinutes(), d = ba.getDay();
  return d >= 1 && d <= 5 && m >= 630 && m <= 1020;
}

let ESTADO = {}, PROPS = [], USUARIO = { lista: [], cartera: [], ons: {}, capital: {} };

// ---------- propuestas ----------
const CONSEJO_TXT = { mantener: "Mantener", subir_stop: "Subir el stop", salir: "Salir", antes_balance: "Ojo, balance", cerca_stop: "Cerca del stop", cancelar: "Cancelar la orden", esperar: "Esperando precio" };
const CONSEJO_COL = { mantener: "verde", subir_stop: "verde", salir: "rojo", antes_balance: "amar", cerca_stop: "amar", cancelar: "rojo", esperar: "" };
function tarjeta(p) {
  const pl = p.plan, ok = p.decision === "pendiente";
  const sen = (p.senales || []).filter((s) => s.texto).map((s) =>
    `<div class="agente"><b>${esc(NOMBRES[s.agente] || s.agente)}</b><span>${esc(s.texto)}</span></div>`).join("");
  const seg = p.seguimiento || {};
  const estadoSeg = seg.estado === "pendiente" ? "Esperando entrada" : seg.estado === "abierta" ? `Abierta · ${num(seg.r_actual, 2)}R`
    : seg.r !== undefined ? `Cerrada (${seg.estado}) · ${num(seg.r_neto, 2)}R neto` : seg.estado;
  return `<div class="card" data-tarjeta="${esc(p.id)}">
    <div class="fila"><div><span class="tenue">${esc(fecha(p.fecha))} ${esc(p.hora)} · ${esc(p.sector || "")}</span>
      <div style="font-size:18px;font-weight:600">${esc(p.ticker)}</div></div>
      <span class="chip ${p.decision === "aprobada" ? "verde" : p.decision === "rechazada" ? "rojo" : ""}">${esc(p.decision)}</span></div>
    ${seg.consejo ? `<div class="consejo ${CONSEJO_COL[seg.consejo.accion] || ""}"><b>${esc(CONSEJO_TXT[seg.consejo.accion] || seg.consejo.accion)}</b> ${esc(seg.consejo.texto)} <span class="tenue">(${esc(seg.consejo.hora || "")})</span></div>` : ""}
    <p>${esc(p.resumen_jefe || "")} <span class="chip ${p.confianza === "alta" ? "verde" : "amar"}">confianza ${esc(p.confianza)}</span></p>
    <div class="grilla">
      <div class="met"><span>Compra límite</span><b>${num(pl.entrada)}</b></div>
      <div class="met"><span>Objetivo</span><b style="color:var(--verde)">${num(pl.objetivo)}</b></div>
      <div class="met"><span>Stop</span><b style="color:var(--rojo)">${num(pl.stop)}</b></div>
      <div class="met"><span>Tamaño · R neto</span><b>${num(pl.tamano_r, 1)}R · ${num(p.riesgo?.r_neto, 2)}</b></div>
    </div>
    <p class="tenue">${p.cantidad_sugerida ? `Cantidad sugerida: ${num(p.cantidad_sugerida, 0)} (≈ $${num(p.cantidad_sugerida * pl.entrada, 0)}). ` : ""}Arriesga ${num(pl.riesgo_pct, 1)}% para ganar ${num(pl.recompensa_pct, 1)}%. ${p.principal ? `Plazo ${p.ruedas >= 40 ? "~" + Math.round(p.ruedas / 20) + " meses" : p.ruedas + " ruedas"} (idea de ${esc(nombreAg(p.principal))}): vence ${esc(fecha(pl.vence))}.` : `Vence ${esc(pl.vence)}.`} ${esc((p.riesgo?.avisos || []).join(" "))}</p>
    ${p.debate ? `<div class="debate"><b>Alcista:</b> ${esc(p.debate.alcista)}</div><div class="debate baj"><b>Bajista:</b> ${esc(p.debate.bajista)}</div>` : ""}
    <details><summary>Lo que dijo cada agente</summary>${sen || '<p class="tenue">Sin detalle.</p>'}</details>
    <button class="chico" data-abrir-debate="${esc(p.ticker)}">Ver debate completo</button>
    <p class="tenue">Seguimiento en prueba: ${esc(estadoSeg)}</p>
    ${ok ? `<div class="grilla" style="grid-template-columns:1fr 1fr"><button data-dec="rechazada" data-id="${esc(p.id)}">Rechazar</button>
      <button class="prim" data-dec="aprobada" data-id="${esc(p.id)}">Aprobar</button></div>
      <p class="tenue">Aprobar solo la anota: la orden la cargás vos en tu broker.</p>` : ""}
  </div>`;
}

function pintarPropuestas() {
  const hoy = ESTADO.estado?.fecha;
  const activas = PROPS.filter((p) => p.fecha === hoy || p.seguimiento?.estado === "pendiente" || p.seguimiento?.estado === "abierta");
  $("#lista-propuestas").innerHTML = activas.length ? activas.map(tarjeta).join("") : '<div class="vacio">Nada para decidir ahora. Elegir no operar también es una decisión de la mesa.</div>';
  const cerradas = PROPS.filter((p) => !activas.includes(p)).slice(0, 40);
  $("#registro").innerHTML = cerradas.length ? `<div class="tabla-scroll"><table><tr><th>Fecha</th><th>Ticker</th><th>Decisión</th><th>Resultado</th><th class="n">R neto</th></tr>
    ${cerradas.map((p) => `<tr><td>${esc(fecha(p.fecha))}</td><td>${esc(p.ticker)}</td><td>${esc(p.decision)}</td><td>${esc(p.seguimiento?.estado)}</td><td class="n">${num(p.seguimiento?.r_neto, 2)}</td></tr>`).join("")}</table></div>`
    : '<p class="tenue">Todavía no hay operaciones cerradas.</p>';
  const e = ESTADO.estado?.esperanza || {};
  $("#esperanza").innerHTML = e.casos ? `<span class="chip">${e.casos} cerradas</span><span class="chip">${num(e.aciertos_pct, 0)}% aciertos</span>
    <span class="chip ${e.esperanza_r > 0 ? "verde" : "rojo"}">Esperanza ${num(e.esperanza_r, 2)}R por operación</span>` : "";
  document.querySelectorAll("[data-dec]").forEach((b) => b.addEventListener("click", async () => {
    try { await post("decision", { id: b.dataset.id, decision: b.dataset.dec }); VISTOS.add(b.dataset.id); guardarVistos(); toast("Anotado"); await cargar(); } catch (e) { toast(`No se pudo: ${e.message}`); }
  }));
}

function pintarEstado() {
  const est = ESTADO.estado || {}, ind = est.indicadores || {}, rp = est.riesgo_pais || {};
  $("#sub").textContent = est.fecha ? `${mercadoAbierto() ? "● Abierto" : "Cerrado"} · ronda ${fecha(est.fecha)} ${est.hora}` : "Todavía no corrió ninguna ronda";
  const clima = est.clima || "—";
  $("#clima").innerHTML = `<span class="chip ${clima === "malo" ? "rojo" : clima === "bueno" ? "verde" : "amar"}">Clima ${esc(clima)}</span>
    <span class="chip">Riesgo país ${num(rp.valor, 0)}${est.riesgo_pais_ayer ? ` (ayer ${num(est.riesgo_pais_ayer, 0)})` : ""}</span>`;
  $("#alertas").innerHTML = (ESTADO.alertas || []).filter((a) => a.fecha === est.fecha)
    .map((a) => `<div class="card" style="border-color:var(--amar)">🔔 ${esc(a.hora)} — ${esc(a.texto)}</div>`).join("");
  const d = est.dolares || {};
  const mets = [["MEP (AL30)", num(ind.mep_al30)], ["CCL (AL30)", num(ind.ccl_al30)], ["Canje MEP/CCL", pct(ind.canje_pct)],
    ["GD30 vs AL30", pct(ind.spread_gd_al_30)], ["Brecha MEP", pct(ind.brecha_mep_pct)], ["Caución corta TNA", ind.caucion_tna == null ? "—" : num(ind.caucion_tna) + "%"],
    ["Oficial", num(d.oficial?.venta)], ["Reservas BCRA (M US$)", num(est.reservas?.valor, 0)]];
  $("#indicadores").innerHTML = mets.map(([a, b]) => `<div class="met"><span>${a}</span><b>${b}</b></div>`).join("");
  // a qué hora son los datos del mercado
  if (est.fecha) {
    const hoyBA = HOY(), ahora = new Date(new Date().toLocaleString("en-US", { timeZone: "America/Argentina/Buenos_Aires" }));
    const [hh, mm] = String(est.hora || "0:0").split(":").map(Number);
    const min = est.fecha === hoyBA ? ahora.getHours() * 60 + ahora.getMinutes() - (hh * 60 + mm) : null;
    const hace = min === null ? "" : min < 1 ? " · recién" : min < 60 ? ` · hace ${min} min` : ` · hace ${Math.floor(min / 60)} h ${min % 60} min`;
    $("#hora-mercado").innerHTML = `Datos de la ronda de las <b>${esc(est.hora)}</b> ${est.fecha === hoyBA ? "de hoy" : `del ${esc(fecha(est.fecha))}`}${hace}`;
    $("#hora-mercado").classList.toggle("vieja", min === null || min > 20);
    document.querySelectorAll("[data-hora]").forEach((x) => (x.textContent = `· ${est.hora}`));
  }
  pintarEconomista();
  pintarWallStreet();
  pintarMinistro();
  pintarMundo();
  pintarCobros();
  pintarPronosticos();
  pintarCripto();
  pintarADR();
  pintarSenales();
  pintarInformes();
  pintarOportunidades();
  pintarResumenHoy();
  $("#evaluados").innerHTML = (est.evaluados || []).map((e) => `<div class="card"><div class="fila"><b>${esc(e.ticker)}</b>
    <span class="chip ${e.riesgo.ok ? "verde" : "rojo"}">${e.riesgo.ok ? "Pasa" : "Rechazada"}</span></div>
    <p class="tenue">Entrada ${num(e.plan.entrada)} · stop ${num(e.plan.stop)} · objetivo ${num(e.plan.objetivo)} · ${num(e.riesgo.r_neto, 2)}R neto</p>
    ${e.riesgo.motivos.map((m) => `<p class="tenue">• ${esc(m)}</p>`).join("")}</div>`).join("") || '<p class="tenue">Nada pasó el filtro inicial en esta ronda.</p>';
  const c = ESTADO.consumo || { total: 0 }, tope = ESTADO.tope || 25000, u = (c.total / tope) * 100;
  $("#consumo").innerHTML = `<div class="card"><div class="fila"><b>${num(c.total, 0)} de ${num(tope, 0)}</b><span class="chip ${u >= 80 ? "rojo" : ""}">${num(u, 1)}%</span></div>
    <div class="barra-uso"><i style="width:${Math.min(100, u)}%"></i></div>
    <p class="tenue">Por tipo: ${Object.entries(c.por_tipo || {}).map(([k, v]) => `${esc(k)} ${v}`).join(" · ") || "—"}. Al 80% la mesa baja la frecuencia sola.</p></div>`;
}

let SIM_RES = null;
function licChip() {
  const hoy = HOY(), lim = new Date(Date.now() + 7 * 864e5).toLocaleDateString("en-CA", { timeZone: "America/Argentina/Buenos_Aires" });
  const xs = (ESTADO.estado?.eventos || []).filter((e) => e.tipo === "licitacion" && e.fecha >= hoy && e.fecha <= lim);
  if (!xs.length) return "";
  const hoyN = xs.filter((e) => e.fecha === hoy).length;
  return `<button class="chip ir verde" data-ir="propuestas|#licitaciones-hoy">🏦 ${hoyN ? `${hoyN} licitación${hoyN > 1 ? "es" : ""} hoy` : `${xs.length} licitaci${xs.length > 1 ? "ones" : "ón"} esta semana`} ›</button>`;
}
function cobChip() {
  const hoy = HOY(), lim = new Date(Date.now() + 7 * 864e5).toLocaleDateString("en-CA", { timeZone: "America/Argentina/Buenos_Aires" });
  const xs = (ESTADO.estado?.cobros || []).filter((c) => c.fecha >= hoy && c.fecha <= lim);
  return xs.length ? `<button class="chip ir verde" data-ir="propuestas|#cobros-hoy">💵 ${xs.length} cobro${xs.length > 1 ? "s" : ""} esta semana ›</button>` : "";
}
function pintarResumenHoy() {
  const est = ESTADO.estado || {}, rp = est.riesgo_pais || {}, ind = est.indicadores || {};
  const pend = PROPS.filter((p) => p.decision === "pendiente" && (p.fecha === est.fecha || ["pendiente", "abierta"].includes(p.seguimiento?.estado))).length;
  const ops = Object.values(est.oportunidades || {}).reduce((n, l) => n + l.length, 0);
  const clima = est.clima || "—", t = SIM_RES?.total || {};
  $("#resumen-hoy").innerHTML = `<div class="card resumen">
    <div class="tiras" style="margin-top:0"><button class="chip ir ${clima === "malo" ? "rojo" : clima === "bueno" ? "verde" : "amar"}" data-ir="mercado|#economista">Clima ${esc(clima)} ›</button>
      <button class="chip ir" data-ir="mercado|#indicadores">Riesgo país ${num(rp.valor, 0)} ›</button><button class="chip ir" data-ir="mercado|#indicadores">MEP ${num(ind.mep_al30, 0)} ›</button>${licChip()}${cobChip()}</div>
    <div class="grilla" style="margin-top:10px">
      <button class="met ir" data-ir="propuestas|#titulo-decidir"><span>Para decidir ›</span><b>${pend}</b></button>
      <button class="met ir" data-ir="propuestas|#titulo-ops|ops"><span>Oportunidades ›</span><b>${ops}</b></button>
      <button class="met ir" data-ir="ranking|#simulacion"><span>Simulación (cerradas) ›</span><b style="color:var(--${(t.ganancia || 0) >= 0 ? "verde" : "rojo"})">${t.cerradas ? plata(t.ganancia) : "—"}</b></button>
      <button class="met ir" data-ir="ranking|#simulacion"><span>Abiertas en papel ›</span><b>${SIM_RES ? SIM_RES.abiertas || 0 : "—"}</b></button>
    </div></div>`;
}

// ---------- tus cobros (hoy, mañana, esta semana, el mes) ----------
const plataMon = (v, m) => (m === "USD" ? "US$ " : "$") + num(v);
function pintarCobros() {
  const cs = ESTADO.estado?.cobros || [], box = $("#cobros-hoy");
  if (!box) return;
  if (!cs.length) { box.innerHTML = USUARIO.cartera.length ? "" : ""; return; }
  const hoy = HOY(), d = (n) => new Date(Date.now() + n * 864e5).toLocaleDateString("en-CA", { timeZone: "America/Argentina/Buenos_Aires" });
  const finSem = (() => { const x = new Date(hoy + "T12:00:00"); x.setDate(x.getDate() + (7 - x.getDay()) % 7); return x.toISOString().slice(0, 10); })();
  const grupos = [["Hoy", (c) => c.fecha === hoy], ["Mañana", (c) => c.fecha === d(1)], ["Esta semana", (c) => c.fecha > d(1) && c.fecha <= finSem],
    ["Próximos 30 días", (c) => c.fecha > finSem && c.fecha <= d(30)]];
  const tot = (xs) => { const t = {}; for (const c of xs) if (c.total != null) t[c.moneda] = (t[c.moneda] || 0) + c.total;
    return Object.entries(t).map(([m, v]) => plataMon(v, m)).join(" + ") || "—"; };
  const fila = (c) => `<div class="evento"><span class="ev-ic">💵</span><span><b>${diaTxt(c.fecha)}</b> · <b class="link" data-abrir-debate="${esc(c.ticker)}">${esc(c.ticker)}</b>
    ${c.total != null ? `<b>${plataMon(c.total, c.moneda)}</b> <span class="tenue">(${c.renta ? "renta " + plataMon(c.renta, c.moneda) : ""}${c.renta && c.amortizacion ? " + " : ""}${c.amortizacion ? "amortización " + plataMon(c.amortizacion, c.moneda) : ""} · ${num(c.nominales, 0)} nominales)</span>`
      : `<span class="tenue">${esc(c.descripcion)}</span>`}</span></div>`;
  const bloques = grupos.map(([t, f]) => { const xs = cs.filter(f); return xs.length ? `<p style="margin:10px 0 4px"><b>${t}</b> · ${tot(xs)}</p>${xs.map(fila).join("")}` : ""; }).join("");
  if (!bloques) { box.innerHTML = ""; return; }
  box.innerHTML = `<h2 class="ir" data-ir="lista|#cal-vista">💵 Tus cobros <span class="tenue">· ver calendario ›</span></h2><div class="card">${bloques}
    <p class="tenue">Calculado con tus nominales de "Lo que tengo" y los flujos de cada papel (MAE / cargados). Te aviso al celular el día antes y el día del pago.</p></div>`;
}

let PLAZO = "corto";
function pintarOportunidades() {
  const ops = (ESTADO.estado?.oportunidades || {})[PLAZO] || [];
  const col = { verde: "verde", amarillo: "amar", rojo: "rojo" };
  $("#oportunidades").innerHTML = ops.length ? ops.map((o) => `<div class="card">
    <div class="fila"><div><b style="font-size:17px">${esc(o.ticker)}</b> <span class="tenue">${esc(o.setup)}</span></div>
    <span class="chip ${col[o.semaforo]}">${o.semaforo === "verde" ? "Pasa Riesgo" : o.semaforo === "amarillo" ? "Con cuidado" : "Riesgo la frena"}</span></div>
    <p style="margin:6px 0">${esc(o.motivo)}</p>
    ${o.mesa ? `<p class="tenue">✔ La confirman: ${esc(o.mesa.a_favor.map(nombreAg).join(", "))}</p>` : ""}
    <div class="grilla"><div class="met"><span>Compra límite</span><b>${num(o.plan.entrada)}</b></div>
      <div class="met"><span>Objetivo</span><b style="color:var(--verde)">${num(o.plan.objetivo)} (${pct(o.plan.recompensa_pct, 1)})</b></div>
      <div class="met"><span>Stop</span><b style="color:var(--rojo)">${num(o.plan.stop)} (−${num(o.plan.riesgo_pct, 1)}%)</b></div>
      <div class="met"><span>Gana/arriesga neto</span><b>${num(o.r_neto, 2)}R</b></div></div>
    <p class="tenue">${esc(o.historia)}. Vence ${esc(o.plan.vence)}.</p>
    ${[...(o.riesgo.motivos || []), ...(o.riesgo.avisos || [])].map((m) => `<p class="tenue">• ${esc(m)}</p>`).join("")}
  </div>`).join("") : `<div class="vacio">Ninguna oportunidad confirmada por la mesa en este plazo.${ESTADO.estado?.oportunidades_observadas ? `<br>${ESTADO.estado.oportunidades_observadas} en observación: otros analistas no las confirman, no se muestran.` : ""}</div>`;
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
      ${lectura ? `<p>${esc(lectura)}${x.lectura_ia_hora ? ` <span class="tenue">(lectura de las ${esc(x.lectura_ia_hora)})</span>` : ""}</p>` : ""}<p class="tenue">${esc(x.resumen)}</p>
      <div class="tabla-scroll"><table><tr>${x.columnas.map((c, j) => `<th class="${j ? "n" : ""}">${esc(c)}</th>`).join("")}</tr>
      ${x.filas.map((f) => `<tr>${f.map((v, j) => `<td class="${j ? "n" : ""}">${esc(v)}</td>`).join("")}</tr>`).join("")}</table></div>
      ${x.nota ? `<p class="tenue">${esc(x.nota)}</p>` : ""}</details>`; }).join("");
  $("#informes").innerHTML = html || '<p class="tenue">Los informes aparecen después de la próxima ronda.</p>';
}

function pintarSenales() {
  const f = ($("#filtro-senales").value || "").toLowerCase();
  const ss = (ESTADO.estado?.senales || []).filter((s) => !f || s.ticker.toLowerCase().includes(f) || nombreAg(s.agente).toLowerCase().includes(f));
  const por = {};
  for (const x of ss) (por[x.agente] ||= []).push(x);
  $("#senales").innerHTML = ss.length ? Object.entries(por).map(([ag, xs]) => {
    const up = xs.filter((x) => x.direccion > 0).length, dn = xs.filter((x) => x.direccion < 0).length;
    return `<details class="grupo" ${f ? "open" : ""}><summary><b>${esc(nombreAg(ag))}</b>
      <span class="tenue">${xs.length} ${xs.length === 1 ? "señal" : "señales"}</span>
      ${up ? `<span class="chip verde">▲ ${up}</span>` : ""}${dn ? `<span class="chip rojo">▼ ${dn}</span>` : ""}</summary>
      ${xs.map((x) => `<div class="agente"><span class="chip ${x.direccion > 0 ? "verde" : x.direccion < 0 ? "rojo" : ""} link" data-abrir-debate="${esc(x.ticker)}">${esc(x.ticker)}</span><span>${esc(x.texto)}</span></div>`).join("")}</details>`;
  }).join("") : '<p class="tenue">Sin señales.</p>';
}
$("#filtro-senales").addEventListener("input", pintarSenales);

// documentos de A3/MAE: se abren a través de la mesa (el link directo de SharePoint falla en el celular)
async function abrirDoc(u, n) {
  toast("Bajando el documento…");
  try {
    const r = await fetch(docUrl(u, n), { credentials: "include" });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || r.status);
    const b = await r.blob(), url = URL.createObjectURL(b), a = document.createElement("a");
    a.href = url; a.download = (n || "documento").replace(/[^\w .\-áéíóúñÁÉÍÓÚÑ]/g, "").slice(0, 80) + ".pdf";
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch (e) { toast("No se pudo abrir: " + e.message); }
}
document.addEventListener("click", (ev) => { const b = ev.target.closest("[data-doc]"); if (b) { ev.preventDefault(); abrirDoc(b.dataset.doc, b.dataset.docN || ""); } });
const docUrl = (u, n = "") => (u && u.includes("mercadoabierto.sharepoint.com") ? `/api/doc?u=${encodeURIComponent(u)}&n=${encodeURIComponent(n)}` : u);

// ---------- favoritos (★): se agregan/quitan desde cualquier papel ----------
const esFav = (tk) => (USUARIO.lista || []).some((x) => x.ticker === String(tk).toUpperCase());
function estrella(tk, origen = "") {
  const on = esFav(tk);
  return `<button class="fav ${on ? "on" : ""}" data-fav="${esc(tk)}" data-fav-origen="${esc(origen)}" aria-label="${on ? "Quitar de" : "Agregar a"} favoritos ${esc(tk)}" title="${on ? "Quitar de favoritos" : "Agregar a favoritos"}">${on ? "★" : "☆"}</button>`;
}
document.addEventListener("click", async (ev) => {
  const b = ev.target.closest("[data-fav]"); if (!b) return;
  ev.preventDefault(); ev.stopPropagation();
  const tk = b.dataset.fav.toUpperCase(), i = USUARIO.lista.findIndex((x) => x.ticker === tk);
  if (i >= 0) USUARIO.lista.splice(i, 1);
  else USUARIO.lista.push({ ticker: tk, precio: null, nota: b.dataset.favOrigen ? `Desde ${b.dataset.favOrigen} (${fecha(HOY())})` : "" });
  try { await put("usuario/lista", USUARIO.lista); } catch (x) { toast("No se pudo guardar: " + x.message); return; }
  document.querySelectorAll(`[data-fav="${CSS.escape(b.dataset.fav)}"]`).forEach((x) => { const on = i < 0; x.classList.toggle("on", on); x.textContent = on ? "★" : "☆"; });
  toast(i >= 0 ? `${tk} salió de favoritos` : `${tk} en favoritos: la mesa lo sigue desde la próxima ronda`);
  pintarUsuario(); pintarPronosticos();
}, true);

// ---------- reunión de la mesa (revisión semanal) ----------
function pintarReunion() {
  const r = ESTADO.estado?.reunion, box = $("#reunion");
  if (!box) return;
  if (!r) { box.innerHTML = ""; return; }
  const col = (v) => (v > 0 ? "verde" : v < 0 ? "rojo" : "texto");
  const ag = (r.agentes || []).filter((a) => a.casos >= 5).map((a) => `<tr><td>${esc(a.nombre)}</td><td class="n">${a.casos}</td><td class="n">${num(a.acierto_pct, 0)}%</td>
    <td class="n" style="color:var(--${col(a.promedio_pct)})">${pct(a.promedio_pct, 1)}</td><td class="n">${r.ajustes?.[a.agente] ? `×${num(r.ajustes[a.agente].factor, 2)}` : ""}</td></tr>`).join("");
  const pap = (r.papeles || []).slice(0, 10).map((p) => `<div class="evento"><span class="ev-ic">${p.acerto === true ? "✅" : p.acerto === false ? "❌" : "➖"}</span>
    <span><b class="link" data-abrir-debate="${esc(p.ticker)}">${esc(p.ticker)}</b> ${pct(p.ret, 1)} desde el ${esc(fecha(p.desde))}
    <span class="tenue">· la mesa ${p.mesa > 0 ? "lo veía a favor" : p.mesa < 0 ? "lo veía en contra" : "estaba dividida"}${p.favor.length ? ` · a favor: ${esc(p.favor.join(", "))}` : ""}${p.contra.length ? ` · en contra: ${esc(p.contra.join(", "))}` : ""}</span></span></div>`).join("");
  box.innerHTML = `<h2>🧑‍⚖️ Reunión de la mesa <span class="hora">· ${esc(fecha(r.fecha))}</span></h2><div class="card">
    <p class="tenue">El Jefe y los analistas revisan todo lo que miraron desde el ${esc(fecha(r.desde))} (${r.senales} señales) contra lo que hizo el precio. Se repite cada día al cierre.</p>
    ${(r.lecciones || []).map((l) => `<p>• ${esc(l)}</p>`).join("")}
    ${ag ? `<div class="tabla-scroll"><table><tr><th>Analista</th><th class="n">Señales</th><th class="n">Acierto</th><th class="n">Prom.</th><th class="n">Ajuste</th></tr>${ag}</table></div>
      <p class="tenue">Ajuste = el voto de ese analista sube o baja por una semana según lo que pasó (máximo ±30%). Solo se ajusta a los de corto plazo: a los de meses no se los juzga en una semana.</p>` : ""}
    ${pap ? `<p style="margin-top:10px"><b>Los papeles que más se movieron</b></p>${pap}` : ""}
    ${(r.ciegos || []).length ? `<p class="tenue" style="margin-top:8px">Se nos escaparon: ${r.ciegos.map((c) => `${esc(c.ticker)} ${pct(c.ret, 0)}`).join(" · ")}</p>` : ""}</div>`;
}

// ---------- libreta de pronósticos ----------
const ESTADO_PRON = { se_dio: ["verde", "✅ Se dio"], fallo: ["rojo", "❌ Falló"], no_se_dio: ["", "➖ No se dio"], en_curso: ["amar", "⏳ En curso"], esperando: ["", "🕒 Espera apertura"] };
const ORIGEN_PRON = { anticipador: "Anticipador", anticipo: "Anticipo NY", mundo: "Corresponsal", jefe: "Jefe", oportunidad: "Oportunidad" };
let FILTRO_PRON = "fav";
function ultimoPronostico(tk) { return (ESTADO.estado?.pronosticos || []).find((x) => x.ticker === tk); }
function filaPron(x) {
  const [col, eti] = ESTADO_PRON[x.estado] || ["", x.estado];
  const dir = x.dir > 0 ? "sube" : "baja";
  return `<div class="item pron"><div class="item-cab">${estrella(x.ticker, ORIGEN_PRON[x.origen])}<b class="link" data-abrir-debate="${esc(x.ticker)}">${esc(x.ticker)}</b>
      <span class="tenue">${esc(ORIGEN_PRON[x.origen] || x.origen)} · ${esc(fecha(x.fecha))}</span><span class="chip ${col}">${eti}</span></div>
    <div class="item-det">Dijo: <b>${dir} ${num(x.objetivo_pct, 1)}%</b>${x.stop_pct ? ` (stop -${num(x.stop_pct, 1)}%)` : ""} hasta el ${esc(fecha(x.vence))}
      ${x.ref ? ` · desde ${num(x.ref)} → ahora ${num(x.ultimo ?? x.ref)} (<b style="color:var(--${x.ahora_pct > 0 ? "verde" : x.ahora_pct < 0 ? "rojo" : "texto"})">${pct(x.ahora_pct, 1)}</b> a favor) · mejor ${pct(x.mejor, 1)} · peor ${pct(x.peor, 1)}` : " · toma el precio en la primera ronda con BYMA abierto"}</div>
    ${x.texto ? `<div class="item-det tenue">${esc(x.texto)}</div>` : ""}</div>`;
}
function pintarPronosticos() {
  const box = $("#pronosticos"); if (!box) return;
  const xs = ESTADO.estado?.pronosticos || [];
  if (!xs.length) { box.innerHTML = '<p class="tenue">Todavía no hay pronósticos anotados: la libreta arranca con la próxima ronda.</p>'; return; }
  const res = {};
  for (const x of xs) { const r = (res[x.origen] ||= { se_dio: 0, fallo: 0, no_se_dio: 0, abiertos: 0, suma: 0 });
    if (["se_dio", "fallo", "no_se_dio"].includes(x.estado)) { r[x.estado]++; r.suma += x.estado === "se_dio" ? x.objetivo_pct : x.estado === "fallo" ? -(x.stop_pct || 0) : x.ahora_pct || 0; } else r.abiertos++; }
  const tabla = `<div class="tabla-scroll"><table><tr><th>Quién</th><th class="n">Se dio</th><th class="n">No / falló</th><th class="n">Acierto</th><th class="n">Prom.</th><th class="n">Abiertos</th></tr>
    ${Object.entries(res).map(([o, r]) => { const c = r.se_dio + r.fallo + r.no_se_dio; return `<tr><td>${esc(ORIGEN_PRON[o] || o)}</td><td class="n">${r.se_dio}</td><td class="n">${r.no_se_dio + r.fallo}</td>
      <td class="n">${c ? num(r.se_dio / c * 100, 0) + "%" : "—"}</td><td class="n">${c ? pct(r.suma / c, 1) : "—"}</td><td class="n">${r.abiertos}</td></tr>`; }).join("")}</table></div>`;
  const filtros = [["fav", "⭐ Favoritos"], ["abiertos", "⏳ En curso"], ["cerrados", "Cerrados"], ["todos", "Todos"]];
  const pasa = (x) => FILTRO_PRON === "fav" ? esFav(x.ticker) : FILTRO_PRON === "abiertos" ? ["en_curso", "esperando"].includes(x.estado)
    : FILTRO_PRON === "cerrados" ? ["se_dio", "fallo", "no_se_dio"].includes(x.estado) : true;
  const lista = xs.filter(pasa);
  box.innerHTML = `<div class="card">${tabla}<p class="tenue">Acierto = llegó al objetivo dentro del plazo. Prom. = resultado promedio a favor del pronóstico.</p></div>
    <div class="tiras" id="filtro-pron">${filtros.map(([k, t]) => `<button class="chico ${FILTRO_PRON === k ? "prim" : ""}" data-fpron="${k}">${t}</button>`).join("")}</div>
    ${lista.length ? lista.slice(0, 60).map(filaPron).join("") : `<p class="tenue">${FILTRO_PRON === "fav" ? "Ninguno de tus favoritos tiene pronósticos todavía. Marcá ☆ en los papeles que te interesen." : "Nada para mostrar con este filtro."}</p>`}`;
  box.querySelectorAll("[data-fpron]").forEach((b) => b.onclick = () => { FILTRO_PRON = b.dataset.fpron; pintarPronosticos(); });
}

// ---------- alertas de nivel de cada favorito ----------
function alertasItem(x, i) {
  const disp = ESTADO.estado?.alertas_disparadas || {};
  const filas = (x.alertas || []).map((a, j) => { const d = disp[a.id], mon = a.moneda === "USD" ? "US$ " : "$";
    return `<div class="alerta-niv ${d ? "hecha" : ""}">🔔 ${a.tipo === "baja" ? "Si baja de" : "Si sube de"} <b>${mon}${num(a.nivel)}</b>${a.moneda === "USD" ? ' <span class="tenue">(en EE.UU.)</span>' : ""}
      ${d ? `<span class="chip verde">avisó el ${esc(fecha(d.fecha))} ${esc(d.hora)} a ${mon}${num(d.precio)}</span>` : '<span class="chip">activa</span>'}${a.nota ? ` <span class="tenue">${esc(a.nota)}</span>` : ""}
      <button class="quitar" data-quitar-alerta="${i},${j}" aria-label="Borrar alerta">✕</button></div>`; }).join("");
  return `<div class="item-det">${filas}
    <details class="nueva-alerta"><summary>＋ Avisarme si…</summary>
      <form class="fila-form" data-form-alerta="${i}"><select name="tipo"><option value="baja">baja de</option><option value="sube">sube de</option></select>
        <input name="nivel" placeholder="Precio" inputmode="decimal" required>
        <select name="moneda"><option value="ARS">$ (BYMA)</option><option value="USD">US$ (en EE.UU.)</option></select><button>Guardar</button></form>
    </details></div>`;
}

// ---------- Mi lista, cartera, capital ----------
function pintarUsuario() {
  const precios = ESTADO.estado?.precios || {};
  const color = (v) => (v > 0 ? "verde" : v < 0 ? "rojo" : "");
  $("#mi-lista").innerHTML = USUARIO.lista.length ? USUARIO.lista.map((x, i) => {
    const q = precios[x.ticker] || {}, dist = q.ultimo && x.precio ? (q.ultimo / x.precio - 1) * 100 : null;
    return `<div class="item"><div class="item-cab"><b class="link" data-abrir-debate="${esc(x.ticker)}">${esc(x.ticker)}</b>
        <span class="item-precio">${num(q.ultimo)} <span class="chip ${color(q.variacion)}">${pct(q.variacion)}</span></span>
        <button class="quitar" data-quitar-lista="${i}" aria-label="Quitar ${esc(x.ticker)}">✕</button></div>
      ${(() => { const pr = ultimoPronostico(x.ticker); if (!pr) return ""; const [c, e] = ESTADO_PRON[pr.estado] || ["", pr.estado];
        return `<div class="item-det"><span class="chip ${c}">${e}</span> ${esc(ORIGEN_PRON[pr.origen] || pr.origen)} (${esc(fecha(pr.fecha))}): ${pr.dir > 0 ? "sube" : "baja"} ${num(pr.objetivo_pct, 1)}%${pr.ref ? ` · va ${pct(pr.ahora_pct, 1)}` : ""}</div>`; })()}
      ${alertasItem(x, i)}
      <div class="item-det">${x.precio ? `Tu precio ${num(x.precio)} · ${dist === null ? "sin cotización" : Math.abs(dist) < 0.3 ? "<b>¡en tu precio!</b>" : `está ${num(Math.abs(dist), 1)}% ${dist > 0 ? "arriba" : "abajo"}`}` : "Sin precio objetivo"}${x.nota ? ` · ${esc(x.nota)}` : ""}</div></div>`;
  }).join("") : '<p class="tenue">Agregá tickers para que la mesa los siga.</p>';
  $("#cartera").innerHTML = USUARIO.cartera.length ? USUARIO.cartera.map((x, i) => {
    const u = precios[x.ticker]?.ultimo, r = u && x.precio ? (u / x.precio - 1) * 100 : null;
    return `<div class="item"><div class="item-cab"><b class="link" data-abrir-debate="${esc(x.ticker)}">${esc(x.ticker)}</b>
        <span class="item-precio">${num(u)}${r === null ? "" : ` <span class="chip ${color(r)}">${pct(r)}</span>`}</span>
        <button class="quitar" data-quitar-cartera="${i}" aria-label="Quitar ${esc(x.ticker)}">✕</button></div>
      <div class="item-det">${num(x.cantidad, 0)} nominales · compra ${num(x.precio)}${u ? "" : " · sin cotización en la ronda"}</div>
      ${(() => { const m = (ESTADO.estado?.ministro?.cartera || []).find((y) => y.ticker === x.ticker.toUpperCase());
        return m ? `<div class="item-det">🏛️ <b>Ministro:</b> ${esc(m.texto)}</div>` : ""; })()}
      ${(() => { const o = (ESTADO.estado?.opinion_cartera || {})[x.ticker.toUpperCase()]; if (!o) return "";
        return `<div class="item-det"><span class="chip ${o.veredicto === "a favor" ? "verde" : o.veredicto === "en contra" ? "rojo" : ""}">La mesa: ${esc(o.veredicto)}</span> ${o.favor} a favor · ${o.contra} en contra${o.balance ? ` · <b>balance el ${esc(fecha(o.balance))}</b>` : ""}</div>${o.principal ? `<div class="item-det">${esc(o.principal)}</div>` : ""}`; })()}</div>`;
  }).join("") : '<p class="tenue">Sin posiciones cargadas.</p>';
  const cap = USUARIO.capital || {};
  $("#capital-info").textContent = cap.monto_ars ? `1R = ${num(cap.monto_ars * (cap.riesgo_pct || 1) / 100, 0)} pesos de pérdida máxima por operación.` : "Si no lo cargás, se usa el de la configuración.";
  document.querySelectorAll("[data-quitar-alerta]").forEach((b) => b.onclick = async () => {
    const [i, j] = b.dataset.quitarAlerta.split(",").map(Number); USUARIO.lista[i].alertas.splice(j, 1);
    await put("usuario/lista", USUARIO.lista); pintarUsuario(); toast("Alerta borrada"); });
  document.querySelectorAll("[data-form-alerta]").forEach((f) => f.onsubmit = async (ev) => {
    ev.preventDefault(); const i = +f.dataset.formAlerta, d = leerForm(f), nivel = aNum(d.nivel);
    if (!nivel) return toast("Poné el precio");
    (USUARIO.lista[i].alertas ||= []).push({ id: Date.now().toString(36), tipo: d.tipo, nivel, moneda: d.moneda, creada: HOY() });
    await put("usuario/lista", USUARIO.lista); pintarUsuario(); toast("Alerta guardada: la mesa la revisa en cada ronda y te avisa al celular"); });
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
  for (const pos of USUARIO.cartera) { const tk = pos.ticker.toUpperCase(), on = USUARIO.ons[tk] || ESTADO.estado?.flujos_bonos?.[tk]; if (!on) continue;
    for (const f of flujo(on, pos.cantidad, HOY())) filas.push({ ...f, ticker: pos.ticker, moneda: on.moneda }); }
  filas.sort((a, b) => a.fecha.localeCompare(b.fecha));
  const porMes = {}; for (const f of filas) { const m = f.fecha.slice(0, 7); porMes[m] = (porMes[m] || 0) + f.total; }
  const dias = (f) => Math.round((new Date(f) - new Date(HOY())) / 864e5);
  $("#calendario").innerHTML = filas.length ? `<div class="tiras">${Object.entries(porMes).slice(0, 6).map(([m, v]) => `<span class="chip">${MESES_TXT[+m.slice(5, 7) - 1]} ${m.slice(2, 4)}: ${num(v)}</span>`).join("")}</div>
    <div class="tabla-scroll"><table><tr><th>Fecha</th><th>Papel</th><th class="n">Renta</th><th class="n">Amort.</th><th class="n">Total</th><th class="n">Faltan</th></tr>
    ${filas.slice(0, 40).map((f) => `<tr><td>${fechaLarga(f.fecha)}</td><td>${esc(f.ticker)} <span class="tenue">${esc(f.moneda || "")}</span></td><td class="n">${num(f.interes)}</td><td class="n">${num(f.amortizacion)}</td><td class="n"><b>${num(f.total)}</b></td><td class="n">${dias(f.fecha)} d</td></tr>`).join("")}</table></div>`
    : '<p class="tenue">Cargá en "Lo que tengo" tus bonos, ONs y letras con sus nominales: la mesa baja sola sus flujos de pago (MAE) y calcula cuánto cobrás.</p>';
  pintarEventos();
  pintarMAE();
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
    ${fl.map((f) => `<tr><td>${fechaLarga(f.fecha)}</td><td class="n">${num(f.interes)}</td><td class="n">${num(f.amortizacion)}</td><td class="n"><b>${num(f.total)}</b></td></tr>`).join("")}</table></div>
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

// ---------- cartel de recomendación (en cualquier pestaña) ----------
let VISTOS = new Set(), AVISADOS = null;
try { VISTOS = new Set(JSON.parse(localStorage.getItem("mesa_vistos") || "[]")); } catch (_) {}
const guardarVistos = () => { try { localStorage.setItem("mesa_vistos", JSON.stringify([...VISTOS].slice(-200))); } catch (_) {} };
function minutosDesde(fechaP, horaP) {
  if (fechaP !== HOY()) return null;
  const ba = new Date(new Date().toLocaleString("en-US", { timeZone: "America/Argentina/Buenos_Aires" }));
  const [h, m] = String(horaP || "0:0").split(":").map(Number);
  return ba.getHours() * 60 + ba.getMinutes() - (h * 60 + m);
}
function sonar() {
  try { navigator.vibrate?.([200, 100, 200]); } catch (_) {}
  try { const c = new (window.AudioContext || window.webkitAudioContext)(), o = c.createOscillator(), g = c.createGain();
    o.frequency.value = 880; o.connect(g); g.connect(c.destination); g.gain.setValueAtTime(0.15, c.currentTime);
    o.start(); g.gain.exponentialRampToValueAtTime(0.0001, c.currentTime + 0.6); o.stop(c.currentTime + 0.6); } catch (_) {}
}
function pintarAviso() {
  const precios = ESTADO.estado?.precios || {};
  // 1) propuestas nuevas del Jefe para decidir  2) consejos de seguimiento importantes de hoy
  const nuevas = PROPS.filter((p) => p.decision === "pendiente" && p.fecha === HOY() && !VISTOS.has(p.id));
  const consejos = PROPS.filter((p) => p.decision === "aprobada" && ["salir", "subir_stop", "antes_balance", "cancelar"].includes(p.seguimiento?.consejo?.accion)
    && !VISTOS.has(p.id + "|" + p.seguimiento.consejo.accion));
  const radarAltas = (ESTADO.estado?.radar || []).filter((r) => r.severidad === "alta" && ESTADO.estado?.fecha === HOY() && !VISTOS.has("radar|" + HOY() + "|" + r.ticker));
  const box = $("#aviso-global");
  if (!nuevas.length && !consejos.length && !radarAltas.length) { box.style.display = "none"; document.title = "Mesa de dinero"; return; }
  const items = nuevas.map((p) => {
    const pl = p.plan, ult = precios[p.ticker]?.ultimo, min = minutosDesde(p.fecha, p.hora);
    const lejos = ult && ult > pl.entrada * 1.01;
    return `<div class="aviso-item"><div><b>🔔 El Jefe recomienda COMPRAR ${esc(p.ticker)}</b> con límite <b>${num(pl.entrada)}</b>
        · objetivo ${num(pl.objetivo)} · stop ${num(pl.stop)}${p.cantidad_sugerida ? ` · ${num(p.cantidad_sugerida, 0)} unidades` : ""}</div>
      <div class="tenue">${min !== null ? (min < 1 ? "recién" : `hace ${min} min`) : esc(p.hora)} · válida hoy${ult ? ` · ahora ${num(ult)}` : ""}${lejos ? " · <b>el precio se alejó: no lo persigas, dejá la orden límite</b>" : ""}</div>
      <div class="fila-form" style="margin-top:6px"><button class="chico prim" data-ir-prop="${esc(p.id)}">Ver y decidir</button><button class="chico" data-visto="${esc(p.id)}">Entendido</button></div></div>`;
  }).concat(consejos.map((p) => `<div class="aviso-item"><div><b>⚠️ ${esc(p.ticker)}: ${esc(CONSEJO_TXT[p.seguimiento.consejo.accion])}</b></div>
      <div class="tenue">${esc(p.seguimiento.consejo.texto)} (${esc(p.seguimiento.consejo.hora || "")})</div>
      <div class="fila-form" style="margin-top:6px"><button class="chico prim" data-ir-prop="${esc(p.id)}">Ver</button><button class="chico" data-visto="${esc(p.id + "|" + p.seguimiento.consejo.accion)}">Entendido</button></div></div>`))
    .concat(radarAltas.slice(0, 3).map((r) => `<div class="aviso-item"><div><b>📡 Radar: ${esc(r.texto)}</b></div>
      <div class="tenue">${esc(r.conclusion)} · desde las ${esc(r.primera || r.hora)}</div>
      <div class="fila-form" style="margin-top:6px"><button class="chico prim" data-ir-radar="1">Ver análisis</button><button class="chico" data-visto="${esc("radar|" + HOY() + "|" + r.ticker)}">Entendido</button></div></div>`));
  box.innerHTML = items.join("");
  box.style.display = "block";
  document.title = `(${items.length}) Mesa de dinero`;
  const ids = [...nuevas.map((p) => p.id), ...consejos.map((p) => p.id + "|" + p.seguimiento.consejo.accion), ...radarAltas.map((r) => "radar|" + r.ticker)].join(",");
  if (AVISADOS !== null && ids !== AVISADOS && ids) sonar();  // llegó algo nuevo con la web abierta
  AVISADOS = ids;
  box.querySelectorAll("[data-visto]").forEach((b) => b.onclick = () => { VISTOS.add(b.dataset.visto); guardarVistos(); pintarAviso(); });
  box.querySelectorAll("[data-ir-radar]").forEach((b) => b.onclick = () => { irA("propuestas"); setTimeout(() => $("#radar")?.scrollIntoView({ behavior: "smooth" }), 100); });
  box.querySelectorAll("[data-ir-prop]").forEach((b) => b.onclick = () => { irA("propuestas"); setTimeout(() => document.querySelector(`[data-tarjeta="${b.dataset.irProp}"]`)?.scrollIntoView({ behavior: "smooth", block: "center" }), 100); });
}

// ---------- anticipos ----------
function pintarAnticipos() {
  const e = ESTADO.estado || {}, at = e.anticipos || [], li = e.anticipo_lista || {}, es = e.anticipo_estadistica;
  if (!at.length && !(li.lista || []).length) { $("#anticipos").innerHTML = ""; return; }
  const col = (v) => (v > 0 ? "verde" : "rojo");
  const tablaAt = at.length ? `<p class="tenue">Lo que su acción ya hizo en Nueva York (incluye el pre-market) y el CEDEAR todavía no. ${at.some((a) => a.antes_de_abrir) ? "<b>BYMA todavía no abrió:</b> esto es lo que debería pasar a las 11." : ""}</p>
    <div class="tabla-scroll"><table><tr><th>CEDEAR</th><th class="n">En NY</th><th class="n">CEDEAR</th><th class="n">Le falta</th></tr>
    ${at.slice(0, 12).map((a) => `<tr><td>${estrella(a.ticker, "Anticipo NY")}<span class="link" data-abrir-debate="${esc(a.ticker)}">${esc(a.ticker)}</span></td><td class="n">${pct(a.us, 1)}</td>
      <td class="n">${a.antes_de_abrir ? "<span class='tenue'>sin abrir</span>" : pct(a.cedear, 1)}</td><td class="n" style="color:var(--${col(a.atraso)})"><b>${pct(a.atraso, 1)}</b></td></tr>`).join("")}</table></div>` : "";
  const p = li.prueba || {};
  const tablaLi = (li.lista || []).length ? `<p class="tenue" style="margin-top:10px"><b>Para los próximos días</b> (lista del cierre ${esc(fecha(li.fecha))}): papeles con las señales que suelen aparecer antes de una suba de 5% o más en la semana.
      ${p.base_pct ? `En la prueba con datos que no vio, de cada 100 marcados subieron así ${num(p.top10_pct, 0)}, contra ${num(p.base_pct, 0)} al azar.` : ""}${li.activo ? "" : " (todavía no supera la prueba: solo informativo)"}</p>
    ${li.lista.slice(0, 10).map((x) => { const pr = (ESTADO.estado?.pronosticos || []).find((p) => p.origen === "anticipador" && p.ticker === x.ticker && p.fecha === li.fecha);
      const [c, e] = pr ? ESTADO_PRON[pr.estado] || ["", ""] : ["", ""];
      return `<div class="agente"><b>${estrella(x.ticker, "Anticipador")}<span class="link" data-abrir-debate="${esc(x.ticker)}">${esc(x.ticker)}</span><br><span class="tenue">${num(x.prob * 100, 0)}%</span></b>
        <span>${esc((x.razones || []).join(" · ") || "combinación de precursores")}${x.fr_contra ? ' <span class="chip rojo">entre los más débiles: pesa la mitad</span>' : ""}${pr ? `<br><span class="chip ${c}">${e}</span> ${pr.ref ? `desde ${num(pr.ref)}: va ${pct(pr.ahora_pct, 1)}, mejor ${pct(pr.mejor, 1)}` : ""}` : ""}</span></div>`; }).join("")}
    <p><button class="chico" data-ir-pron>📋 Ver cómo van todos los pronósticos</button></p>` : "";
  const pl = es?.plazos?.al_cierre;
  const est = pl?.casos ? `<p class="tenue" style="margin-top:8px">Estadística propia de los anticipos (desde ${esc(fecha(es.desde))}): acertaron ${num(pl.aciertos / pl.casos * 100, 0)}% de ${pl.casos}, ${pct(pl.suma_ret / pl.casos, 2)} promedio hasta el cierre.</p>` : "";
  $("#anticipos").innerHTML = `<h2>⏩ Anticipos <span class="hora">· ${esc(e.hora || "")}</span></h2><div class="card eco">${tablaAt}${tablaLi}${est}</div>`;
}

// ---------- radar del mercado ----------
const TIPO_RADAR = { volumen: "volumen anormal", precio: "movimiento fuerte", adr: "ADR despegado", macro: "macro" };
function pintarRadar() {
  const rs = ESTADO.estado?.radar || [];
  if (!rs.length) { $("#radar").innerHTML = ""; return; }
  $("#radar").innerHTML = `<h2>📡 Radar del mercado <span class="hora">· ${esc(ESTADO.estado?.hora || "")}</span></h2>
    <p class="tenue">Todo lo anormal que vieron los analistas en esta ronda, con su análisis.</p>` + rs.map((r) => `
    <details class="grupo radar ${r.severidad}"><summary><span class="chip ${r.severidad === "alta" ? "rojo" : "amar"}">${r.severidad === "alta" ? "Alta" : "Media"}</span>
      ${r.grupo !== "macro" ? estrella(r.ticker, "Radar") : ""}<b>${esc(r.ticker)}</b> <span class="tenue">${(r.tipos || [r.tipo]).map((t) => TIPO_RADAR[t] || t).join(" + ")} · desde las ${esc(r.primera || r.hora)}</span></summary>
      <p>${esc(r.texto)}</p>
      <p><b>¿Qué pasa?</b> ${esc(r.conclusion)}</p>
      ${r.grupo !== "macro" ? `<p class="tenue">${esc(r.lectura)} (${r.favor} a favor, ${r.contra} en contra)</p>` : ""}
      ${(r.opiniones || []).map((o) => `<div class="agente"><b>${esc(o.agente)}</b><span><span class="chip ${o.dir > 0 ? "verde" : o.dir < 0 ? "rojo" : ""}">${o.dir > 0 ? "▲" : o.dir < 0 ? "▼" : "="}</span> ${esc(o.texto)}</span></div>`).join("")}
      ${(r.noticias || []).length ? `<p class="tenue"><b>Noticias:</b></p>${r.noticias.map((n) => `<p class="tenue">• ${n.link ? `<a href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.titulo)}</a>` : esc(n.titulo)}</p>`).join("")}` : ""}
      ${(r.eventos || []).map((e) => `<p class="tenue">📅 ${esc(fecha(e.fecha))}: ${esc(e.nombre)}</p>`).join("")}
      ${r.grupo !== "macro" ? `<button class="chico" data-abrir-debate="${esc(r.ticker)}">Ver debate completo</button>` : ""}
    </details>`).join("");
}

// ---------- economista ----------
const CAT_ECO = { acciones: "Acciones locales", bancos: "Bancos", energia: "Energía", utilities: "Servicios públicos", bonos_usd: "Bonos en dólares", cedears: "CEDEARs", pesos: "Pesos" };
function pintarEconomista() {
  const r = ESTADO.estado?.economista;
  if (!r) { $("#economista").innerHTML = ""; return; }
  const inc = Object.entries(r.inclinacion || {}).sort((a, b) => b[1] - a[1]);
  $("#economista").innerHTML = `<div class="card eco"><div class="fila"><b>🎓 La clase del Economista</b><span class="tenue">${esc(fecha(r.fecha))}</span></div>
    <p style="font-weight:600;margin:8px 0">${esc(r.titulo)}</p>
    <div class="tiras">${inc.map(([k, v]) => `<span class="chip ${v >= 0.4 ? "verde" : v <= -0.4 ? "rojo" : ""}">${esc(CAT_ECO[k] || k)} ${v > 0 ? "▲" : v < 0 ? "▼" : "="}</span>`).join("")}</div>
    ${(r.clase || []).map((x) => `<p>${esc(x)}</p>`).join("")}
    ${(r.ensena || []).length ? `<p class="tenue"><b>Lo que les enseña hoy al resto:</b></p>${r.ensena.map((x) => `<p class="tenue">• ${esc(x)}</p>`).join("")}` : ""}
    <p class="tenue">${r.ensenanza_activa ? "Así ajusta a la mesa: a las señales de los demás que van con este contexto se les cree hasta 25% más, y a las que van en contra, hasta 25% menos." : "⏸ " + esc(r.ensenanza_motivo || "Su enseñanza está en pausa hasta que la historia muestre que sirve.")}</p></div>`;
}

function pintarWallStreet() {
  const r = ESTADO.estado?.wallstreet;
  if (!r || !r.clase?.length) { $("#wallstreet").innerHTML = ""; return; }
  const col = r.riesgo >= 0.5 ? "verde" : r.riesgo <= -0.4 ? "rojo" : "amar";
  $("#wallstreet").innerHTML = `<div class="card eco"><div class="fila"><b>🗽 La clase de Wall Street (CEDEARs)</b><span class="chip ${col}">${esc(r.titulo)}</span></div>
    ${r.clase.map((x) => `<p>${esc(x)}</p>`).join("")}
    ${(r.ensena || []).length ? `<p class="tenue"><b>Lo que les enseña hoy al resto:</b></p>${r.ensena.map((x) => `<p class="tenue">• ${esc(x)}</p>`).join("")}` : ""}
    <p class="tenue">Opina en los CEDEARs con tendencia (promedio de 200 ruedas) y momentum de 12 meses en dólares. ${r.ensenanza_activa ? esc(r.ensenanza_motivo) : "⏸ " + esc(r.ensenanza_motivo || "")}</p>
    <p class="tenue">Datos de Wall Street al cierre del ${esc(fecha(r.fecha))}.</p></div>`;
}

function pintarCripto() {
  const r = ESTADO.estado?.cripto;
  if (!r || !r.clase?.length) { $("#cripto").innerHTML = ""; return; }
  const est = r.btc?.estado, col = est === "alcista" ? "verde" : est === "bajista" ? "rojo" : "amar";
  $("#cripto").innerHTML = `<div class="card eco"><div class="fila"><b>₿ La visión Cripto</b><span class="chip ${col}">${esc(r.titulo)}</span></div>
    ${r.clase.map((x) => `<p>${esc(x)}</p>`).join("")}
    ${(r.ensena || []).map((x) => `<p class="tenue">• ${esc(x)}</p>`).join("")}
    <p class="tenue">Agente a prueba: si con los datos no demuestra que aporta, se discontinúa.</p></div>`;
}

const NOMBRE_GRUPO = { soberanos: "Bonos soberanos", ons: "ONs", letras: "Letras", bonos: "Bonos" };
function pintarMAE() {
  const r = ESTADO.estado?.mae, dias = ESTADO.estado?.mae_dias || [];
  if (!r && !dias.length) { $("#mae").innerHTML = ""; return; }
  const res = r?.resumen || {};
  const tablaRes = Object.keys(res).length ? `<div class="tabla-scroll"><table><tr><th>Ahora</th><th class="n">Diferencia típica</th><th class="n">9 de cada 10, menos de</th><th class="n">Más de 1%</th><th class="n">Papeles</th></tr>
    ${Object.entries(res).map(([g, x]) => `<tr><td>${esc(NOMBRE_GRUPO[g] || g)}</td><td class="n">${num(x.mediana, 2)}%</td><td class="n">${num(x.p90, 2)}%</td><td class="n">${x.mayor_1pct}</td><td class="n">${x.n}</td></tr>`).join("")}</table></div>` : "";
  const pares = (r?.pares || []).filter((p) => Math.abs(p.dif) >= 0.5).slice(0, 10);
  const tablaPares = pares.length ? `<p class="tenue" style="margin-top:10px"><b>Mayores diferencias</b> (con volumen en los dos mercados). Negativo = más barato en MAE.</p>
    <div class="tabla-scroll"><table><tr><th>Papel</th><th class="n">MAE</th><th class="n">BYMA</th><th class="n">Diferencia</th></tr>
    ${pares.map((p) => `<tr><td><span class="link" data-abrir-debate="${esc(p.ticker)}">${esc(p.ticker)}</span> <span class="tenue">${esc(p.plazo_mae)}</span></td><td class="n">${num(p.mae, 2)}</td><td class="n">${num(p.byma, 2)}</td>
      <td class="n" style="color:var(--${p.dif < 0 ? "verde" : "rojo"})"><b>${pct(p.dif, 2)}</b></td></tr>`).join("")}</table></div>` : '<p class="tenue">Ahora no hay diferencias de 0,5% o más con volumen en los dos mercados.</p>';
  const hist = dias.length ? `<p class="tenue" style="margin-top:10px"><b>Al cierre de cada día</b> (diferencia típica): ${dias.slice(-10).reverse().map((d) =>
    `${esc(fecha(d.fecha))}: ${Object.entries(d.resumen).map(([g, x]) => `${esc(NOMBRE_GRUPO[g] || g)} ${num(x.mediana, 2)}%`).join(", ")}`).join(" · ")}</p>` : "";
  $("#mae").innerHTML = `<div class="card eco"><div class="fila"><b>⚖️ MAE contra BYMA</b><span class="tenue">${esc(r?.hora || "")}</span></div>
    <p class="tenue">El mismo bono o la misma ON cotiza en los dos mercados. Si la diferencia es grande y hay volumen, el radar avisa: conviene comprar donde está más barato (o es un precio viejo: mirar las puntas).</p>
    ${tablaRes}${tablaPares}${hist}</div>`;
}

const NOMBRE_REGLA_MIN = { acumula: "Acumula reservas", pierde: "Pierde reservas", tasa_real_alta: "Tasa real alta", tasa_real_negativa: "Tasa real negativa",
  inflacion_baja: "Inflación bajando", dolar_acelera: "Dólar acelerando", pago_cerca_con_reservas: "Pago de deuda cerca, con reservas" };
function pintarMinistro() {
  const r = ESTADO.estado?.ministro, box = $("#ministro");
  if (!box) return;
  if (!r) { box.innerHTML = ""; return; }
  const f = r.foto || {}, n0 = (v, d = 0) => (v == null ? "—" : num(v, d));
  const ind = [["Reservas BCRA", `US$ ${n0(f.reservas)} M`, f.reservas_20d != null ? `${f.reservas_20d >= 0 ? "+" : ""}${n0(f.reservas_20d)} M en 20 ruedas` : ""],
    ["Compras del BCRA", f.compras_20d != null ? `US$ ${n0(f.compras_20d)} M` : "—", "últimas 20 ruedas"],
    ["Tasa real", f.tasa_real != null ? `${num(f.tasa_real, 1)} pp` : "—", f.tamar ? `TAMAR ${num(f.tamar, 1)}% − inflación esperada ${num(f.expectativa, 1)}%` : ""],
    ["Inflación", f.inflacion != null ? `${num(f.inflacion, 1)}% mensual` : "—", f.inflacion_tendencia != null ? (f.inflacion_tendencia < 0 ? "bajando" : f.inflacion_tendencia > 0 ? "subiendo" : "estable") : ""],
    ["Dólar mayorista", f.tc ? `$${n0(f.tc, 2)}` : "—", f.tc_20d_pct != null ? `${pct(f.tc_20d_pct, 1)} en 20 ruedas` : ""],
    ["Próximo pago de deuda", f.pago_deuda ? fecha(f.pago_deuda) : "—", f.dias_pago_deuda != null ? `faltan ${f.dias_pago_deuda} días` : ""],
    ...(f.rollover != null ? [["Rollover del Tesoro", `${num(f.rollover, 0)}%`, f.rollover < 100 ? "libera pesos al mercado" : "absorbe pesos"]] : [])];
  const reglas = (r.reglas || []).map((x) => `<p>• ${esc(x.texto)} <span class="chip ${x.estado ? "verde" : x.estado === false ? "" : "amar"}">${x.estado ? "probado: vota" : x.estado === false ? "solo dato" : "a prueba"}</span></p>`).join("");
  const pr = Object.entries(r.prueba || {});
  const tabla = pr.length ? `<div class="tabla-scroll"><table><tr><th>Regla</th><th class="n">Acierta</th><th class="n">Prom. 20 ruedas</th><th class="n">Casos</th></tr>
    ${pr.map(([k, x]) => `<tr><td>${esc(NOMBRE_REGLA_MIN[k] || k)}${x.activa ? " ✅" : ""}</td><td class="n">${num(x.acierto, 0)}%</td><td class="n">${pct(x.promedio, 1)}</td><td class="n">${x.casos}</td></tr>`).join("")}</table></div>` : "";
  const tit = (r.titulares || []).slice(0, 4).map((n) => `<div class="evento"><span class="ev-ic">📰</span><span>${n.link ? `<a href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.titulo)}</a>` : esc(n.titulo)}</span></div>`).join("");
  box.innerHTML = `<div class="card eco"><div class="fila"><b>🏛️ El Ministro</b><span class="tenue">política económica · BCRA ${esc(fecha(f.fecha || ""))}</span></div>
    <p class="tenue">Mira el mercado como el Ministerio de Economía: reservas, compras del BCRA, tasa real, inflación, dólar y pagos de deuda. Lo que ve lo comparte con toda la mesa.</p>
    <div class="grilla">${ind.map(([t, v, d]) => `<div class="met"><span>${t}</span><b>${v}</b><span>${esc(d)}</span></div>`).join("")}</div>
    ${reglas ? `<p style="margin-top:10px"><b>Lo que hoy le dice a la mesa</b></p>${reglas}` : '<p class="tenue" style="margin-top:10px">Hoy ninguna señal de política económica fuerte.</p>'}
    ${tabla ? `<p class="tenue" style="margin-top:10px"><b>Probado con la historia</b> (cada regla, a 20 ruedas): solo votan las que ganaron más que la comisión.</p>${tabla}` : ""}
    ${(r.cartera || []).length ? `<p style="margin-top:10px"><b>Tu cartera, según el Ministro</b></p>${r.cartera.map((c) => `<p class="tenue">• <b class="link" data-abrir-debate="${esc(c.ticker)}">${esc(c.ticker)}</b>: ${esc(c.texto)}</p>`).join("")}` : ""}
    ${tit ? `<p class="tenue" style="margin-top:10px"><b>Lo último del Ministro</b></p>${tit}` : ""}</div>`;
}

const NOMBRE_TEMA = { empresa_rumor: "Rumores de empresas", empresa_hecho: "Noticias de empresas" };
function pintarMundo() {
  const r = ESTADO.estado?.mundo;
  if (!r) { $("#mundo").innerHTML = ""; return; }
  const link = (n) => n.link ? `<a href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.titulo)}</a>` : esc(n.titulo);
  const chips = (ef) => Object.entries(ef).map(([tk, d]) => `<span class="chip ${d > 0 ? "verde" : "rojo"}">${esc(tk)} ${d > 0 ? "▲" : "▼"}</span>`).join(" ");
  const temas = (r.temas || []).map((t) => `<div class="tema-mundo"><b>${esc(t.nombre)}</b> <span class="tenue">· ${t.n} titulares${t.base ? ` (lo normal: ${num(t.base, 0)})` : ""}</span>
    ${t.nuevo === false ? '<span class="chip">tema de fondo: no vota</span>' : '<span class="chip verde">novedad: vota</span>'}
    <p class="tenue">${esc(t.explica)}</p><div class="tiras">${chips(t.efectos)}</div>
    ${t.titulares.slice(0, 3).map((n) => `<div class="evento"><span class="ev-ic">📰</span><span>${link(n)} <span class="tenue">${esc(n.fuente || "")}</span></span></div>`).join("")}</div>`).join("");
  const emp = (r.empresas || []).map((e) => `<div class="evento"><span class="ev-ic">${e.dir > 0 ? "🟢" : "🔴"}</span><span>${estrella(e.ticker, "Corresponsal")}<b class="link" data-abrir-debate="${esc(e.ticker)}">${esc(e.ticker)}</b>
    ${e.rumor ? '<span class="chip">rumor</span> ' : ""}${link(e.titulares[0])}</span></div>`).join("");
  const st = Object.entries(r.stats || {}).filter(([, x]) => x.casos);
  const tablaSt = st.length ? `<p class="tenue" style="margin-top:10px"><b>Cómo le fue</b> (a 5 ruedas, lo que el tema anticipaba): con 10 casos o más, si no acierta se silencia solo.</p>
    <div class="tabla-scroll"><table><tr><th>Tema</th><th class="n">Acierta</th><th class="n">Promedio</th><th class="n">Casos</th></tr>
    ${st.map(([k, x]) => `<tr><td>${esc(NOMBRE_TEMA[k] || k.replaceAll("_", " "))}</td><td class="n">${num(x.aciertos / x.casos * 100, 0)}%</td><td class="n">${pct(x.suma_ret / x.casos, 2)}</td><td class="n">${x.casos}</td></tr>`).join("")}</table></div>`
    : '<p class="tenue" style="margin-top:10px">Agente a prueba: arranca con medio voto. Su estadística propia sale a la semana de las primeras noticias.</p>';
  $("#mundo").innerHTML = `<div class="card eco"><div class="fila"><b>🌍 El Corresponsal</b><span class="tenue">${esc(r.hora || "")} · ${r.titulares || 0} titulares leídos</span></div>
    <p class="tenue">Lee portales y diarios del mundo y de Argentina cada 30 minutos. Si detecta un tema que mueve precios (guerra en el Golfo, la Fed, aranceles, China, Vaca Muerta, el FMI...) o una noticia de una empresa, se lo dice a la mesa y el Jefe lo escucha.</p>
    ${temas || '<p class="tenue">Ahora no hay temas del mundo que muevan precios.</p>'}
    ${emp ? `<p style="margin-top:10px"><b>Empresas</b></p>${emp}` : ""}${tablaSt}</div>`;
}

function pintarADR() {
  const r = ESTADO.estado?.adr;
  if (!r || (!r.filas?.length && !r.vivo?.length)) { $("#adr").innerHTML = ""; return; }
  const color = (v, u = 1) => (Math.abs(v) < u ? "tenue" : v > 0 ? "verde" : "rojo");
  const manana = r.filas?.length ? `<p class="tenue"><b>Anoche:</b> cómo cerraron los ADRs contra el cierre local y cuánto le falta hoy a cada acción para ponerse al día (vale en la mañana).</p>
    <div class="tabla-scroll"><table><tr><th>Acción</th><th class="n">ADR anoche</th><th class="n">Hoy</th><th class="n">Le falta</th></tr>
    ${r.filas.map((x) => `<tr><td><span class="link" data-abrir-debate="${esc(x.ticker)}">${esc(x.ticker)}</span> <span class="tenue">${esc(x.adr)}</span></td>
      <td class="n">${pct(x.brecha, 1)}</td><td class="n">${pct(x.hoy, 1)}</td><td class="n" style="color:var(--${color(x.resta, 1.5)})"><b>${pct(x.resta, 1)}</b></td></tr>`).join("")}</table></div>` : "";
  const vivo = r.vivo?.length ? `<p class="tenue" style="margin-top:10px"><b>En vivo:</b> lo que el ADR (con el CCL) se movió hoy de más o de menos que la acción local. Positivo = la local quedó atrás.</p>
    <div class="tiras">${r.vivo.map((x) => `<span class="chip ${color(x.brecha) === "verde" ? "verde" : color(x.brecha) === "rojo" ? "rojo" : ""}">${esc(x.ticker)} ${pct(x.brecha, 1)}</span>`).join("")}</div>` : "";
  const e = r.estadistica, p = e?.plazos || {}, fila = (k, t) => p[k]?.casos ? `<tr><td>${t}</td><td class="n">${num(p[k].aciertos / p[k].casos * 100, 0)}%</td><td class="n">${pct(p[k].suma_ret / p[k].casos, 2)}</td><td class="n">${num(p[k].casos, 0)}</td></tr>` : "";
  const est = e ? `<p class="tenue" style="margin-top:10px"><b>Estadística propia</b> (desde ${esc(fecha(e.desde))}, ${e.dias} días): cuando la brecha pasó 1%, cuánto se movió la acción local hacia el lado del ADR.</p>
    <div class="tabla-scroll"><table><tr><th>Después de</th><th class="n">Acierta</th><th class="n">Promedio</th><th class="n">Casos</th></tr>
    ${fila("30", "30 minutos")}${fila("60", "1 hora")}${fila("cierre", "al cierre")}</table></div>` : `<p class="tenue" style="margin-top:10px">Estadística propia: se arma sola con una foto por ronda; el primer resultado sale hoy al cierre.</p>`;
  $("#adr").innerHTML = `<div class="card eco"><div class="fila"><b>🌙 ADRs en Nueva York</b><span class="tenue">${esc(r.hora)}</span></div>${manana}${vivo}${est}</div>`;
}

// ---------- calendario de eventos ----------
const ICONO_EV = { cobro: "💵", balance: "📊", dividendo: "💰", macro: "🏛️", licitacion: "🏦" };
const DIAS_TXT = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
let SOLO_MIO = true;
function diaTxt(f) { const d = new Date(f + "T12:00:00"); const n = Math.round((d - new Date(HOY() + "T12:00:00")) / 864e5);
  return n === 0 ? "Hoy" : n === 1 ? "Mañana" : `${DIAS_TXT[d.getDay()]} ${fecha(f)}`; }
function filaEvento(e) {
  return `<div class="evento ${e.fuerte ? "fuerte" : ""}"><span class="ev-ic">${ICONO_EV[e.tipo] || "•"}</span>
    <span>${e.ticker && e.ticker !== "AL/GD" ? `<b class="link" data-abrir-debate="${esc(e.ticker)}">${esc(e.ticker)}</b> ` : ""}${e.link ? `<a href="#" data-doc="${esc(e.link)}" data-doc-n="${esc(e.nombre)}">${esc(e.nombre)}</a>` : esc(e.nombre)}${e.fuerte ? ' <span class="chip rojo">ese día no se abren posiciones</span>' : ""}</span></div>`;
}
function pintarEventos() {
  const evs = (ESTADO.estado?.eventos || []).filter((e) => !SOLO_MIO || e.mio || e.tipo === "cobro" || e.tipo === "macro");
  const porDia = {}; for (const e of evs) (porDia[e.fecha] ||= []).push(e);
  $("#eventos").innerHTML = `<label class="check"><input type="checkbox" id="solo-mio" ${SOLO_MIO ? "checked" : ""}> Solo lo mío y lo que mueve al mercado</label>` +
    (Object.keys(porDia).length ? Object.entries(porDia).map(([f, xs]) => `<div class="dia"><div class="dia-tit">${diaTxt(f)}</div>${xs.map(filaEvento).join("")}</div>`).join("")
      : '<p class="tenue">Sin eventos en los próximos 45 días.</p>') +
    '<p class="tenue">🏦 licitaciones (ONs, fideicomisos, Tesoro, provincias; fuente MAE) · 💵 cobros de bonos y ONs · 📊 balances · 💰 dividendos · 🏛️ inflación, Reserva Federal y otras fechas macro. Antes de un balance la mesa no propone entrar en ese papel.</p>';
  $("#solo-mio").onchange = (ev) => { SOLO_MIO = ev.target.checked; pintarEventos(); };
  // Hoy: lo de los próximos 7 días
  const lim = new Date(Date.now() + 7 * 864e5).toLocaleDateString("en-CA", { timeZone: "America/Argentina/Buenos_Aires" });
  const sem = (ESTADO.estado?.eventos || []).filter((e) => e.fecha <= lim && e.tipo !== "licitacion" && (e.mio || e.tipo === "macro" || e.tipo === "cobro"));
  pintarLicitaciones(lim);
  $("#eventos-semana").innerHTML = sem.length ? `<h2 class="ir" data-ir="lista|#cal-vista|eventos">Esta semana <span class="tenue">· ver calendario ›</span></h2><div class="card">${sem.slice(0, 8).map((e) =>
    `<div class="evento ${e.fuerte ? "fuerte" : ""}"><span class="ev-ic">${ICONO_EV[e.tipo] || "•"}</span><span><b>${diaTxt(e.fecha)}</b> · ${e.ticker && e.ticker !== "AL/GD" ? esc(e.ticker) + " · " : ""}${esc(e.nombre)}</span></div>`).join("")}</div>` : "";
}
const CHIP_LIC = { ON: "verde", Tesoro: "azul", Provincia: "azul", Fideicomiso: "", VCP: "", Otra: "" };
function pintarLicitaciones(lim) {
  const hoy = HOY();
  const ahora = new Date().toLocaleTimeString("en-GB", { timeZone: "America/Argentina/Buenos_Aires", hour: "2-digit", minute: "2-digit" });
  const xs = (ESTADO.estado?.eventos || []).filter((e) => e.tipo === "licitacion" && e.fecha >= hoy && e.fecha <= lim);
  const nots = ESTADO.estado?.licitaciones_noticias || [];
  const av = ESTADO.estado?.licitaciones_avisos || {};
  if (!xs.length && !nots.length && !(av.anuncios || []).length && !(av.resultados || []).length) { $("#licitaciones-hoy").innerHTML = ""; return; }
  const TIT = { moneda: "Moneda", integracion: "Se paga con", pago: "Paga en", tasa: "Tasa", margen: "Margen", vencimiento: "Vencimiento", amortizacion: "Amortización",
    intereses: "Pago de intereses", emision: "Emisión y liquidación", periodo: "Período de licitación", minimo: "Monto mínimo", precio: "Precio de emisión",
    calificacion: "Calificación", garantia: "Garantía", vn_emitido: "Monto emitido", ofertado: "Ofertas recibidas", margen_corte: "Margen de corte",
    tasa_corte: "Tasa de corte", factor_prorrateo: "Prorrateo", duration: "Duration" };
  const doc = (n, ic) => {
    const ca = n.campos || {};
    const filas = Object.entries(TIT).filter(([k]) => ca[k]).map(([k, t]) => `<tr><td><b>${t}</b></td><td>${esc(ca[k])}</td></tr>`).join("");
    const cab = `<span class="ev-ic">${ic}</span><span><b>${esc(fecha(n.fecha))}</b> · ${esc(n.titulo)}</span>`;
    const boton = n.link ? `<button class="chico" data-doc="${esc(n.link)}" data-doc-n="${esc(n.titulo)}">📄 Abrir documento</button>` : "";
    if (!n.resumen && !filas) return `<div class="evento">${cab}</div>${boton ? `<div class="lic-det">${boton}</div>` : ""}`;
    return `<details class="lic"><summary class="evento">${cab}<span class="tenue lic-mas">ver resumen ›</span></summary><div class="lic-det">
      ${n.resumen ? `<p style="margin:6px 0"><b>En resumen:</b> ${esc(n.resumen)}</p>` : ""}${filas ? `<div class="tabla-scroll"><table class="ficha">${filas}</table></div>` : ""}${boton}</div></details>`;
  };
  const deHoy = xs.filter((e) => e.fecha === hoy), prox = xs.filter((e) => e.fecha > hoy);
  const estado = (e) => !e.hora_cierre ? "" : ahora < e.hora_inicio ? `<span class="chip">abre ${esc(e.hora_inicio)}</span>`
    : ahora <= e.hora_cierre ? `<span class="chip verde">abierta hasta ${esc(e.hora_cierre)}</span>` : '<span class="chip rojo">cerró</span>';

  const detalle = (e) => {
    const ca = e.ficha?.campos || {};
    const filas = Object.entries(TIT).filter(([k]) => ca[k]).map(([k, t]) => `<tr><td><b>${t}</b></td><td>${esc(ca[k])}</td></tr>`).join("");
    const docs = (e.documentos || []).map((d) => `<div class="evento"><span class="ev-ic">📄</span><span><a href="#" data-doc="${esc(d.url)}" data-doc-n="${esc(d.titulo)}">${esc(d.titulo)}</a> <span class="tenue">${esc(fecha(d.fecha))}</span></span></div>`).join("");
    if (!e.resumen && !filas && !docs) return "";
    return `${e.resumen ? `<p style="margin:6px 0"><b>En resumen:</b> ${esc(e.resumen)}</p>` : ""}
      ${filas ? `<div class="tabla-scroll"><table class="ficha">${filas}</table></div>` : ""}
      ${docs ? `<p class="tenue" style="margin:8px 0 2px">Documentos (aviso, suplemento, prospecto):</p>${docs}` : ""}
      <p class="tenue">Resumen armado con el aviso de suscripción publicado en A3. Antes de ofertar, confirmá las condiciones en el suplemento.</p>`;
  };
  const fila = (e, conDia) => {
    const cab = `<span class="ev-ic">🏦</span><span>${conDia ? `<b>${diaTxt(e.fecha)}</b> · ` : ""}<span class="chip ${CHIP_LIC[e.clase] || ""}">${esc(e.clase)}</span> ${esc(e.nombre)}
      ${e.emisor ? `<span class="tenue"> · Emisor: ${esc(e.emisor)}</span>` : ""} ${e.fecha === hoy ? estado(e) : ""}</span>`;
    const det = detalle(e);
    return det ? `<details class="lic"><summary class="evento">${cab}<span class="tenue lic-mas">ver condiciones ›</span></summary><div class="lic-det">${det}</div></details>`
      : `<div class="evento">${cab}</div>`;
  };
  $("#licitaciones-hoy").innerHTML = `<h2>🏦 Licitaciones${deHoy.length ? " de hoy" : " de la semana"}</h2><div class="card">` +
    (deHoy.length ? deHoy.map((e) => fila(e, false)).join("") : '<p class="tenue">Hoy no hay licitaciones.</p>') +
    (prox.length ? `<p class="tenue" style="margin-top:.6em">Próximas:</p>${prox.slice(0, 6).map((e) => fila(e, true)).join("")}` : "") +
    ((av.anuncios || []).length ? `<p class="tenue" style="margin-top:.6em">Anunciadas en los últimos días (aviso de suscripción o colocación):</p>${av.anuncios.slice(0, 6).map((n) => doc(n, "📣")).join("")}` : "") +
    ((av.resultados || []).length ? `<p class="tenue" style="margin-top:.6em">Resultados (a qué tasa o precio cortó):</p>${av.resultados.slice(0, 6).map((n) => doc(n, "✅")).join("")}` : "") +
    (nots.length ? `<p class="tenue" style="margin-top:.6em">En las noticias (ONs que se licitan por otros sistemas y no figuran en el MAE):</p>${nots.slice(0, 5).map((n) =>
      `<div class="evento"><span class="ev-ic">📰</span><span>${n.link ? `<a href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.titulo)}</a>` : esc(n.titulo)}</span></div>`).join("")}` : "") +
    '<p class="tenue">Fuente: calendario público del MAE (A3 Mercados). Para participar se pide al colocador o al bróker antes del cierre.</p></div>';
}
document.querySelectorAll("#cal-vista button").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll("#cal-vista button").forEach((x) => x.classList.toggle("prim", x === b));
  $("#calendario").style.display = b.dataset.cal === "cobros" ? "" : "none";
  $("#eventos").style.display = b.dataset.cal === "eventos" ? "" : "none";
}));

// ---------- aprendizajes ----------
function pintarAprendizajes() {
  const xs = ESTADO.estado?.aprendizajes || [];
  $("#aprendizajes").innerHTML = xs.length ? xs.map((a) => `<div class="card"><div class="fila"><b>${esc(a.caso)}</b><span class="tenue">${esc(a.fecha)}</span></div>
    <p class="tenue">${esc(a.que_paso)}</p><p><b>Lección:</b> ${esc(a.leccion)}</p><p><b>Cambio:</b> ${esc(a.cambio)}</p></div>`).join("")
    : '<p class="tenue">Todavía no hay aprendizajes registrados.</p>';
}

// ---------- simulación en papel ----------
const ORIGEN = { corto: "Corto", mediano: "Mediano", jefe: "Jefe" };
const ESTADO_SIM = { abierta: "Abierta", pendiente: "Esperando precio", objetivo: "Llegó al objetivo", stop: "Tocó el stop", plazo: "Venció el plazo", no_se_dio: "No se dio" };
const plata = (x) => (x === null || x === undefined ? "—" : `${x < 0 ? "-" : ""}$${num(Math.abs(x), 0)}`);
let SIM_VISTA = "abiertas";
function tablaStats(obj, nombres = {}) {
  const filas = Object.entries(obj || {}).filter(([, v]) => v.cerradas);
  if (!filas.length) return '<p class="tenue">Todavía no hay operaciones cerradas.</p>';
  return `<div class="tabla-scroll"><table><tr><th></th><th class="n">Cerradas</th><th class="n">Ganadoras</th><th class="n">Prom.</th><th class="n">Resultado</th></tr>
    ${filas.sort((a, b) => b[1].ganancia - a[1].ganancia).map(([k, v]) => `<tr><td>${esc(nombres[k] || k)}</td><td class="n">${v.cerradas}</td><td class="n">${num(v.ganadoras_pct, 0)}%</td>
    <td class="n">${pct(v.promedio_pct, 1)}</td><td class="n" style="color:var(--${v.ganancia >= 0 ? "verde" : "rojo"})">${plata(v.ganancia)}</td></tr>`).join("")}</table></div>`;
}
async function pintarSimulacion() {
  const box = $("#simulacion");
  let d; try { d = await api("simulacion"); } catch (_) { box.innerHTML = '<p class="tenue">Sin datos de simulación.</p>'; return; }
  const r = d.resumen || {}, t = r.total || {};
  SIM_RES = r; pintarResumenHoy();
  const col = (x) => `color:var(--${(x || 0) >= 0 ? "verde" : "rojo"})`;
  const activa = (p) => ["abierta", "pendiente"].includes(p.estado);
  const ok = (p) => p.aprobada || p.origen === "jefe";
  const lista = d.posiciones.filter((p) => SIM_VISTA === "observacion" ? !ok(p)
    : ok(p) && (SIM_VISTA === "abiertas" ? activa(p) : !activa(p)));
  const obs = r.observacion || {};
  const item = (p) => {
    const abierta = p.estado === "abierta", g = abierta ? p.ganancia_actual : p.ganancia, gp = abierta ? p.ganancia_pct_actual : p.ganancia_pct;
    const ref = abierta ? `ahora ${num(p.ultimo)}` : p.salida ? `salió ${num(p.salida)}` : `límite ${num(p.entrada)}`;
    return `<div class="item"><div class="item-cab"><b class="link" data-abrir-debate="${esc(p.ticker)}">${esc(p.ticker)}</b>
        <span class="chip ${p.origen === "jefe" ? "" : p.semaforo === "verde" ? "verde" : p.semaforo === "rojo" ? "rojo" : "amar"}">${esc(ORIGEN[p.origen] || p.origen)}</span>
        <span class="item-precio">${g === undefined ? "" : `<b style="${col(g)}">${plata(g)}</b> <span class="tenue">${pct(gp, 1)}</span>`}</span></div>
      ${p.estado === "abierta" && p.ultimo ? `<div class="item-det">Precio ${pct((p.ultimo / p.entrada - 1) * 100, 1)} · con comisión ${pct(gp, 1)} (necesita +1,2% para empatar)</div>` : ""}
      <div class="item-det">${esc(ESTADO_SIM[p.estado] || p.estado)} · ${num(p.nominales, 0)} nom. · compra ${p.moneda === "USD" ? "US$" : ""}${num(p.entrada)} → ${ref} · objetivo ${num(p.objetivo)} / stop ${num(p.stop)}</div>
      <div class="item-det">${esc(p.setup)} · desde ${esc(p.fecha)}${p.fecha_cierre ? ` hasta ${esc(p.fecha_cierre)}` : ""}</div></div>`;
  };
  box.innerHTML = `<div class="grilla">
      <div class="met"><span>Resultado cerradas</span><b style="${col(t.ganancia)}">${t.cerradas ? plata(t.ganancia) : "—"}</b></div>
      <div class="met"><span>Ganadoras</span><b>${t.cerradas ? num(t.ganadoras_pct, 0) + "%" : "—"}</b></div>
      <div class="met"><span>Promedio por operación</span><b>${t.cerradas ? pct(t.promedio_pct, 1) : "—"}</b></div>
      <div class="met"><span>Abiertas (${r.abiertas || 0})</span><b style="${col(r.latente)}">${plata(r.latente || 0)}</b></div></div>
    <p class="tenue">Solo lo que la mesa te mostró: ${t.cerradas || 0} cerradas · ${r.pendientes || 0} esperando precio · ${r.no_se_dieron || 0} no se dieron.</p>
    <div class="tiras"><button class="chico ${SIM_VISTA === "abiertas" ? "prim" : ""}" data-simv="abiertas">Abiertas</button><button class="chico ${SIM_VISTA === "cerradas" ? "prim" : ""}" data-simv="cerradas">Cerradas</button><button class="chico ${SIM_VISTA === "observacion" ? "prim" : ""}" data-simv="observacion">En observación</button></div>
    ${SIM_VISTA === "observacion" ? `<p class="tenue">Las que la mesa NO te mostró (sin confirmación de otros analistas, o de antes del comité). Se siguen midiendo para saber si el filtro acierta${obs.cerradas ? `: ${obs.cerradas} cerradas, ${plata(obs.ganancia)} (${pct(obs.promedio_pct, 1)} prom.)` : ""}.</p>` : ""}
    ${lista.slice(0, 40).map(item).join("") || `<p class="tenue">${SIM_VISTA === "abiertas" ? "No hay operaciones simuladas abiertas: se abren solas cuando aparece una oportunidad." : "Todavía no cerró ninguna."}</p>`}
    <details><summary>Resultado por plazo, semáforo y agente</summary>
      <h2>Por plazo</h2>${tablaStats(r.por_origen, ORIGEN)}
      <h2>Por semáforo</h2>${tablaStats(r.por_semaforo, { verde: "Verde", amarillo: "Amarillo", rojo: "Rojo (no recomendadas)" })}
      <h2>Por tipo de oportunidad</h2>${tablaStats(r.por_setup)}
      <h2>Por agente</h2>${tablaStats(r.por_agente, Object.fromEntries(Object.keys(r.por_agente || {}).map((k) => [k, nombreAg(k)])))}
      <p class="tenue">Lo que cotiza en dólares (ej. AL30D) se pasa a pesos con el MEP del día de compra. Ojo: 1.000 nominales de una acción cara invierten mucho más que 1.000 de una barata. Para comparar, mirá el promedio en %.</p>
    </details>`;
  document.querySelectorAll("[data-simv]").forEach((b) => b.onclick = () => { SIM_VISTA = b.dataset.simv; pintarSimulacion(); });
}

// ---------- ranking ----------
async function pintarRanking() {
  const r = await api("ranking");
  const BANDA = { fuerte: "cuando dice fuerte", media: "media", debil: "débil" };
  $("#ranking").innerHTML = r.tabla.length ? r.tabla.map((f) => {
    const c = f.calibracion || {};
    const niv = f.nivel === "sin_datos" ? "" : `<span class="chip ${f.nivel === "titular" ? "verde" : f.nivel === "banco" ? "rojo" : f.nivel === "a_prueba" ? "amar" : ""}">${esc(f.nivel.replace("_", " "))}</span>`;
    const voto = (f.peso ?? 1) * (c.factor ?? 1);
    return `<div class="item"><div class="item-cab"><b>${esc(nombreAg(f.agente))}</b>${niv}
        <span class="item-precio"><span class="tenue">voto</span> <b style="color:var(--${voto >= 1 ? "verde" : voto >= 0.6 ? "amar" : "rojo"})">x${num(voto, 1)}</b></span></div>
      <div class="item-det">${c.casos ? `Acierta <b>${num(c.acierto_pct, 0)}%</b> a 10 ruedas · ${pct(c.esperanza_pct, 1)} promedio · ${num(c.casos, 0)} casos (${esc(c.fuente)})` : f.casos ? `Acierta ${num(f.aciertos_pct, 0)}% en ${f.casos} casos` : "Juntando casos todavía"}${f.sim_cerradas ? ` · simulación ${plata(f.sim_ganancia)}` : ""}</div>
      ${c.bandas && Object.keys(c.bandas).length ? `<div class="item-det">${Object.entries(c.bandas).map(([b, x]) => `${BANDA[b] || b}: ${num(x.acierto_pct, 0)}%${x.factor != null ? ` (voto x${num(x.factor, 1)})` : ""}`).join(" · ")}</div>` : ""}
      ${f.motivo ? `<div class="item-det">${esc(f.motivo)}</div>` : ""}</div>`;
  }).join("") : '<p class="tenue">El ranking arranca cuando los agentes juntan casos (se arma cada viernes).</p>';
  const ens = r.ensenanza || {}, fila = (k, t) => { const x = ens[k]; return x?.casos ? `<tr><td>${t}</td><td class="n">${num(x.aciertos / x.casos * 100, 0)}%</td><td class="n">${pct(x.suma_ret / x.casos, 1)}</td><td class="n">${num(x.casos, 0)}</td></tr>` : ""; };
  $("#ensenanza").innerHTML = Object.keys(ens).length ? `<h2>¿Sirve lo que enseña el Economista?</h2><div class="card">
    <p class="tenue">Señales de los otros agentes en la historia, según si iban a favor o en contra del contexto macro de ese día (a 10 ruedas):</p>
    <div class="tabla-scroll"><table><tr><th></th><th class="n">Acierta</th><th class="n">Promedio</th><th class="n">Casos</th></tr>
    ${fila("a_favor_del_contexto", "A favor del contexto")}${fila("contexto_neutro", "Contexto neutro")}${fila("contra_el_contexto", "En contra del contexto")}</table></div>
    <p class="tenue">Si "a favor" gana más que "en contra", su enseñanza sirve y se mantiene. Se vuelve a medir en cada entrenamiento.</p></div>` : "";
  const ew = r.ensenanza_ws || {}, filaW = (k, t) => { const x = ew[k]; return x?.casos ? `<tr><td>${t}</td><td class="n">${num(x.aciertos / x.casos * 100, 0)}%</td><td class="n">${pct(x.suma_ret / x.casos, 1)}</td><td class="n">${num(x.casos, 0)}</td></tr>` : ""; };
  $("#ensenanza-ws").innerHTML = Object.keys(ew).length ? `<h2>¿Sirve el clima de Wall Street?</h2><div class="card">
    <p class="tenue">Comprar cualquier CEDEAR según el clima de Wall Street de ese día, en 5 años (a 10 ruedas, en dólares):</p>
    <div class="tabla-scroll"><table><tr><th></th><th class="n">Sube</th><th class="n">Promedio</th><th class="n">Casos</th></tr>
    ${filaW("clima_comprador", "Clima comprador")}${filaW("clima_mixto", "Clima mixto")}${filaW("clima_defensivo", "Clima defensivo")}</table></div></div>` : "";
  const j = r.jefe || {};
  const NOMB_J = (k) => k.split("×").map((x) => nombreAg(x).replace("btc_alcista", "Bitcoin alcista").replace("miedo_eeuu", "miedo en Wall Street").replace("rp_subiendo", "riesgo país subiendo")).join(" + ");
  $("#jefe-modelo").innerHTML = j.prueba ? `<h2>El Jefe que aprende combinaciones</h2><div class="card">
    <div class="fila"><b>${j.activo ? "Activo" : "En pausa"}</b><span class="chip ${j.activo ? "verde" : "amar"}">${j.activo ? "elige él" : "sigue la suma de votos"}</span></div>
    <p class="tenue">${esc(j.motivo || "")}</p>
    <div class="tabla-scroll"><table><tr><th>Prueba con datos que no vio (a 20 ruedas)</th><th class="n">Promedio</th><th class="n">Gana más que comisión</th></tr>
      <tr><td>Las que elige el Jefe que aprende</td><td class="n">${pct(j.prueba.modelo.prom, 1)}</td><td class="n">${num(j.prueba.modelo.gana_pct, 0)}%</td></tr>
      <tr><td>Las que elige la suma de votos</td><td class="n">${pct(j.prueba.suma_votos.prom, 1)}</td><td class="n">${num(j.prueba.suma_votos.gana_pct, 0)}%</td></tr>
      <tr><td>Todas las ideas de los agentes</td><td class="n">${pct(j.prueba.todas.prom, 1)}</td><td class="n">${num(j.prueba.todas.gana_pct, 0)}%</td></tr></table></div>
    ${(j.aprendio || []).length ? `<p class="tenue"><b>Lo que más pesa en su decisión:</b> ${j.aprendio.slice(0, 5).map(([k, w]) => `${esc(NOMB_J(k))} (${w > 0 ? "suma" : "resta"})`).join(" · ")}</p>` : ""}
    <p class="tenue">Aprendió con ${num(j.casos, 0)} ideas de la historia; se vuelve a entrenar cada semana.</p></div>` : "";
  const ec = r.ensenanza_cripto || {};
  $("#ensenanza-cripto").innerHTML = (ec.btc || ec.brecha) ? `<h2>¿Aporta el agente Cripto?</h2><div class="card">
    ${[["btc", "Bitcoin como termómetro para CEDEARs"], ["brecha", "Dólar cripto como anticipo del CCL"]].map(([k, t]) => ec[k]?.veredicto ?
      `<p><b>${t}:</b> ${esc(ec[k].veredicto)} <span class="chip ${ec[k].sirve ? "verde" : "rojo"}">${ec[k].sirve ? "aporta" : "no aporta"}</span></p>` : "").join("")}</div>` : "";
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
// lectura técnica con el historial guardado (sin consultas a IOL)
function lecturaTecnica(t, hist) {
  const [ult, , compra, venta] = t;
  if (!hist.length) return null;
  const c = hist.map((v) => v.cierre).concat([ult]);
  const m20 = media(c, 20), m50 = media(c, 50), r = rsi(c);
  const u60 = hist.slice(-60), min60 = Math.min(...u60.map((v) => v.minimo)), max60 = Math.max(...u60.map((v) => v.maximo));
  const pos = (ult - min60) / (max60 - min60 || 1) * 100;
  const spread = compra && venta ? (venta / compra - 1) * 100 : null;
  let veredicto = "Precio neutral", color = "amar"; const porque = [];
  if ((r !== null && r < 35 && pos < 30) || (m20 && ult < m20 * 0.97 && pos < 35)) { veredicto = "Precio bajo: zona de compra"; color = "verde"; }
  else if ((r !== null && r > 70) || pos > 85) { veredicto = "Precio alto: mejor esperar"; color = "rojo"; }
  porque.push(`Está en el ${num(pos, 0)}% del rango de 60 ruedas (${num(min60)} a ${num(max60)}).`);
  if (m20) porque.push(`${ult > m20 ? "Arriba" : "Abajo"} de su media de 20 ruedas (${num(m20)}).`);
  if (m50) porque.push(`${ult > m50 ? "Arriba" : "Abajo"} de su media de 50 ruedas (${num(m50)}): tendencia ${ult > m50 ? "alcista" : "bajista"}.`);
  if (r !== null) porque.push(`RSI ${num(r, 0)} (${r < 30 ? "sobrevendido" : r > 70 ? "sobrecomprado" : "normal"}).`);
  if (spread !== null) porque.push(`Spread compra/venta ${num(spread)}%${spread > 1 ? ": poco líquido, usá orden límite" : ""}.`);
  return { veredicto, color, porque };
}

// ---------- hoja Debate ----------
const VEREDICTO = { comprar: ["verde", "Comprar"], esperar: ["amar", "Esperar"], evitar: ["rojo", "Evitar"], neutral: ["", "Neutral"] };
const nombreAg = (a) => NOMBRES[a] || { oportunidades_corto: "Oportunidades (corto)", oportunidades_mediano: "Oportunidades (mediano)" }[a] || a;
const fuerzaTxt = (f) => (f >= 0.7 ? "fuerte" : f >= 0.4 ? "media" : "débil");
function filasAgentes(xs) {
  return xs.map((s) => `<div class="agente"><b>${esc(nombreAg(s.agente))}<br><span class="tenue">${s.veto ? "VETO" : fuerzaTxt(s.fuerza || 0)}</span></b><span>${esc(s.texto)}</span></div>`).join("");
}
async function cargarDisponibles() {
  try {
    const r = await api("debate?t=");
    $("#debates-disp").innerHTML = r.disponibles.map((t) => `<option value="${esc(t)}">`).join("");
    $("#debate-chips").innerHTML = r.disponibles.slice(0, 16).map((t) => `<button type="button" class="chico" data-deb="${esc(t)}">${esc(t)}</button>`).join("");
    document.querySelectorAll("[data-deb]").forEach((b) => b.onclick = () => verDebate(b.dataset.deb));
  } catch (_) {}
}
async function verDebate(tk) {
  const box = $("#debate"); $("#form-debate").ticker.value = tk;
  box.innerHTML = '<p class="tenue">Armando el debate…</p>';
  try {
    const [p, hist, d] = await Promise.all([panel(), api(`historico?t=${encodeURIComponent(tk)}`), api(`debate?t=${encodeURIComponent(tk)}`)]);
    const t = p.titulos?.[tk], e = d.expediente;
    if (!t && !e) {
      box.innerHTML = `<div class="card"><b>${esc(tk)}</b><p class="tenue">${p.fecha ? `No está en los paneles de la última ronda (${esc(p.fecha)} ${esc(p.hora)}).` : "Todavía no hay ronda guardada."} Revisá el ticker (por ejemplo AL30D para la versión en dólares) o pedilo igual: si cotiza, la mesa lo debate en la próxima ronda.</p>
        <button id="btn-pedir-debate" class="prim" style="width:100%">${d.pedido ? "Ya está pedido" : "Pedir debate"}</button></div>`;
      $("#btn-pedir-debate").onclick = async () => { try { toast((await post("debate/pedir", { ticker: tk })).mensaje); } catch (x) { toast("No se pudo: " + x.message); } };
      return;
    }
    const ult = e?.precio?.ultimo ?? t?.[0], vari = e?.precio?.variacion ?? t?.[1];
    const tec = t ? lecturaTecnica(t, hist) : null;
    let html = `<div class="card"><div class="fila"><div><div style="font-size:20px;font-weight:700">${estrella(tk, "Debate")}${esc(tk)}</div>
      <span class="tenue">${e ? `Debate de la ronda ${esc(fecha(e.fecha))} ${esc(e.hora)}` : `Precio de la ronda ${esc(fecha(p.fecha))} ${esc(p.hora)}`}</span></div>
      <div style="text-align:right"><b style="font-size:18px">${num(ult)}</b><br><span class="chip ${vari > 0 ? "verde" : vari < 0 ? "rojo" : ""}">${pct(vari)}</span></div></div></div>`;
    if (e) {
      const [col, eti] = VEREDICTO[e.supervisor.veredicto] || VEREDICTO.neutral;
      html += `<div class="card sup ${col}"><div class="fila"><b>Opinión del supervisor</b><span class="chip ${col}">${eti}</span></div>
        <p style="font-size:16px;font-weight:600;margin:8px 0">${esc(e.supervisor.titulo)}</p>
        ${e.supervisor.detalle.map((x) => `<p class="tenue">• ${esc(x)}</p>`).join("")}
        ${e.jefe ? `<p><b>Jefe:</b> ${e.jefe.decision === "propuesta" ? "la propuso" : "la descartó"}${e.jefe.texto ? ` — ${esc(e.jefe.texto)}` : ""}</p>` : ""}</div>`;
      html += `<h2>Debate</h2><div class="debate"><b>Alcista:</b> ${esc(e.debate.alcista)}</div><div class="debate baj"><b>Bajista:</b> ${esc(e.debate.bajista)}</div>
        ${e.debate.fuente === "reglas" ? '<p class="tenue">Debate armado con los argumentos de los propios analistas (sin IA).</p>' : ""}`;
      html += `<h2>A favor (${e.favor.length})</h2>${e.favor.length ? `<div class="card">${filasAgentes(e.favor)}</div>` : '<p class="tenue">Ningún analista a favor.</p>'}`;
      html += `<h2>En contra (${e.contra.length})</h2>${e.contra.length ? `<div class="card">${filasAgentes(e.contra)}</div>` : '<p class="tenue">Ningún analista en contra.</p>'}`;
      if (e.neutral.length) html += `<details><summary>Neutrales (${e.neutral.length})</summary><div class="card">${filasAgentes(e.neutral)}</div></details>`;
      const det = (e.historiador?.detalle || []).slice().sort((a, b) => b.hasta.localeCompare(a.hasta));
      if (det.length) {
        const fx = (f) => `${f.slice(8, 10)}/${f.slice(5, 7)}/${f.slice(2, 4)}`;
        const celda = (v) => v === undefined ? "<td class=\"n\">—</td>" : `<td class="n" style="color:var(--${v >= 0 ? "verde" : "rojo"})">${pct(v, 1)}</td>`;
        html += `<h2>Gráficos parecidos (Historiador)</h2><div class="card"><p class="tenue">Momentos en que ${esc(tk)} dibujó una forma parecida a la de las últimas 20 ruedas, y qué hizo después. Sirve para recordar qué pasaba en el país o en la empresa en esas fechas.</p>
          <div class="tabla-scroll"><table><tr><th>Tramo</th><th class="n">Parecido</th><th class="n">5 ruedas</th><th class="n">10</th><th class="n">20</th></tr>
          ${det.map((d) => `<tr><td>${fx(d.desde)} → ${fx(d.hasta)}</td><td class="n">${num(d.correlacion * 100, 0)}%</td>${celda(d.despues["5"])}${celda(d.despues["10"])}${celda(d.despues["20"])}</tr>`).join("")}</table></div>
          ${det.length < 5 ? '<p class="tenue">Pocos casos: tomalo como contexto, no como regla.</p>' : ""}</div>`;
      }
      if (e.plan) {
        const r = e.riesgo || {};
        html += `<h2>Plan de Riesgo</h2><div class="card"><div class="grilla">
          <div class="met"><span>Entrada</span><b>${num(e.plan.entrada)}</b></div><div class="met"><span>Objetivo</span><b style="color:var(--verde)">${num(e.plan.objetivo)}</b></div>
          <div class="met"><span>Stop</span><b style="color:var(--rojo)">${num(e.plan.stop)}</b></div><div class="met"><span>Relación neta</span><b>${num(r.r_neto)}R</b></div></div>
          <p class="tenue">${r.ok ? "Pasa los filtros de Riesgo." : "No pasa Riesgo: " + esc((r.motivos || []).join(" "))} ${esc((r.avisos || []).join(" "))}</p></div>`;
      }
    } else {
      const sen = (ESTADO.estado?.senales || []).filter((s) => s.ticker === tk);
      html += `<div class="card"><b>Todavía no hay debate completo de ${esc(tk)}.</b>
        <p class="tenue">${d.pedido ? "Ya está pedido: sale en la próxima ronda (en horario de mercado, hasta 5 minutos)." : "Pedilo y en la próxima ronda los analistas lo discuten y el supervisor opina."}</p>
        ${sen.length ? `<p class="tenue">Mientras tanto, lo que ya dijeron:</p>${filasAgentes(sen)}` : ""}</div>`;
    }
    if (tec) html += `<h2>Precio de entrada (técnico)</h2><div class="card"><div class="fila"><b>${esc(tk)}</b><span class="chip ${tec.color}">${tec.veredicto}</span></div>
      ${tec.porque.map((x) => `<p class="tenue">• ${esc(x)}</p>`).join("")}</div>`;
    else if (t) html += '<p class="tenue">Sin historial guardado todavía para la lectura técnica: al pedir el debate, la mesa lo carga.</p>';
    html += `<button id="btn-pedir-debate" class="${e ? "" : "prim"}" style="width:100%;margin-top:10px">${e ? "Actualizar debate" : "Pedir debate completo"}</button>
      <p class="tenue">Es el análisis de la mesa, no una recomendación. La orden la decidís y cargás vos.</p>`;
    box.innerHTML = html;
    $("#btn-pedir-debate").onclick = async () => {
      try { const r = await post("debate/pedir", { ticker: tk }); toast(r.mensaje); } catch (x) { toast("No se pudo: " + x.message); }
    };
  } catch (x) { box.innerHTML = `<p class="tenue">No se pudo: ${esc(x.message)}</p>`; }
}
function abrirDebate(tk) { document.querySelector('.tabs button[data-v="asistente"]').click(); verDebate(tk); }
document.addEventListener("click", (ev) => { const b = ev.target.closest("[data-abrir-debate]"); if (b) abrirDebate(b.dataset.abrirDebate); });
// accesos directos: tocar un número o un chip lleva a su detalle (vista|#lugar|extra)
function irYResaltar(vista, sel) {
  irA(vista);
  setTimeout(() => { const el = sel && $(sel); if (!el) return; el.scrollIntoView({ behavior: "smooth", block: "start" });
    el.classList.remove("resaltar"); void el.offsetWidth; el.classList.add("resaltar"); }, 120);
}
document.addEventListener("click", (ev) => {
  const b = ev.target.closest("[data-ir]"); if (!b) return;
  const [vista, sel, extra] = b.dataset.ir.split("|");
  if (extra === "ops") {  // si no hay de corto pero sí de mediano, mostrar las de mediano
    const o = ESTADO.estado?.oportunidades || {};
    if (!(o[PLAZO] || []).length) { const otro = PLAZO === "corto" ? "mediano" : "corto"; if ((o[otro] || []).length) document.querySelector(`#ops-plazo [data-plazo="${otro}"]`)?.click(); }
  }
  if (extra === "eventos") document.querySelector('#cal-vista [data-cal="eventos"]')?.click();
  irYResaltar(vista, sel);
});
document.addEventListener("click", (ev) => { if (ev.target.closest("[data-ir-pron]")) { irA("ranking"); setTimeout(() => $("#titulo-pronosticos")?.scrollIntoView({ behavior: "smooth" }), 100); } });
$("#form-debate").addEventListener("submit", (ev) => { ev.preventDefault(); verDebate(ev.target.ticker.value.trim().toUpperCase()); });
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
    pintarEstado(); pintarPropuestas(); pintarUsuario(); pintarAprendizajes(); pintarAnticipos(); pintarRadar(); pintarAviso();
    $("#login").style.display = "none"; $("#bloqueo").style.display = "none"; document.querySelector("main").style.display = "";
  } catch (e) {
    if (String(e.message).includes("bloqueada")) { mostrarBloqueo(); return; }
    if (String(e.message).includes("sin acceso")) {
      $("#login").style.display = "block"; document.querySelector("main").style.display = "none";
      $("#sub").textContent = "Ingresá tu clave";
    } else $("#sub").textContent = `No se pudo cargar: ${e.message}`;
  }
}
$("#form-login").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  try { await post("login", { clave: ev.target.clave.value }); ev.target.reset(); BLOQUEADA = false; await cargar().then(cargarDisponibles); pintarRanking().catch(() => {}); pintarSimulacion(); }
  catch (e) { toast(e.message); }
});
// ---------- huella / cara (passkey) ----------
const b64u = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const desB64u = (s) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((s.length + 3) % 4)), (c) => c.charCodeAt(0));
let BLOQUEADA = false;
let AUTO_INTENTO = false;
function mostrarBloqueo() {
  if (!BLOQUEADA && !AUTO_INTENTO) { AUTO_INTENTO = true; setTimeout(() => desbloquear(true), 300); }  // Android lo pide solo; iPhone necesita tocar el botón
  BLOQUEADA = true;
  $("#bloqueo").style.display = "block"; $("#login").style.display = "none"; document.querySelector("main").style.display = "none";
  $("#sub").textContent = "Bloqueada";
}
async function desbloquear(auto = false) {
  try {
    const r = await post("passkey/reto", {});
    const cred = await navigator.credentials.get({ publicKey: { challenge: desB64u(r.reto), rpId: r.rpId, userVerification: "required", timeout: 60000,
      allowCredentials: r.ids.map((id) => ({ type: "public-key", id: desB64u(id) })) } });
    await post("passkey/verificar", { id: cred.id, authenticatorData: b64u(cred.response.authenticatorData),
      clientDataJSON: b64u(cred.response.clientDataJSON), signature: b64u(cred.response.signature) });
    BLOQUEADA = false; await cargar(); cargarDisponibles(); pintarRanking().catch(() => {}); pintarSimulacion();
    AUTO_INTENTO = false;
  } catch (e) { if (!auto) toast(e.name === "NotAllowedError" ? "Cancelado: probá de nuevo o usá la clave" : "No se pudo: " + e.message); }
}
$("#btn-desbloquear").onclick = () => desbloquear(false);
$("#btn-usar-clave").onclick = () => { $("#bloqueo").style.display = "none"; $("#login").style.display = "block"; };
async function pintarPasskey() {
  try {
    const e = await api("passkey/estado");
    $("#passkey-estado").textContent = e.activa ? `Activada (${e.cantidad} ${e.cantidad === 1 ? "dispositivo" : "dispositivos"}).` : "Desactivada: la app queda abierta en este celular.";
    $("#btn-passkey").textContent = e.activa ? "Sumar este celular" : "Activar en este celular";
    $("#btn-passkey-borrar").style.display = e.activa ? "" : "none";
  } catch (_) {}
}
$("#btn-passkey").onclick = async () => {
  if (!window.PublicKeyCredential) return toast("Este navegador no permite huella o cara");
  try {
    const r = await post("passkey/reto", {});
    const cred = await navigator.credentials.create({ publicKey: { challenge: desB64u(r.reto), rp: { name: "Mesa de dinero", id: r.rpId },
      user: { id: crypto.getRandomValues(new Uint8Array(16)), name: "mesa", displayName: "Mesa de dinero" },
      pubKeyCredParams: [{ type: "public-key", alg: -7 }, { type: "public-key", alg: -257 }],
      authenticatorSelection: { authenticatorAttachment: "platform", userVerification: "required", residentKey: "preferred" }, timeout: 60000,
      excludeCredentials: r.ids.map((id) => ({ type: "public-key", id: desB64u(id) })) } });
    const spki = cred.response.getPublicKey?.();
    if (!spki) return toast("Este celular no permite registrar la huella desde el navegador");
    await post("passkey/registrar", { id: cred.id, spki: b64u(spki), alg: cred.response.getPublicKeyAlgorithm(),
      clientDataJSON: b64u(cred.response.clientDataJSON), nombre: navigator.userAgent.match(/\(([^;)]+)/)?.[1] || "celular" });
    toast("Listo: desde ahora la app pide tu huella o tu cara"); pintarPasskey();
  } catch (e) { toast(e.name === "InvalidStateError" ? "Este celular ya estaba registrado" : e.name === "NotAllowedError" ? "Cancelado" : "No se pudo: " + e.message); }
};
$("#btn-passkey-borrar").onclick = async () => {
  try { await post("passkey/borrar", {}); toast("Desactivada: ya no pide huella"); pintarPasskey(); } catch (e) { toast("No se pudo: " + e.message); }
};
pintarPasskey();

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js");
cargar().then(cargarDisponibles); pintarRanking().catch(() => {}); pintarSimulacion();
setInterval(() => { if (!document.hidden && !BLOQUEADA) { cargar(); pintarSimulacion(); } }, 60000);
document.addEventListener("visibilitychange", () => { if (!document.hidden && !BLOQUEADA) cargar(); });
