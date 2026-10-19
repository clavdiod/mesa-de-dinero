"""Informe de cada analista sobre su mercado, en cada ronda (aunque no haya señales).

Cada informe: {titulo, resumen (texto), columnas, filas, nota}. Si hay IA, el resumen lo escribe Claude
con los números del informe; si no, se arma con reglas.
"""
from __future__ import annotations

import re
import statistics as st
from datetime import date

from ..nucleo import calc
from ..nucleo.contexto import Contexto

_MESES = {"E": 1, "F": 2, "M": 3, "A": 4, "Y": 5, "J": 6, "L": 7, "G": 8, "S": 9, "O": 10, "N": 11, "D": 12}


def _ar(x, d=2):
    if x is None:
        return "—"
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(x):
    return "—" if x is None else ("+" if x > 0 else "") + _ar(x) + "%"


def _base(t: str) -> bool:
    """Ticker en pesos (sin sufijo D/C de dólar MEP/cable)."""
    return not re.search(r"[A-Z0-9][DC]$", t) or len(t) <= 3


def _vto_letra(tk: str) -> date | None:
    """S30N6 → 30-nov-2026 (formato de LECAP/BONCAP: S|T|X + día + mes + año)."""
    m = re.match(r"^[STX](\d{2})([EFMAYJLGSOND])(\d)$", tk)
    if not m:
        return None
    try:
        return date(2020 + int(m.group(3)), _MESES[m.group(2)], int(m.group(1)))
    except ValueError:
        return None


def acciones(ctx: Contexto) -> dict:
    ts = [t for t in ctx.grupo("acciones") if t.get("ultimo") and t.get("variacion") is not None and _base(t["simbolo"])]
    if not ts:
        return {}
    suben = sum(t["variacion"] > 0 for t in ts)
    bajan = sum(t["variacion"] < 0 for t in ts)
    prom = st.mean(t["variacion"] for t in ts)
    top = sorted(ts, key=lambda t: t["variacion"], reverse=True)
    vol = sorted(ts, key=lambda t: t.get("monto") or 0, reverse=True)[:5]
    filas = [[t["simbolo"], _ar(t["ultimo"]), _pct(t["variacion"]), _ar((t.get("monto") or 0) / 1e6, 0)]
             for t in top[:5] + top[-5:]]
    return {"titulo": "Acciones", "columnas": ["Ticker", "Último", "Día", "Monto (M$)"], "filas": filas,
            "resumen": f"{suben} suben y {bajan} bajan (promedio {_pct(prom)}). Mejor: {top[0]['simbolo']} {_pct(top[0]['variacion'])}; "
                       f"peor: {top[-1]['simbolo']} {_pct(top[-1]['variacion'])}. Más operadas: {', '.join(t['simbolo'] for t in vol)}.",
            "nota": "Arriba las 5 que más suben, abajo las 5 que más bajan."}


def cedears(ctx: Contexto) -> dict:
    tit = {t["simbolo"]: t for t in ctx.grupo("cedears") if t.get("simbolo") and t.get("ultimo")}
    filas_ccl = []
    for s, t in tit.items():
        c = tit.get(s + "C")
        if c and c.get("ultimo") and _base(s):
            filas_ccl.append((s, t["ultimo"] / c["ultimo"], t.get("variacion"), t.get("monto") or 0))
    if len(filas_ccl) < 5:
        return {}
    filas_ccl = [f for f in filas_ccl if f[3] > 0] or filas_ccl  # solo los que operaron
    med = st.median(f[1] for f in filas_ccl)
    orden = sorted(filas_ccl, key=lambda f: f[1])
    filas = [[s, _ar(v), _pct((v / med - 1) * 100), _pct(var)] for s, v, var, _ in orden[:6] + orden[-6:]]
    return {"titulo": "CEDEARs", "columnas": ["Ticker", "CCL implícito", "vs mediana", "Día"], "filas": filas,
            "resumen": f"Dólar implícito mediano de los CEDEARs: {_ar(med)}. Más baratos: {', '.join(f[0] for f in orden[:3])}; "
                       f"más caros: {', '.join(f[0] for f in orden[-3:])}.",
            "nota": "Arriba los de dólar implícito más bajo (relativamente baratos), abajo los más caros. Solo CEDEARs que operaron hoy."}


