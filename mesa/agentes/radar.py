"""Radar del mercado: todos los analistas vigilan TODO el mercado y están obligados a avisar lo anormal.

En cada ronda se revisa el panel completo y se levanta una alerta cuando aparece:
- Volumen fuera de lo normal: el volumen proyectado del día (según la hora) es 2,5 veces su promedio o más.
- Movimiento fuerte de precio: ±4% en acciones/CEDEARs, ±2% en bonos y ONs.
- ADR despegado: el ADR en Nueva York (con el CCL) va 1,5% o más distinto que la acción local.
- Macro: el CCL se mueve 1,5% en el día, el riesgo país salta 25 puntos, el dólar cripto se despega 1,5% del CCL.

Cada alerta obliga a investigar: los papeles marcados entran al análisis de TODOS los analistas en esa misma
ronda (Técnico, Historiador, Wall Street, Cripto, Economista...), se buscan noticias del emisor, se mira el
calendario (balance, pago, dividendo) y se arma una conclusión de "qué está pasando".
"""
from __future__ import annotations

import statistics as st
from datetime import timedelta

from ..nucleo.config import nombre_emisor

UMBRAL_PRECIO = {"acciones": 4.0, "cedears": 4.0, "soberanos": 2.0, "ons": 2.0}


def detectar(ctx, minuto: int, adr_brechas: dict[str, float] | None = None, rp_ayer: float | None = None,
             ccl_ayer: float | None = None) -> list[dict]:
    frac = min(1.0, max(0.15, (minuto - 630) / 390))
    out = []
    for grupo in ("acciones", "cedears", "soberanos", "ons"):
        for t in ctx.grupo(grupo):
            tk = t.get("simbolo")
            if not tk or not t.get("ultimo"):
                continue
            # volumen (solo si hay historial con volumen real del mercado local)
            velas = ctx.cache.velas(tk) if ctx.cache and tk in ctx.cache.indice else []
            vols = [v["volumen"] for v in velas[-30:] if v.get("volumen")][-20:]
            if len(vols) >= 10 and (t.get("volumen") or 0) and st.mean(vols):
                rel = (t["volumen"] / frac) / st.mean(vols)
                if rel >= 2.5 and (t.get("monto") or 0) >= 5_000_000:
                    out.append({"tipo": "volumen", "ticker": tk, "grupo": grupo, "valor": round(rel, 1),
                                "severidad": "alta" if rel >= 4 else "media",
                                "texto": f"{tk}: volumen camino a {rel:.1f} veces lo normal ({t.get('variacion') or 0:+.1f}% en el día)."})
            var = t.get("variacion")
            if var is not None and abs(var) >= UMBRAL_PRECIO[grupo] and (t.get("monto") or 0) >= 2_000_000:
                out.append({"tipo": "precio", "ticker": tk, "grupo": grupo, "valor": round(var, 2),
                            "severidad": "alta" if abs(var) >= 2 * UMBRAL_PRECIO[grupo] else "media",
                            "texto": f"{tk}: {'sube' if var > 0 else 'cae'} {var:+.1f}% en el día."})
    for tk, b in (adr_brechas or {}).items():
        if b is not None and abs(b) >= 1.5:
            out.append({"tipo": "adr", "ticker": tk, "grupo": "acciones", "valor": b, "severidad": "alta" if abs(b) >= 3 else "media",
                        "texto": f"{tk}: su ADR en Nueva York va {b:+.1f}% distinto que la acción local."})
    rp = ctx.riesgo_pais.get("valor")
    if rp and rp_ayer and rp - rp_ayer >= 25:
        out.append({"tipo": "macro", "ticker": "RIESGO PAÍS", "grupo": "macro", "valor": rp - rp_ayer, "severidad": "alta",
                    "texto": f"El riesgo país salta {rp - rp_ayer:+.0f} puntos en el día ({rp:.0f})."})
    ccl = (ctx.dolares.get("contadoconliqui") or {}).get("venta")
    if ccl and ccl_ayer and abs(ccl / ccl_ayer - 1) * 100 >= 1.5:
        v = (ccl / ccl_ayer - 1) * 100
        out.append({"tipo": "macro", "ticker": "DÓLAR CCL", "grupo": "macro", "valor": round(v, 2), "severidad": "alta" if abs(v) >= 3 else "media",
                    "texto": f"El dólar CCL se mueve {v:+.1f}% en el día ({ccl:,.0f}).".replace(",", ".")})
    cripto = (ctx.dolares.get("cripto") or {}).get("venta")
    if cripto and ccl and abs(cripto / ccl - 1) * 100 >= 1.5:
        v = (cripto / ccl - 1) * 100
        out.append({"tipo": "macro", "ticker": "DÓLAR CRIPTO", "grupo": "macro", "valor": round(v, 2), "severidad": "media",
                    "texto": f"El dólar cripto está {v:+.1f}% contra el CCL: puede anticipar un movimiento del dólar de bolsa."})
    # una alerta por ticker (la más severa); varias causas se juntan en el texto
    por_tk: dict[str, dict] = {}
    for a in out:
        p = por_tk.get(a["ticker"])
        if not p:
            por_tk[a["ticker"]] = {**a, "tipos": [a["tipo"]]}
        else:
            p["tipos"].append(a["tipo"])
            p["texto"] += " " + a["texto"].split(": ", 1)[-1]
            if a["severidad"] == "alta":
                p["severidad"] = "alta"
    return sorted(por_tk.values(), key=lambda a: (a["severidad"] != "alta", -abs(a["valor"])))


