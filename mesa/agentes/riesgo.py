"""12. Riesgo: arma el plan (entrada, stop, objetivo) y decide si pasa, con qué tamaño, o lo veta.

Reglas (config/mesa.yaml → riesgo):
- Relación ganancia/pérdida neta de comisiones ≥ r_minimo_neto.
- Spread y monto operado mínimos (liquidez).
- Tope de pérdida diaria/semanal en R: si se alcanzó, no hay propuestas nuevas.
- Máximo por sector, contando posiciones abiertas y propuestas del día.
- Clima malo → tamaño reducido; riesgo país sobre el tope → no bancos ni soberanos.
- Calendario: el día de un evento marcado como 'fuerte', no se abren posiciones nuevas.
- Un hecho grave del emisor (veto) frena cualquier compra.
"""
from __future__ import annotations

from datetime import timedelta

from ..nucleo import calc
from ..nucleo.config import config, sector
from ..nucleo.contexto import Contexto
from ..nucleo.modelos import Plan


# Plazo de cada idea según el agente que la origina (en ruedas): cada estrategia gana en su plazo.
# Wall Street (tendencia + momentum) gana a ~3 meses; Cripto y lo técnico, en días.
PLAZO_AGENTE = {"wallstreet": 60, "oportunidades_mediano": 60, "economista": 20, "panico": 20,
                "cripto": 10, "adr": 3, "volumen_flujo": 5, "anticipo": 3, "anticipador": 5, "mundo": 5, "ministro": 20, "ganadores": 20, "profesionales": 40}


def plazo_de(agente: str | None) -> int:
    return PLAZO_AGENTE.get(agente or "", int(config()["riesgo"]["salida_por_tiempo_dias"]))