def bonos(ctx: Contexto) -> dict:
    p = {t["simbolo"]: t for t in ctx.grupo("soberanos") if t.get("simbolo") and t.get("ultimo")}
    filas = []
    for base in ("AL29", "AL30", "AL35", "AE38", "AL41", "GD29", "GD30", "GD35", "GD38", "GD41", "GD46"):
        ars, usd, cab = p.get(base), p.get(base + "D"), p.get(base + "C")
        if not (ars and usd):
            continue
        mep = ars["ultimo"] / usd["ultimo"]
        ccl = ars["ultimo"] / cab["ultimo"] if cab else None
        filas.append([base, _ar(usd["ultimo"]), _pct(usd.get("variacion")), _ar(mep), _ar(ccl)])
    if not filas:
        return {}
    rp, ayer = ctx.riesgo_pais.get("valor"), ctx.riesgo_pais_ayer
    sp = ctx.extra.get("spread_gd_al_30")
    txt = f"Riesgo país {_ar(rp, 0)}" + (f" (ayer {_ar(ayer, 0)})" if ayer else "") + ". "
    txt += f"MEP AL30 {_ar(ctx.extra.get('mep_al30'))}, CCL AL30 {_ar(ctx.extra.get('ccl_al30'))}, canje {_pct(ctx.extra.get('canje_pct'))}. "
    if sp is not None:
        txt += f"GD30 cotiza {_pct(sp)} sobre AL30."
    return {"titulo": "Bonos soberanos en dólares", "columnas": ["Bono", "Precio US$", "Día", "MEP", "CCL"],
            "filas": filas, "resumen": txt, "nota": "Precio en dólares MEP (especie D), cada 100 nominales."}


def ons(ctx: Contexto) -> dict:
    ts = [t for t in ctx.grupo("ons") if t.get("ultimo") and t["simbolo"].endswith("D")]
    if not ts:
        return {}
    tirs = ctx.extra.get("tir_ons") or {}
    ts.sort(key=lambda t: t.get("volumen") or 0, reverse=True)
    filas = []
    for t in ts[:15]:
        c, v = t.get("compra"), t.get("venta")
        spread = (v / c - 1) * 100 if c and v else None
        filas.append([t["simbolo"], _ar(t["ultimo"]), _pct(t.get("variacion")), _pct(spread),
                      _ar(tirs.get(t["simbolo"])) + "%" if tirs.get(t["simbolo"]) else "—"])
    bajo_par = sum(t["ultimo"] < 100 for t in ts)
    return {"titulo": "Obligaciones negociables (US$ MEP)", "columnas": ["ON", "Precio", "Día", "Spread", "TIR"],
            "filas": filas, "resumen": f"{len(ts)} ONs en dólares MEP con precio. {bajo_par} cotizan bajo la par (menos de 100). "
                                       f"Las 15 más operadas, con su spread compra/venta. "
                                       f"TIR calculada para {len(tirs)} (las que tienen flujos cargados en Cobros).",
            "nota": "Fuente gratis (data912), no gasta cupo de IOL. Para TIR y cobros, cargá los flujos de la ON en la pestaña Cobros."}


def letras(ctx: Contexto) -> dict:
    filas = []
    for t in ctx.grupo("letras"):
        v = _vto_letra(t["simbolo"] or "")
        if not v or not t.get("ultimo") or v <= ctx.fecha:
            continue
        dias = (v - ctx.fecha).days
        filas.append((v, [t["simbolo"], v.strftime("%d/%m/%Y"), str(dias), _ar(t["ultimo"], 3), _pct(t.get("variacion"))]))
    if not filas:
        return {}
    filas.sort()
    return {"titulo": "Letras y bonos a tasa fija (LECAP/BONCAP)", "columnas": ["Ticker", "Vence", "Días", "Precio", "Día"],
            "filas": [f for _, f in filas], "resumen": f"{len(filas)} letras/bonos a tasa fija con precio, ordenados por vencimiento.",
            "nota": "La tasa (TNA/TEM) necesita el valor final de cada letra; se agrega cuando cargues sus datos."}


def pesos(ctx: Contexto) -> dict:
    cau = [t for t in ctx.grupo("cauciones") if t.get("ultimo")]
    if not cau:
        return {}
    filas = [[t["descripcion"] or t["simbolo"], _ar(t["ultimo"]) + "%", _ar((t.get("monto") or 0) / 1e6, 0), t.get("fecha") or "—"] for t in cau[:8]]
    return {"titulo": "Pesos y tasas (cauciones)", "columnas": ["Plazo", "TNA", "Monto (M$)", "Fecha"], "filas": filas,
            "resumen": f"Caución más corta: {filas[0][1]} TNA.", "nota": "Datos del panel de cauciones de IOL."}


