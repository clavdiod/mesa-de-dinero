"""Analistas por reglas fijas. Cada uno recibe el Contexto y devuelve una lista de Senal."""
from __future__ import annotations

import statistics as st

from ..nucleo import calc
from ..nucleo.config import config, sector
from ..nucleo.contexto import Contexto
from ..nucleo.modelos import Senal


def _ar(x: float, d: int = 2) -> str:
    """Número con formato argentino: 1.234,56"""
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


# 1. Acciones -----------------------------------------------------------------------------------
def acciones(ctx: Contexto) -> list[Senal]:
    out = []
    for t in ctx.grupo("acciones"):
        s, var, ult = t["simbolo"], t.get("variacion"), t.get("ultimo")
        if not s or var is None or not ult:
            continue
        velas = ctx.cache.velas(s) if ctx.cache else []
        vols = [v["volumen"] for v in velas[-20:] if v.get("volumen")]
        vol_rel = (t.get("volumen") or 0) / st.mean(vols) if len(vols) >= 10 and st.mean(vols) > 0 else None
        cierres = [v["cierre"] for v in velas] + [ult]
        m20 = calc.sma(cierres, 20)
        datos = {"variacion": round(var, 2), "vol_relativo": round(vol_rel, 2) if vol_rel else None,
                 "sobre_media20": (ult > m20) if m20 else None}
        if vol_rel and vol_rel >= 1.5 and var >= 1.5 and m20 and ult > m20:
            out.append(Senal("acciones", s, +1, _clip(0.4 + var / 10 + (vol_rel - 1.5) / 5),
                             f"Sube {var:.1f}% con volumen {vol_rel:.1f}x el promedio y arriba de su media de 20 ruedas.", datos))
        elif vol_rel and vol_rel >= 1.5 and var <= -2:
            out.append(Senal("acciones", s, -1, _clip(0.4 + abs(var) / 10),
                             f"Cae {abs(var):.1f}% con volumen {vol_rel:.1f}x: hay vendedores fuertes.", datos))
    return out


# 2. CEDEARs: CCL implícito relativo --------------------------------------------------------------
def cedears(ctx: Contexto) -> list[Senal]:
    """Compara el dólar implícito de cada CEDEAR (precio en pesos / precio en cable 'C').
    Un CEDEAR con CCL implícito bastante por debajo de la mediana está relativamente barato."""
    titulos = {t["simbolo"]: t for t in ctx.grupo("cedears") if t.get("simbolo") and t.get("ultimo")}
    ccls = {}
    for s, t in titulos.items():
        c = titulos.get(s + "C")
        if c and c["ultimo"] and not s.endswith(("C", "D")):
            ccls[s] = t["ultimo"] / c["ultimo"]
    if len(ccls) < 5:
        return []
    med = st.median(ccls.values())
    ctx.extra["ccl_cedears_mediana"] = round(med, 2)
    out = []
    for s, v in ccls.items():
        desvio = (v / med - 1) * 100
        if desvio <= -1.5:
            out.append(Senal("cedears", s, +1, _clip(abs(desvio) / 5),
                             f"Su dólar implícito ({_ar(v, 0)}) está {abs(desvio):.1f}% por debajo de la mediana de CEDEARs ({_ar(med, 0)}): relativamente barato.",
                             {"ccl_implicito": round(v, 2), "mediana": round(med, 2), "desvio_pct": round(desvio, 2)}))
        elif desvio >= 2.5:
            out.append(Senal("cedears", s, -1, _clip(desvio / 6),
                             f"Su dólar implícito está {desvio:.1f}% por encima de la mediana: relativamente caro.",
                             {"ccl_implicito": round(v, 2), "mediana": round(med, 2), "desvio_pct": round(desvio, 2)}))
    return out


# 3. ONs ----------------------------------------------------------------------------------------
def ons(ctx: Contexto) -> list[Senal]:
    """Con flujos cargados en config/ons.yaml calcula TIR y compara contra la mediana del grupo."""
    from ..nucleo.config import ons as datos_ons
    base = {**(datos_ons() or {}), **(ctx.extra.get("ons_usuario") or {})}
    tirs = {}
    for s, on in base.items():
        t = ctx.titulo(s)
        if not t or not t.get("ultimo"):
            continue
        flujo100 = calc.flujo_por_nominales(on, 100, ctx.fecha)
        r = calc.tir(t["ultimo"], flujo100, ctx.fecha)
        if r is not None:
            tirs[s] = r
    ctx.extra["tir_ons"] = tirs
    if len(tirs) < 3:
        return []
    med = st.median(tirs.values())
    out = []
    for s, r in tirs.items():
        if r - med >= 0.75:
            out.append(Senal("ons", s, +1, _clip((r - med) / 3),
                             f"Rinde {r:.2f}% anual, {r - med:.2f} puntos más que la mediana de ONs cargadas ({med:.2f}%).",
                             {"tir": r, "mediana": med}))
    return out


