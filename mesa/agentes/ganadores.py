"""26. Cazador de ganadores: las herramientas que usan los profesionales de Wall Street para encontrar a los
próximos ganadores ANTES de la gran suba, probadas con 5 años de historia de los CEDEARs (en dólares).

1. Plantilla de tendencia (Mark Minervini / William O'Neil, CAN SLIM): precio sobre sus promedios de 50, 150 y
   200 ruedas, ordenados, el de 200 subiendo, cerca del máximo de 52 semanas, lejos del mínimo y con fuerza
   relativa entre los mejores. Es el "filtro" que usan los fondos de momentum.
2. Ruptura de máximo de 52 semanas con volumen (George & Hwang 2004: los papeles cerca de su máximo anual
   siguen ganando; el mercado tarda en creer en ellos).
3. Gap con volumen (deriva post-resultados, PEAD: Bernard & Thomas 1989): cuando un papel abre muy arriba con
   volumen enorme (casi siempre por un buen balance), sigue subiendo semanas. Es lo que pasó con NOW esta semana.
4. Contracción de volatilidad (VCP de Minervini): el precio se "aprieta" cerca del máximo antes de despegar.

Cada estrategia se mide contra el promedio de todos los días (no alcanza con ganar: tiene que ganarle al azar y a
la comisión). Solo votan las que lo demuestran.
"""
from __future__ import annotations

import statistics as st

from ..nucleo.modelos import Senal

ESTRATEGIAS = {
    "tendencia": "Plantilla de tendencia (Minervini / CAN SLIM)",
    "maximo_52": "Ruptura del máximo de 52 semanas con volumen",
    "gap": "Gap con volumen (deriva post-resultados)",
    "contraccion": "Contracción de volatilidad cerca del máximo",
}


def _ma(c: list[float], n: int) -> float:
    return sum(c[-n:]) / n


def evaluar_dia(f: list[dict], i: int, rs_pct: float | None) -> dict[str, str]:
    """Qué estrategias se cumplen al cierre del día i (sin mirar el futuro). Devuelve {estrategia: motivo}."""
    if i < 260:
        return {}
    c = [x["c"] for x in f[: i + 1]]
    v = [x.get("v") or 0 for x in f[: i + 1]]
    hoy, ayer = f[i], f[i - 1]
    ma50, ma150, ma200, ma200_ant = _ma(c, 50), _ma(c, 150), _ma(c, 200), sum(c[-220:-20]) / 200
    mx52, mn52 = max(c[-252:]), min(c[-252:])
    v20 = st.mean(v[-21:-1]) or 1
    out = {}
    if c[-1] > ma50 > ma150 > ma200 and ma200 > ma200_ant and c[-1] >= 0.75 * mx52 and c[-1] >= 1.3 * mn52 and (rs_pct or 0) >= 0.7:
        out["tendencia"] = f"sobre sus promedios de 50/150/200 ordenados, a {(1 - c[-1] / mx52) * 100:.0f}% del máximo anual, fuerza relativa en el {rs_pct * 100:.0f}% superior"
    if c[-1] >= max(c[-253:-1]) and v[-1] >= 1.5 * v20:
        out["maximo_52"] = f"nuevo máximo de 52 semanas con volumen {v[-1] / v20:.1f} veces el normal"
    o = hoy.get("o") or c[-1]
    rango = (hoy["h"] - hoy["l"]) or 1e-9
    if o / ayer["c"] - 1 >= 0.04 and v[-1] >= 2.5 * v20 and (c[-1] - hoy["l"]) / rango >= 0.5:
        out["gap"] = f"abrió {(o / ayer['c'] - 1) * 100:.0f}% arriba con volumen {v[-1] / v20:.1f} veces el normal y cerró firme"
    r10 = max(c[-10:]) / min(c[-10:]) - 1
    r50 = max(c[-50:]) / min(c[-50:]) - 1
    if r50 > 0 and r10 / r50 < 0.35 and c[-1] >= 0.9 * mx52 and c[-1] > ma50:
        out["contraccion"] = f"el rango de 10 ruedas es {r10 / r50 * 100:.0f}% del de 50, pegado al máximo anual"
    return out


def _rs(series: dict[str, list[dict]], fecha_idx: dict[str, dict[str, int]], fecha: str) -> dict[str, float]:
    """Percentil de fuerza relativa (retorno de 6 meses) de cada papel en esa fecha."""
    r = {}
    for tk, f in series.items():
        i = fecha_idx[tk].get(fecha)
        if i is not None and i >= 126:
            r[tk] = f[i]["c"] / f[i - 126]["c"] - 1
    orden = sorted(r, key=r.get)
    n = len(orden)
    return {tk: (k + 1) / n for k, tk in enumerate(orden)} if n >= 10 else {}