def tecnico_historiador(ctx: Contexto) -> dict:
    filas = []
    for tk in sorted(ctx.cache.indice) if ctx.cache else []:
        t = ctx.titulo(tk)
        velas = ctx.cache.velas(tk)
        if not t or not t.get("ultimo") or len(velas) < 60:
            continue
        cierres = [v["cierre"] for v in velas] + [t["ultimo"]]
        r = calc.rsi(cierres)
        m50 = calc.sma(cierres, 50)
        sop = calc.soporte_cercano(velas, t["ultimo"])
        pat = calc.patrones_parecidos(cierres, 20, 0.85, (10,))
        h = pat["horizontes"].get(10)
        hist = f"{h['subas']}/{pat['casos']} subió, {_pct(h['promedio_pct'])}" if h else "sin casos"
        filas.append([tk, _ar(r, 0), "arriba" if m50 and t["ultimo"] > m50 else "abajo",
                      f"{_ar(sop['nivel'])} ({sop['toques']}x, {_pct((t['ultimo'] / sop['nivel'] - 1) * 100)})" if sop else "—",
                      hist])
    if not filas:
        return {}
    return {"titulo": "Técnico e Historiador", "columnas": ["Ticker", "RSI", "Media 50", "Soporte (distancia)", "Gráficos parecidos a 10 ruedas"],
            "filas": filas, "resumen": f"{len(filas)} activos con historial suficiente. RSI < 30 = sobrevendido, > 70 = sobrecomprado.",
            "nota": "Gráficos parecidos: de los casos históricos con forma similar, en cuántos subió a 10 ruedas y cuánto en promedio. Menos de 8 casos es evidencia débil."}


def licitaciones(ctx: Contexto) -> dict:
    d = ctx.extra.get("licitaciones") or {}
    if not d:
        return {}
    prox, ult = d.get("proxima") or {}, d.get("ultima") or {}
    filas = []
    if prox:
        filas.append(["Próxima", prox.get("fecha") or "—", ", ".join(prox.get("instrumentos") or []) or "—",
                      prox.get("vencimientos_a_cubrir") or "—"])
    if ult:
        filas.append(["Última", ult.get("fecha") or "—", ult.get("tasas") or "—",
                      f"rollover {ult['rollover_pct']}%" if ult.get("rollover_pct") else "—"])
    for t in (d.get("titulares") or [])[:6]:
        filas.append(["Noticia", (t.get("fecha") or "")[:10], t.get("titulo", "")[:90], ""])
    return {"titulo": "Licitaciones del Tesoro", "columnas": ["", "Fecha", "Detalle", ""], "filas": filas,
            "resumen": d.get("lectura") or "Últimas noticias sobre licitaciones del Tesoro (se actualiza cada mañana).",
            "nota": f"Actualizado {d.get('actualizado', '—')}. Fuente: noticias; verificá el llamado oficial en argentina.gob.ar/economia/finanzas."}


def todos(ctx: Contexto, ia=None) -> dict:
    out = {}
    for nombre, fn in (("acciones", acciones), ("cedears", cedears), ("bonos", bonos), ("ons", ons),
                       ("letras", letras), ("licitaciones", licitaciones), ("pesos", pesos), ("tecnico", tecnico_historiador)):
        try:
            r = fn(ctx)
        except Exception as e:  # un informe roto no frena la ronda
            print(f"[informe] {nombre}: {e}")
            r = {}
        if r:
            out[nombre] = r
    if ia is not None and ia.disponible and out:
        import json
        res = ia.json("Sos el jefe de análisis de una mesa de dinero argentina. Para cada informe escribí 2 oraciones claras "
                      "para alguien que decide desde el celular: qué está pasando y qué mirar. Usá solo los números dados. "
                      "Formato: {\"acciones\":\"...\",\"cedears\":\"...\"} con las mismas claves recibidas.",
                      json.dumps({k: {"resumen": v["resumen"], "filas": v["filas"][:8]} for k, v in out.items()}, ensure_ascii=False)[:8000])
        if isinstance(res, dict):
            for k, txt in res.items():
                if k in out and isinstance(txt, str):
                    out[k]["lectura_ia"] = txt
    return out