# 4. Soberanos ----------------------------------------------------------------------------------
def soberanos(ctx: Contexto) -> list[Senal]:
    out = []
    p = {s: (ctx.titulo(s) or {}).get("ultimo") for s in ("AL30", "AL30D", "AL30C", "GD30", "GD30D")}
    if p["AL30"] and p["AL30D"]:
        ctx.extra["mep_al30"] = round(p["AL30"] / p["AL30D"], 2)
    if p["AL30"] and p["AL30C"]:
        ctx.extra["ccl_al30"] = round(p["AL30"] / p["AL30C"], 2)
    if ctx.extra.get("mep_al30") and ctx.extra.get("ccl_al30"):
        ctx.extra["canje_pct"] = round((ctx.extra["ccl_al30"] / ctx.extra["mep_al30"] - 1) * 100, 2)
    # brecha de legislación GD30D vs AL30D frente a su propio historial
    if p["AL30D"] and p["GD30D"] and ctx.cache:
        al, gd = ctx.cache.velas("AL30D"), ctx.cache.velas("GD30D")
        gd_por_fecha = {v["fecha"]: v["cierre"] for v in gd}
        hist = [(gd_por_fecha[v["fecha"]] / v["cierre"] - 1) * 100 for v in al if v["fecha"] in gd_por_fecha]
        hoy = (p["GD30D"] / p["AL30D"] - 1) * 100
        ctx.extra["spread_gd_al_30"] = round(hoy, 2)
        if len(hist) >= 30:
            mu, sd = st.mean(hist[-60:]), st.pstdev(hist[-60:]) or 0.01
            z = (hoy - mu) / sd
            if z >= 2:
                out.append(Senal("soberanos", "AL30D", +1, _clip(z / 4),
                                 f"El GD30 está {hoy:.2f}% arriba del AL30 (normal {mu:.2f}%): el AL30 quedó barato en términos relativos.",
                                 {"spread": round(hoy, 2), "media": round(mu, 2), "z": round(z, 2)}))
    # riesgo país: suba fuerte = presión sobre todo lo argentino
    rp, ayer = ctx.riesgo_pais.get("valor"), ctx.riesgo_pais_ayer
    if rp and ayer and rp - ayer >= 20:
        for s in ("AL30D", "GD30D", "AL35D", "GD35D"):
            out.append(Senal("soberanos", s, -1, _clip((rp - ayer) / 60),
                             f"Riesgo país sube {rp - ayer:.0f} puntos ({ayer:.0f} → {rp:.0f}): los bonos siguen bajo presión.",
                             {"riesgo_pais": rp, "ayer": ayer}))
    return out


# 5. Pesos y tasas (contexto, no evaluable) -----------------------------------------------------
def pesos_tasas(ctx: Contexto) -> list[Senal]:
    cau = [t for t in ctx.grupo("cauciones") if t.get("ultimo")]
    if not cau:
        return []
    import re as _re
    corta = min(cau, key=lambda t: int((_re.findall(r"\d+", t["simbolo"] or "") or [999])[0]))
    ctx.extra["caucion_tna"] = corta["ultimo"]
    return [Senal("pesos_tasas", "PESOS", 0, 0.0, f"Caución más corta: {corta['ultimo']:.2f}% TNA.",
                  {"caucion": corta["ultimo"], "simbolo": corta["simbolo"]}, evaluable=False)]


# 6. Técnico ------------------------------------------------------------------------------------
def tecnico(ctx: Contexto, tickers: list[str]) -> list[Senal]:
    prm = {"rsi_bajo": 32, "rsi_alto": 72, "ventana_quiebre": 20, **ctx.params.get("tecnico", {})}
    out = []
    for s in tickers:
        t = ctx.titulo(s)
        velas = ctx.cache.velas(s) if ctx.cache else []
        if not t or not t.get("ultimo") or len(velas) < 50:
            continue
        ult = t["ultimo"]
        cierres = [v["cierre"] for v in velas] + [ult]
        r, m20, m50 = calc.rsi(cierres), calc.sma(cierres, 20), calc.sma(cierres, 50)
        w = int(prm["ventana_quiebre"])
        max_w = max(v["maximo"] for v in velas[-w:])
        min_w = min(v["minimo"] for v in velas[-w:])
        sop = calc.soporte_cercano(velas, ult)
        datos = {"rsi": round(r, 1) if r else None, "media20": m20, "media50": m50, "max_w": max_w, "min_w": min_w,
                 "soporte": sop}
        if ult > max_w and m20 and m50 and m20 > m50:
            out.append(Senal("tecnico", s, +1, 0.7, f"Quiebra el máximo de {w} ruedas ({_ar(max_w, 2)}) con tendencia alcista.", datos))
        elif ult < min_w:
            out.append(Senal("tecnico", s, -1, 0.7, f"Perfora el mínimo de {w} ruedas ({_ar(min_w, 2)}).", datos))
        elif r is not None and r <= prm["rsi_bajo"] and sop and ult <= sop["nivel"] * 1.03:
            out.append(Senal("tecnico", s, +1, 0.5,
                             f"Sobrevendido (RSI {r:.0f}) y a {(ult / sop['nivel'] - 1) * 100:.1f}% de un soporte que tocó {sop['toques']} veces.", datos))
        elif r is not None and r >= prm["rsi_alto"]:
            out.append(Senal("tecnico", s, -1, 0.4, f"Sobrecomprado (RSI {r:.0f}).", datos))
    return out


