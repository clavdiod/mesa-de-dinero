"""Oportunidades de hoy: ranking de entradas posibles a corto (1-10 ruedas) y mediano plazo (1-3 meses).

A diferencia del Jefe (estricto, máx. 3 por día), acá se muestra todo lo que está cerca, con semáforo de Riesgo:
verde = pasa todo; amarillo = pasa con advertencias; rojo = Riesgo lo frena hoy (se muestra el motivo).
Cada oportunidad queda como señal medible, así el ranking dice con el tiempo si estos setups ganan plata.
"""
from __future__ import annotations

import statistics as st
from datetime import timedelta

from ..nucleo import calc
from ..nucleo.config import config, sector
from ..nucleo.contexto import Contexto
from ..nucleo.modelos import Plan, Senal
from . import riesgo


def _plan(ctx: Contexto, tk: str, precio: float, stop: float, objetivo: float, ruedas: int) -> Plan:
    vence = (ctx.fecha + timedelta(days=ruedas * 7 // 5)).isoformat()
    return Plan(tk, "compra", round(precio, 4), round(stop, 4), round(objetivo, 4), 1.0, vence)


def _semaforo(ev: dict) -> str:
    if not ev["ok"]:
        return "rojo"
    return "amarillo" if ev["avisos"] else "verde"


def detectar(ctx: Contexto, estado: dict, vetos: set[str]) -> dict:
    com = config()["capital"]["comision_ida_vuelta_pct"]
    corto, mediano = [], []
    tickers = [tk for tk in (ctx.cache.indice if ctx.cache else {}) if ctx.titulo(tk)]
    for tk in tickers:
        t = ctx.titulo(tk)
        velas = ctx.cache.velas(tk)
        if not t.get("ultimo") or len(velas) < 60:
            continue
        precio = t.get("venta") or t["ultimo"]
        cierres = [v["cierre"] for v in velas] + [t["ultimo"]]
        a = calc.atr(velas) or precio * 0.02
        r = calc.rsi(cierres)
        m20, m50, m200 = calc.sma(cierres, 20), calc.sma(cierres, 50), calc.sma(cierres, 200)
        sop = calc.soporte_cercano(velas, precio)
        res = calc.resistencia_cercana(velas, precio)
        vols = [v["volumen"] for v in velas[-20:] if v.get("volumen")]
        vol_rel = (t.get("volumen") or 0) / st.mean(vols) if len(vols) >= 10 and st.mean(vols) else None
        pat10 = calc.patrones_parecidos(cierres, 20, 0.85, (10, 20))
        h10, h20 = pat10["horizontes"].get(10), pat10["horizontes"].get(20)
        casos = pat10["casos"]
        hist_txt = (f"En {casos} gráficos parecidos subió {h10['subas']} veces a 10 ruedas ({h10['promedio_pct']:+.1f}% prom.)"
                    if h10 else "Sin gráficos parecidos suficientes")

        # ---------- CORTO (1-10 ruedas) ----------
        setups = []
        if r is not None and r <= 35 and sop and sop["toques"] >= 2 and precio <= sop["nivel"] * 1.03:
            stop = sop["desde"] - 0.3 * a
            obj = res["nivel"] if res else precio + 2.5 * (precio - stop)
            setups.append(("Rebote en soporte", f"Sobrevendido (RSI {r:.0f}) a {(precio / sop['nivel'] - 1) * 100:.1f}% de un soporte que aguantó {sop['toques']} veces.", stop, obj))
        max20 = max(v["maximo"] for v in velas[-20:])
        if t["ultimo"] > max20 and (vol_rel or 0) >= 1.3:
            stop = max20 - 1.0 * a
            obj = precio + 2.5 * (precio - stop)
            setups.append(("Quiebre con volumen", f"Supera el máximo de 20 ruedas ({max20:,.2f}) con volumen {vol_rel:.1f}x.", stop, obj))
        for nombre, motivo, stop, obj in setups:
            if stop >= precio:
                continue
            plan = _plan(ctx, tk, precio, stop, obj, 10)
            ev = riesgo.evaluar(ctx, plan, estado, vetos)
            prob = (h10["subas"] / casos) if h10 and casos >= 8 else 0.5
            corto.append({"ticker": tk, "sector": sector(tk), "plazo": "corto", "setup": nombre, "motivo": motivo,
                          "historia": hist_txt, "plan": plan.dict(), "r_neto": round(plan.r_neto(com), 2),
                          "semaforo": _semaforo(ev), "riesgo": ev, "puntaje": round(plan.r_neto(com) * prob, 3)})

        # ---------- MEDIANO (1-3 meses) ----------
        m50_antes = calc.sma(cierres[:-20], 50) if len(cierres) >= 70 else None
        # tendencia de verdad: la media de 50 tiene que venir subiendo (≥1% en 20 ruedas), no un lateral
        # (lección del 20/10: METR estaba encima de sus medias pero lateral entre 2.255 y 2.442 hacía dos meses)
        sube = bool(m50_antes and m50 and m50 >= m50_antes * 1.01)
        if m50 and m200 and sube and precio > m50 > m200 and precio <= m50 * 1.04:
            stop = min(m50 - 1.0 * a, (sop["desde"] if sop else m50 - 1.5 * a))
            obj = precio + 3 * (precio - stop)
            if stop < precio:
                plan = _plan(ctx, tk, precio, stop, obj, 60)
                ev = riesgo.evaluar(ctx, plan, estado, vetos)
                mediano.append({"ticker": tk, "sector": sector(tk), "plazo": "mediano", "setup": "Tendencia alcista, retroceso a la media",
                                "motivo": f"Por encima de sus medias de 50 y 200 ruedas y cerca de la de 50 ({m50:,.2f}): buen punto de entrada en tendencia.",
                                "historia": hist_txt, "plan": plan.dict(), "r_neto": round(plan.r_neto(com), 2),
                                "semaforo": _semaforo(ev), "riesgo": ev, "puntaje": round(plan.r_neto(com) * 0.55, 3)})
        if h20 and casos >= 8 and h20["subas"] / casos >= 0.65 and h20["promedio_pct"] >= 3:
            stop = (sop["desde"] if sop else precio - 2 * a) - 0.3 * a
            obj = precio * (1 + h20["promedio_pct"] / 100 * 1.5)
            if stop < precio < obj:
                plan = _plan(ctx, tk, precio, stop, obj, 40)
                ev = riesgo.evaluar(ctx, plan, estado, vetos)
                mediano.append({"ticker": tk, "sector": sector(tk), "plazo": "mediano", "setup": "La historia acompaña",
                                "motivo": f"En {casos} casos parecidos subió {h20['subas']} veces a 20 ruedas, {h20['promedio_pct']:+.1f}% promedio.",
                                "historia": hist_txt, "plan": plan.dict(), "r_neto": round(plan.r_neto(com), 2),
                                "semaforo": _semaforo(ev), "riesgo": ev, "puntaje": round(plan.r_neto(com) * h20["subas"] / casos, 3)})

    # CEDEARs relativamente baratos por dólar implícito (no necesitan historial).
    # Filtrado: solo líquidos, con un desvío que pague la comisión, y como máximo unos pocos por día
    # (la primera simulación mostró que los poco operados "baratos" no se corrigen solos).
    oc = {"cedear_desvio_min_pct": 3.0, "cedear_monto_min_ars": 20_000_000, "cedear_max": 3,
          **(config().get("oportunidades") or {})}
    med = ctx.extra.get("ccl_cedears_mediana")
    validos = ctx.extra.get("ccl_cedears") or {}  # solo CEDEARs con las dos líneas operadas hoy y desvío creíble
    baratos = []
    if med:
        for s, v in validos.items():
            t = ctx.titulo(s)
            if not t or (t.get("monto") or 0) < oc["cedear_monto_min_ars"]:
                continue
            desvio = (v / med - 1) * 100
            if desvio <= -oc["cedear_desvio_min_pct"]:
                baratos.append((desvio, t, s))
    for desvio, t, s in sorted(baratos, key=lambda x: x[0])[: oc["cedear_max"]]:
        precio = t.get("venta") or t["ultimo"]
        plan = _plan(ctx, s, precio, precio * 0.95, precio * (1 + abs(desvio) / 100 + 0.075), 10)
        ev = riesgo.evaluar(ctx, plan, estado, vetos)
        corto.append({"ticker": s, "sector": "cedears", "plazo": "corto", "setup": "CEDEAR barato por dólar implícito",
                      "motivo": f"Su dólar implícito está {abs(desvio):.1f}% debajo de la mediana: si se normaliza, gana esa diferencia además del subyacente.",
                      "historia": "Sin historial propio (se compara contra el resto de los CEDEARs).", "plan": plan.dict(),
                      "r_neto": round(plan.r_neto(com), 2), "semaforo": _semaforo(ev), "riesgo": ev,
                      "puntaje": round(plan.r_neto(com) * 0.5, 3)})

    orden = {"verde": 0, "amarillo": 1, "rojo": 2}
    for lista in (corto, mediano):
        lista.sort(key=lambda o: (orden[o["semaforo"]], -o["puntaje"]))
    return {"corto": corto[:8], "mediano": mediano[:8]}


def como_senales(ops: dict) -> list[Senal]:
    """Cada oportunidad verde/amarilla queda registrada para medir si el setup gana con el tiempo."""
    out = []
    for plazo, lista in ops.items():
        for o in lista:
            if o["semaforo"] != "rojo":
                out.append(Senal(f"oportunidades_{plazo}", o["ticker"], +1, min(1.0, max(0.1, o["puntaje"] / 2)),
                                 f"{o['setup']}: {o['motivo']}", {"setup": o["setup"]}))
    return out
