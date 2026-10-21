// Asistente de la mesa: preguntas libres ("bonos en pesos que paguen mensual", "¿está bien el precio de X?").
// Usa Claude con herramientas que leen los datos de la mesa (precios de la última ronda, historial, informes,
// tu cartera) y búsqueda web para condiciones de emisión (frecuencia de pago, vencimientos, amortización).

const MODELO = "claude-sonnet-5-5";
const MAX_PREGUNTAS_DIA = 40;

const SISTEMA = `Sos el asistente de una mesa de dinero personal del mercado argentino. Respondés en español rioplatense, claro y concreto, para alguien que decide desde el celular.

Reglas:
- Nunca inventes tickers, precios, tasas ni fechas de pago. Los precios salen SOLO de las herramientas de la mesa (última ronda). Las condiciones de emisión (frecuencia de cupón, amortización, vencimiento, moneda, tasa) búscalas con web_search en fuentes confiables (prospectos/suplementos en CNV, BYMA, el emisor, Ministerio de Economía, brokers serios) y citá la fuente.
- Si un dato no está verificado, decilo ("no pude confirmar la frecuencia de pago de X").
- Para "¿el precio de entrada está bien?": compará el precio actual contra su historial (media de 20 y 50 ruedas, mínimos y máximos recientes, soportes) con la herramienta historial, y para bonos/ONs/letras contra la TIR o el rendimiento de instrumentos parecidos. Explicá en 1-2 líneas.
- Cuando sugieras instrumentos, mostrá una tabla breve: ticker, moneda, precio (última ronda y hora), frecuencia de pago, próximo pago si lo sabés, vencimiento, rendimiento aproximado si se puede calcular, y una línea de "precio de entrada".
- Si el pedido es por necesidad de flujo de fondos (cobrar todos los meses, cada trimestre), proponé una combinación escalonada para cubrir los meses y aclarales los meses que quedan sin cobro.
- Tené en cuenta liquidez (spread compra/venta) y riesgo de crédito; marcá lo poco líquido.
- Terminá con una línea: "No es asesoramiento financiero; verificá condiciones antes de operar." No envíes órdenes ni digas que operaste.`;

const HERRAMIENTAS = [
  { name: "buscar_titulos", description: "Lista títulos de la última ronda de la mesa, filtrando por grupo (acciones, cedears, soberanos, ons, letras, cauciones) y/o texto en el ticker. Devuelve ticker, último, variación del día, compra, venta.",
    input_schema: { type: "object", properties: { grupo: { type: "string" }, texto: { type: "string" }, max: { type: "integer" } } } },
  { name: "cotizacion", description: "Precio de la última ronda para una lista de tickers.",
    input_schema: { type: "object", properties: { tickers: { type: "array", items: { type: "string" } } }, required: ["tickers"] } },
  { name: "historial", description: "Velas diarias guardadas de un ticker (fecha, cierre, máximo, mínimo, volumen). Solo existen para los tickers que la mesa sigue.",
    input_schema: { type: "object", properties: { ticker: { type: "string" }, ruedas: { type: "integer" } }, required: ["ticker"] } },
  { name: "mi_cartera", description: "La cartera, Mi lista y los flujos de ONs cargados por el usuario.", input_schema: { type: "object", properties: {} } },
  { name: "estado_mesa", description: "Indicadores (MEP, CCL, riesgo país, caución), informes por mercado, oportunidades y propuestas vigentes de la mesa.",
    input_schema: { type: "object", properties: {} } },
  { type: "web_search_20250305", name: "web_search", max_uses: 4 },
];