def armar_plan(ctx: Contexto, ticker: str, ruedas: int | None = None) -> Plan | None:
    """Entrada, stop y objetivo. Con más plazo, stop más holgado y objetivo más lejos (la idea necesita aire)."""
    t = ctx.titulo(ticker)
    velas = ctx.cache.velas(ticker) if ctx.cache else []
    if not t or not t.get("ultimo") or len(velas) < 20:
        return None
    precio = t.get("venta") or t["ultimo"]
    a = calc.atr(velas) or precio * 0.02
    sop = calc.soporte_cercano(velas, precio)
    res = calc.resistencia_cercana(velas, precio)
    # entrada: si hay soporte a menos de 1 ATR, esperar ahí; si no, precio actual
    entrada = sop["hasta"] if sop and precio - sop["hasta"] <= a else precio
    # no perseguir: si hoy ya subió fuerte, la entrada va con límite medio ATR abajo
    # (lección del 20/10: TXAR se vio a 690,5 y el Jefe lo propuso a 715 tras subir 3%)
    if (t.get("variacion") or 0) >= float(config()["riesgo"].get("no_perseguir_suba_pct", 2.5)):
        entrada = min(entrada, precio - 0.5 * a)
    entrada = round(min(entrada, precio), 4)
    ruedas = int(ruedas or config()["riesgo"]["salida_por_tiempo_dias"])
    escala = max(1.0, (ruedas / 10) ** 0.5)  # 60 ruedas ≈ 2,4 veces más aire que 10
    base_stop = sop["desde"] if sop and entrada - sop["desde"] <= 2 * a * escala else entrada - 1.5 * a * escala
    stop = round(min(base_stop - 0.25 * a, entrada - 1.5 * a * escala) if escala > 1 else base_stop - 0.25 * a, 4)
    riesgo = entrada - stop
    minimo_obj = 2.5 if ruedas <= 10 else 3.0
    objetivo = res["nivel"] if res and res["nivel"] - entrada >= minimo_obj * riesgo else entrada + minimo_obj * riesgo
    vence = (ctx.fecha + timedelta(days=ruedas * 7 // 5)).isoformat()
    return Plan(ticker, "compra", entrada, stop, round(objetivo, 4), 1.0, vence)


def evaluar(ctx: Contexto, plan: Plan, estado: dict, vetos: set[str]) -> dict:
    """Devuelve {'ok': bool, 'tamano_r': float, 'motivos': [...], 'avisos': [...]}"""
    c = config()["riesgo"]
    com = config()["capital"]["comision_ida_vuelta_pct"]
    t = ctx.titulo(plan.ticker) or {}
    motivos, avisos = [], []
    tam = 1.0

    if plan.ticker in vetos:
        motivos.append("Hecho grave del emisor: compras congeladas.")
    if estado.get("perdida_dia_r", 0) <= -c["perdida_max_dia_r"]:
        motivos.append(f"Se alcanzó la pérdida máxima del día ({c['perdida_max_dia_r']}R).")
    if estado.get("perdida_semana_r", 0) <= -c["perdida_max_semana_r"]:
        motivos.append(f"Se alcanzó la pérdida máxima de la semana ({c['perdida_max_semana_r']}R).")
    # costo real de entrar y salir: comisión + la diferencia entre compra y venta (se compra a la punta vendedora
    # y se vende a la compradora). En papeles que operan poco, la diferencia puede comerse toda la ganancia.
    from ..nucleo.calc import spread_pct
    spread = spread_pct(t)
    costo = com + (spread or 0)
    rn = plan.r_neto(costo)
    if rn < c["r_minimo_neto"]:
        motivos.append(f"Relación neta {rn:.2f}R, menor al mínimo {c['r_minimo_neto']}R"
                       + (f" (entrar y salir cuesta {costo:.1f}%: comisión {com:.1f}% + diferencia compra/venta {spread:.1f}%)." if spread else "."))
    if spread is not None and spread > c["spread_max_pct"]:
        motivos.append(f"Spread {spread:.2f}% demasiado abierto.")
    elif spread:
        avisos.append(f"Entrar y salir cuesta {costo:.1f}% (comisión {com:.1f}% + diferencia compra/venta {spread:.1f}%).")
    monto = t.get("monto")
    if monto is not None and monto < c["monto_min_operado_ars"] and t.get("moneda") in (None, "peso_Argentino", "ARS"):
        avisos.append(f"Poco volumen operado hoy (${monto:,.0f}".replace(",", ".") + "): usar orden límite y montos chicos.")
    sec = sector(plan.ticker)
    en_sector = sum(1 for p in estado.get("abiertas", []) + estado.get("propuestas_hoy", []) if sector(p["ticker"]) == sec)
    if en_sector >= c["max_por_sector"]:
        motivos.append(f"Ya hay {en_sector} operaciones en el sector {sec}.")
    rp = ctx.riesgo_pais.get("valor")
    if rp and rp > c["riesgo_pais_tope_bancos"] and sec in ("bancos", "soberanos"):
        motivos.append(f"Riesgo país {rp:.0f} > {c['riesgo_pais_tope_bancos']}: no se compran {sec}.")
    base = plan.ticker[:-1] if plan.ticker.endswith(("D", "C")) and ctx.titulo(plan.ticker[:-1]) else plan.ticker
    limite = (ctx.fecha + timedelta(days=c.get("dias_antes_balance", 3))).isoformat()
    bal = next((e for e in ctx.eventos if e.get("tipo") == "balance" and e.get("ticker") == base
                and ctx.fecha.isoformat() <= e.get("fecha", "") <= limite), None)
    if bal:
        motivos.append(f"Presenta balance el {bal['fecha'][8:10]}/{bal['fecha'][5:7]}: no se entra justo antes (puede saltar para cualquier lado).")
    if any(e.get("fuerte") and e.get("fecha") == ctx.fecha.isoformat() for e in ctx.eventos):
        motivos.append("Hoy hay un evento fuerte en el calendario: no se abren posiciones nuevas.")
    if ctx.clima <= -0.3:
        tam = c["clima_malo_tamano_r"]
        avisos.append(f"Clima de mercado malo: tamaño reducido a {tam}R.")
    return {"ok": not motivos, "tamano_r": tam, "r_neto": round(rn, 2), "motivos": motivos, "avisos": avisos,
            "costo_pct": round(costo, 2), "spread_pct": spread}