def entrenar(series: dict[str, list[dict]], paso: int = 3) -> dict:
    """Prueba cada estrategia en 5 años: retorno a 20 y 60 ruedas contra el promedio de todos los días."""
    idx = {tk: {x["fecha"]: k for k, x in enumerate(f)} for tk, f in series.items()}
    fechas = sorted({x["fecha"] for f in series.values() for x in f})
    base = {20: [], 60: []}
    res: dict[str, dict[int, list]] = {e: {20: [], 60: []} for e in ESTRATEGIAS}
    ultimo: dict[tuple, int] = {}
    for n, fe in enumerate(fechas[260::paso]):
        rs = _rs(series, idx, fe)
        for tk, f in series.items():
            i = idx[tk].get(fe)
            if i is None or i + 60 >= len(f):
                continue
            for h in (20, 60):
                base[h].append((f[i + h]["c"] / f[i]["c"] - 1) * 100)
            for e in evaluar_dia(f, i, rs.get(tk)):
                if n - ultimo.get((tk, e), -99) < 7:  # no contar 7 veces la misma subida
                    continue
                ultimo[(tk, e)] = n
                for h in (20, 60):
                    res[e][h].append((f[i + h]["c"] / f[i]["c"] - 1) * 100)
    out = {"base": {h: {"casos": len(v), "promedio": round(st.mean(v), 2), "acierto": round(sum(1 for x in v if x > 0) / len(v) * 100, 1)}
                    for h, v in base.items() if v}, "estrategias": {}}
    for e, hs in res.items():
        d = {}
        for h, v in hs.items():
            if len(v) >= 20:
                d[h] = {"casos": len(v), "promedio": round(st.mean(v), 2), "mediana": round(st.median(v), 2),
                        "acierto": round(sum(1 for x in v if x > 0) / len(v) * 100, 1),
                        "exceso": round(st.mean(v) - out["base"][h]["promedio"], 2)}
        # el plazo es el que más le gana al promedio entre los que además aciertan más de la mitad
        validos = [h for h in d if d[h]["acierto"] >= 52 and d[h]["casos"] >= 40]
        h_mejor = max(validos or d, key=lambda h: d[h]["exceso"]) if d else None
        activa = bool(h_mejor in validos and d[h_mejor]["exceso"] >= 1.0)
        out["estrategias"][e] = {"nombre": ESTRATEGIAS[e], "horizontes": d, "plazo": h_mejor, "activa": activa}
    return out


def lista_hoy(series: dict[str, list[dict]]) -> list[dict]:
    idx = {tk: {x["fecha"]: k for k, x in enumerate(f)} for tk, f in series.items()}
    ult = max((f[-1]["fecha"] for f in series.values() if f), default=None)
    if not ult:
        return []
    rs = _rs(series, idx, ult)
    out = []
    for tk, f in series.items():
        if not f or f[-1]["fecha"] != ult:
            continue
        ev = evaluar_dia(f, len(f) - 1, rs.get(tk))
        if ev:
            out.append({"ticker": tk, "fecha": ult, "estrategias": ev, "rs": round((rs.get(tk) or 0) * 100)})
    return sorted(out, key=lambda x: (-len(x["estrategias"]), -x["rs"]))


def senales(lista: list[dict], prueba: dict, existe) -> list[Senal]:
    est = (prueba or {}).get("estrategias") or {}
    out = []
    for x in lista:
        act = [e for e in x["estrategias"] if (est.get(e) or {}).get("activa")]
        if not act or not existe(x["ticker"]):
            continue
        hz = lambda e: est[e]["horizontes"].get(str(est[e]["plazo"])) or est[e]["horizontes"].get(est[e]["plazo"]) or {}
        exc = max(hz(e).get("exceso", 0) for e in act)
        fuerza = round(min(0.8, 0.35 + 0.1 * len(act) + exc / 20), 2)
        txt = "; ".join(f"{ESTRATEGIAS[e]}: {x['estrategias'][e]}" for e in act)
        plazo = max(est[e]["plazo"] for e in act)
        out.append(Senal("ganadores", x["ticker"], 1, fuerza,
                         f"Cazador de ganadores — {txt}. En 5 años, esta configuración le ganó {exc:+.1f}% al promedio a {plazo} ruedas.",
                         {"estrategias": act, "plazo": plazo}))
    return out