async function ejecutar(env, nombre, input) {
  const leer = async (k, d = null) => (await env.MESA.get(k, "json")) ?? d;
  if (nombre === "buscar_titulos" || nombre === "cotizacion") {
    const panel = await leer("ui/panel", { titulos: {} });
    const fila = ([tk, [u, v, c, ve, g]]) => ({ ticker: tk, ultimo: u, variacion: v, compra: c, venta: ve, grupo: g });
    let filas = Object.entries(panel.titulos || {});
    if (nombre === "cotizacion") {
      const pedidos = new Set((input.tickers || []).map((t) => String(t).toUpperCase()));
      filas = filas.filter(([tk]) => pedidos.has(tk));
    } else {
      if (input.grupo) filas = filas.filter(([, x]) => x[4] === input.grupo);
      if (input.texto) filas = filas.filter(([tk]) => tk.includes(String(input.texto).toUpperCase()));
      filas = filas.slice(0, Math.min(input.max || 80, 200));
    }
    return { ronda: `${panel.fecha} ${panel.hora}`, titulos: filas.map(fila) };
  }
  if (nombre === "historial") {
    const t = String(input.ticker || "").toUpperCase().replace(/[^A-Z0-9.]/g, "");
    const v = (await leer(`cache/lote/${t.slice(0, 1) || "_"}`, {}))[t] || (await leer(`cache/diario/${t}`, []));
    const n = Math.min(input.ruedas || 120, 400);
    return v.length ? v.slice(-n).map((x) => [x.fecha, x.cierre, x.maximo, x.minimo, x.volumen]) : { error: "sin historial guardado" };
  }
  if (nombre === "mi_cartera") {
    const [cartera, lista, ons] = await Promise.all([leer("usuario/cartera", []), leer("usuario/lista", []), leer("usuario/ons", {})]);
    return { cartera, lista, ons };
  }
  if (nombre === "estado_mesa") {
    const e = await leer("ui/estado", {});
    return { fecha: e.fecha, hora: e.hora, clima: e.clima, indicadores: e.indicadores, riesgo_pais: e.riesgo_pais,
      dolares: e.dolares, informes: e.informes, oportunidades: e.oportunidades };
  }
  return { error: "herramienta desconocida" };
}

export async function asistente(req, env) {
  if (!env.ANTHROPIC_API_KEY) return { status: 501, cuerpo: { error: "Falta cargar ANTHROPIC_API_KEY para usar el asistente." } };
  const hoy = new Date().toLocaleDateString("en-CA", { timeZone: "America/Argentina/Buenos_Aires" });
  const claveUso = `asistente/uso/${hoy}`;
  const usadas = Number((await env.MESA.get(claveUso)) || 0);
  if (usadas >= MAX_PREGUNTAS_DIA) return { status: 429, cuerpo: { error: `Llegaste al tope de ${MAX_PREGUNTAS_DIA} preguntas por día.` } };

  const { pregunta, historial = [] } = await req.json();
  if (!pregunta || String(pregunta).length > 2000) return { status: 400, cuerpo: { error: "Pregunta vacía o muy larga." } };
  const mensajes = [...historial.slice(-8).map((m) => ({ role: m.rol === "yo" ? "user" : "assistant", content: String(m.texto).slice(0, 4000) })),
    { role: "user", content: `Hoy es ${hoy}. ${pregunta}` }];

  const fuentes = [];
  for (let paso = 0; paso < 8; paso++) {
    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "x-api-key": env.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json" },
      body: JSON.stringify({ model: env.MODELO_ASISTENTE || MODELO, max_tokens: 2500, system: SISTEMA, tools: HERRAMIENTAS, messages: mensajes }),
    });
    if (!r.ok) return { status: 502, cuerpo: { error: `La IA respondió ${r.status}: ${(await r.text()).slice(0, 200)}` } };
    const d = await r.json();
    mensajes.push({ role: "assistant", content: d.content });
    for (const b of d.content) {
      if (b.type === "web_search_tool_result" && Array.isArray(b.content))
        for (const x of b.content) if (x.url && fuentes.length < 8 && !fuentes.some((f) => f.url === x.url)) fuentes.push({ titulo: x.title, url: x.url });
    }
    if (d.stop_reason === "pause_turn") continue; // búsqueda web larga: se retoma tal cual
    const usos = d.content.filter((b) => b.type === "tool_use");
    if (d.stop_reason !== "tool_use" || !usos.length) {
      await env.MESA.put(claveUso, String(usadas + 1), { expirationTtl: 172800 });
      const texto = d.content.filter((b) => b.type === "text").map((b) => b.text).join("\n").trim();
      return { status: 200, cuerpo: { respuesta: texto, fuentes, restantes: MAX_PREGUNTAS_DIA - usadas - 1 } };
    }
    const resultados = [];
    for (const u of usos) {
      let res;
      try { res = await ejecutar(env, u.name, u.input || {}); } catch (e) { res = { error: e.message }; }
      resultados.push({ type: "tool_result", tool_use_id: u.id, content: JSON.stringify(res).slice(0, 30000) });
    }
    mensajes.push({ role: "user", content: resultados });
  }
  return { status: 504, cuerpo: { error: "La consulta tomó demasiados pasos. Probá con una pregunta más concreta." } };
}