# 7. Macro / dólar: fija el clima de mercado ----------------------------------------------------
def macro_dolar(ctx: Contexto) -> list[Senal]:
    clima, motivos = 0.0, []
    rp, ayer = ctx.riesgo_pais.get("valor"), ctx.riesgo_pais_ayer
    if rp and ayer:
        d = rp - ayer
        clima -= _clip(d / 40, -1, 1)
        motivos.append(f"riesgo país {ayer:.0f}→{rp:.0f}")
    mep = (ctx.dolares.get("bolsa") or {}).get("venta")
    ccl = (ctx.dolares.get("contadoconliqui") or {}).get("venta")
    of = (ctx.dolares.get("oficial") or {}).get("venta")
    if mep and of:
        brecha = (mep / of - 1) * 100
        ctx.extra["brecha_mep_pct"] = round(brecha, 2)
        if brecha > 10:
            clima -= 0.3
            motivos.append(f"brecha MEP {brecha:.1f}%")
    if mep and ccl:
        ctx.extra["canje_dolarapi_pct"] = round((ccl / mep - 1) * 100, 2)
    ctx.clima = max(-1.0, min(1.0, clima))
    estado = "malo" if ctx.clima <= -0.3 else "bueno" if ctx.clima >= 0.3 else "neutral"
    ctx.extra["clima_estado"] = estado
    return [Senal("macro_dolar", "MERCADO", 0, abs(ctx.clima), f"Clima {estado}: " + (", ".join(motivos) or "sin datos"),
                  {"clima": round(ctx.clima, 2), "mep": mep, "ccl": ccl, "oficial": of,
                   "reservas": ctx.reservas.get("valor")}, evaluable=False)]


# 9. Historiador --------------------------------------------------------------------------------
def historiador(ctx: Contexto, tickers: list[str]) -> list[Senal]:
    cfg = {**config()["historiador"], **ctx.params.get("historiador", {})}
    out = []
    for s in tickers:
        velas = ctx.cache.velas(s) if ctx.cache else []
        t = ctx.titulo(s)
        if not t or not t.get("ultimo") or len(velas) < 80:
            continue
        cierres = [v["cierre"] for v in velas] + [t["ultimo"]]
        res = calc.patrones_parecidos(cierres, cfg["ventana"], cfg["correlacion_min"], tuple(cfg["horizontes"]))
        h10 = res["horizontes"].get(10)
        sop = calc.soporte_cercano(velas, t["ultimo"])
        datos = {**res, "soporte": sop, "evidencia": "debil" if res["casos"] < cfg["casos_minimos"] else "ok"}
        if not h10:
            continue
        pct_subas = h10["subas"] / res["casos"] * 100
        txt = (f"{res['casos']} gráficos parecidos: subió en {h10['subas']} ({pct_subas:.0f}%), "
               f"{h10['promedio_pct']:+.1f}% promedio a 10 ruedas.")
        if sop:
            txt += f" Soporte en {_ar(sop['nivel'], 2)} ({sop['toques']} toques)."
        if res["casos"] < cfg["casos_minimos"]:
            out.append(Senal("historiador", s, 0, 0.0, txt + " Evidencia débil: no pesa en la decisión.", datos))
        elif pct_subas >= 60 and h10["promedio_pct"] > 0:
            out.append(Senal("historiador", s, +1, _clip((pct_subas - 50) / 40), txt, datos))
        elif pct_subas <= 40 and h10["promedio_pct"] < 0:
            out.append(Senal("historiador", s, -1, _clip((50 - pct_subas) / 40), txt, datos))
    return out


def sector_de(s: str) -> str:
    return sector(s)