def investigar(alerta: dict, ctx, por_ticker: dict, noticias_emisor: list[dict], nombres_ag: dict) -> dict:
    """Arma el análisis de la alerta: qué dice cada analista, noticias, calendario y conclusión."""
    tk = alerta["ticker"]
    sen = [s for s in por_ticker.get(tk, []) if s.texto]
    opiniones = [{"agente": nombres_ag.get(s.agente, s.agente), "dir": s.direccion, "texto": s.texto}
                 for s in sorted(sen, key=lambda s: -s.fuerza)[:8]]
    favor, contra = sum(1 for s in sen if s.direccion > 0), sum(1 for s in sen if s.direccion < 0)
    lim_a, lim_b = (ctx.fecha - timedelta(days=3)).isoformat(), (ctx.fecha + timedelta(days=3)).isoformat()
    ev = [e for e in ctx.eventos if e.get("ticker") in (tk, tk[:-1]) and lim_a <= e.get("fecha", "") <= lim_b]
    causas = []
    if noticias_emisor:
        causas.append(f"Hay noticias recientes: «{noticias_emisor[0]['titulo'][:120]}»")
    for e in ev:
        causas.append(f"Calendario: {e.get('nombre')} ({e['fecha'][8:10]}/{e['fecha'][5:7]})")
    if "adr" in alerta.get("tipos", []):
        causas.append("Diferencia con Nueva York: si el ADR lidera, la acción local suele acomodarse.")
    if alerta["grupo"] == "macro":
        conclusion = "Movimiento de mercado general: revisar CEDEARs (cobertura) y bonos; la mesa ajusta el clima en esta misma ronda."
    elif causas:
        conclusion = "Probable causa: " + causas[0] + "."
    elif "volumen" in alerta.get("tipos", []):
        conclusion = ("Volumen alto sin noticia ni evento a la vista: alguien sabe o espera algo. "
                      "Ojo con entrar sin entender por qué; seguirlo de cerca.")
    else:
        conclusion = "Movimiento sin causa visible todavía: seguirlo en las próximas rondas."
    lectura = ("La mayoría de los analistas lo ve a favor." if favor > contra else
               "La mayoría de los analistas lo ve en contra." if contra > favor else "Los analistas están divididos o sin opinión.")
    return {**alerta, "hora": ctx.hora, "opiniones": opiniones, "favor": favor, "contra": contra, "lectura": lectura,
            "noticias": [{"titulo": n["titulo"], "link": n.get("link")} for n in noticias_emisor[:3]],
            "eventos": [{"fecha": e["fecha"], "nombre": e.get("nombre")} for e in ev], "conclusion": conclusion,
            "emisor": nombre_emisor(tk)}
