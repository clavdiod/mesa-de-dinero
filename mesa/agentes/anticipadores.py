"""31. Dos anticipadores más, con el mismo método que viene funcionando (precursores de una suba de 5% en la semana):

- Anticipador ARG: solo acciones argentinas, con el contexto de acá en vez del de Wall Street:
  Merval de los últimos 5 días, nivel del riesgo país y cómo se movió el CCL.
- Anticipador Mundo: CEDEARs con lo que pasa en el mundo además de su gráfico: petróleo, oro, cobre, dólar global,
  tasa a 10 años de EE.UU., Japón y Alemania (lo que cerró de noche y a la mañana) y cómo viene el sector de cada
  empresa. La idea: llegar días antes de que el movimiento global se note en el papel.

Cada uno se prueba con la historia (70% para aprender, 30% final para examinar) y solo vota si pasa el examen.
"""
from __future__ import annotations

import numpy as np

from . import anticipo
from ..nucleo.modelos import Senal

NOMBRES_ARG = anticipo.NOMBRES[:8] + ["Merval 5 días", "riesgo país", "CCL 5 días"]
GLOBALES = {"petroleo": "CL=F", "oro": "GC=F", "cobre": "HG=F", "dolar_global": "DX-Y.NYB", "tasa10": "^TNX",
            "japon": "^N225", "alemania": "^GDAXI"}
NOMBRES_MUNDO = anticipo.NOMBRES + ["petróleo 5 días", "oro 5 días", "cobre 5 días", "dólar global 5 días", "tasa 10 años 5 días",
                                    "Japón 1 día", "Alemania 1 día", "sector 5 días", "sector contra el mercado 20 días"]


_CLAVES: dict[int, list[str]] = {}


def _r(serie: dict, fecha: str, n: int) -> float:
    """Variación de los últimos n días hasta la fecha (sin mirar después). Rápido: busca con bisect."""
    if not serie:
        return 0.0
    import bisect
    ks = _CLAVES.get(id(serie))
    if ks is None or len(ks) != len(serie) or ks[0] not in serie or ks[-1] not in serie:
        ks = _CLAVES[id(serie)] = sorted(serie)
    j = bisect.bisect_right(ks, fecha) - 1
    if j - n < 0:
        return 0.0
    a, b = serie[ks[j - n]], serie[ks[j]]
    return (b / a - 1) if a else 0.0


# ---------- Argentina ----------
def entrenar_arg(acciones: dict[str, list[dict]], merval: dict, riesgo_pais: dict, ccl: dict, desde_prueba: str | None = None, **kw) -> dict:
    m = anticipo.entrenar(acciones, merval, riesgo_pais, ccl, nombres=NOMBRES_ARG, desde_prueba=desde_prueba, **kw)
    m["nombre"] = "Anticipador ARG"
    return m


def lista_arg(modelo: dict, acciones: dict[str, list[dict]], merval: dict, riesgo_pais: dict, ccl: dict, fecha: str) -> list[dict]:
    cx = anticipo.contexto_mkt(fecha, dict(sorted(merval.items())), dict(sorted(riesgo_pais.items())), dict(sorted(ccl.items())))
    return anticipo.puntuar(modelo, acciones, cx)


def a_dolares(series: dict[str, list[dict]], ccl: dict) -> dict[str, list[dict]]:
    """Pasa las velas en pesos a dólares CCL del mismo día (le saca el efecto de la inflación y la devaluación)."""
    import bisect
    fs = sorted(ccl)
    out = {}
    for tk, f in series.items():
        v = []
        for x in f:
            j = bisect.bisect_right(fs, x["fecha"]) - 1
            if j < 0 or not ccl[fs[j]]:
                continue
            c = ccl[fs[j]]
            v.append({**x, "c": x["c"] / c, "h": x["h"] / c, "l": x["l"] / c, "o": ((x.get("o") or x["c"]) / c)})
        out[tk] = v
    return out


def merval_dolares(merval: dict, ccl: dict) -> dict:
    import bisect
    fs = sorted(ccl)
    return {f: v / ccl[fs[bisect.bisect_right(fs, f) - 1]] for f, v in merval.items() if fs and f >= fs[0]}


def datos_arg(tickers: list[str], anios: int = 10) -> tuple[dict, dict, dict, dict]:
    """5-10 años gratis de Yahoo (.BA), Merval, riesgo país y CCL. Devuelve (acciones en USD, merval USD, riesgo país, ccl)."""
    from concurrent.futures import ThreadPoolExecutor
    from ..datos import gratis
    with ThreadPoolExecutor(8) as ex:
        ser = {tk: f for tk, f in zip(tickers, ex.map(lambda t: gratis.yahoo_ohlcv(t + ".BA", f"{anios}y"), tickers)) if len(f) > 300}
    macro = gratis.series_macro(anios)
    rp, ccl = macro.get("riesgo_pais") or {}, macro.get("ccl") or {}
    merval = {f: c for f, c in gratis.yahoo("^MERV", f"{anios}y")}
    return {k: v for k, v in a_dolares(ser, ccl).items() if len(v) > 300}, merval_dolares(merval, ccl), rp, ccl


# ---------- Mundo ----------
def _ctx_mundo(glob: dict[str, dict], spy: dict, vix: dict, btc: dict):
    def fn(fe: str) -> dict:
        cx = anticipo.contexto_mkt(fe, spy, vix, btc)
        cx.update({"petroleo": _r(glob.get("petroleo"), fe, 5), "oro": _r(glob.get("oro"), fe, 5), "cobre": _r(glob.get("cobre"), fe, 5),
                   "dolar_global": _r(glob.get("dolar_global"), fe, 5), "tasa10": _r(glob.get("tasa10"), fe, 5),
                   "japon": _r(glob.get("japon"), fe, 1), "alemania": _r(glob.get("alemania"), fe, 1), "fecha": fe})
        return cx
    return fn


def _rasgos_mundo(sector_de: dict[str, str], etfs: dict[str, dict], spy: dict):
    def fn(f, i, cx, tk):
        base = anticipo.rasgos(f, i, cx)
        if base is None:
            return None
        fe = cx.get("fecha") or f[i]["fecha"]
        etf = etfs.get(sector_de.get(tk) or "") or {}
        s5 = _r(etf, fe, 5)
        rs20 = _r(etf, fe, 20) - _r(spy, fe, 20) if etf else 0.0
        return base + [cx["petroleo"], cx["oro"], cx["cobre"], cx["dolar_global"], cx["tasa10"], cx["japon"], cx["alemania"], s5, rs20]
    return fn


def entrenar_mundo(cedears: dict[str, list[dict]], spy: dict, vix: dict, btc: dict, glob: dict[str, dict],
                   sector_de: dict[str, str], etfs: dict[str, dict], **kw) -> dict:
    spy_o, vix_o, btc_o = dict(sorted(spy.items())), dict(sorted(vix.items())), dict(sorted(btc.items()))
    glob = {k: dict(sorted(v.items())) for k, v in glob.items()}
    etfs = {k: dict(sorted(v.items())) for k, v in etfs.items()}
    m = anticipo.entrenar(cedears, spy_o, vix_o, btc_o, ctx_fn=_ctx_mundo(glob, spy_o, vix_o, btc_o),
                          rasgos_fn=_rasgos_mundo(sector_de, etfs, spy_o), nombres=NOMBRES_MUNDO, **kw)
    m["nombre"] = "Anticipador Mundo"
    # tiene que agregar algo: si elige lo mismo que el Anticipador común, votaría dos veces la misma idea
    base = anticipo.entrenar(cedears, spy_o, vix_o, btc_o, **kw)
    pb, pm = base.get("prueba") or {}, m.get("prueba") or {}
    mejora = (pm.get("top10_pct", 0) - pb.get("top10_pct", 0) >= 2) or (pm.get("ret5_top10", 0) - pb.get("ret5_top10", 0) >= 0.3)
    m["base"] = pb
    if m.get("activo") and not mejora:
        m["activo"] = False
        m["motivo"] = (m.get("motivo") or "") + (f" Pero no mejora al Anticipador común ({pm.get('top10_pct')} contra {pb.get('top10_pct')} de cada 100, "
                                                 f"{pm.get('ret5_top10')}% contra {pb.get('ret5_top10')}% a 5 ruedas): lo que pasa en el mundo ya está en el "
                                                 "gráfico de cada papel. Queda en observación.")
    return m


def lista_mundo(modelo: dict, cedears: dict[str, list[dict]], spy: dict, vix: dict, btc: dict, glob: dict[str, dict],
                sector_de: dict[str, str], etfs: dict[str, dict], fecha: str) -> list[dict]:
    spy_o, vix_o, btc_o = dict(sorted(spy.items())), dict(sorted(vix.items())), dict(sorted(btc.items()))
    glob = {k: dict(sorted(v.items())) for k, v in glob.items()}
    etfs = {k: dict(sorted(v.items())) for k, v in etfs.items()}
    cx = _ctx_mundo(glob, spy_o, vix_o, btc_o)(fecha)
    out = anticipo.puntuar(modelo, cedears, cx, rasgos_fn=_rasgos_mundo(sector_de, etfs, spy_o))
    for x in out:  # qué del mundo empuja hoy
        mov = [(k, cx[k]) for k in ("petroleo", "oro", "cobre", "japon", "alemania") if abs(cx.get(k) or 0) >= 0.02]
        if mov:
            nom = {"petroleo": "petróleo", "oro": "oro", "cobre": "cobre", "japon": "Japón", "alemania": "Alemania"}
            x["razones"] = x["razones"] + ["mundo: " + ", ".join(f"{nom[k]} {v * 100:+.0f}%" for k, v in mov)]
    return out


# ---------- votos ----------
AGENTES = {"anticipador": ("anticipo/lista", "Anticipador"), "anticipador_arg": ("anticipo_arg/lista", "Anticipador ARG"),
           "anticipador_mundo": ("anticipo_mundo/lista", "Anticipador Mundo")}


def senales(agente: str, lista: dict, existe, fr_debil: set[str]) -> list[Senal]:
    out = []
    if not lista.get("activo"):
        return out
    nom = AGENTES[agente][1]
    vol = lista.get("volatil") or {}
    pv = float(vol.get("peso") or 1.0) if vol.get("hoy") else 1.0  # en días volátiles pesa según cómo anduvo en días así
    for x in lista.get("lista") or []:
        x["fr_contra"] = x["ticker"] in fr_debil
        if existe(x["ticker"]):
            out.append(Senal(agente, x["ticker"], 1, round(min(0.8, 0.3 + x["prob"]) * (0.5 if x["fr_contra"] else 1) * pv, 2),
                             f"{nom}: precursores de suba para esta semana ({x['prob'] * 100:.0f}% de probabilidad de subir 5% o más): "
                             + (", ".join(x["razones"]) or "combinación de señales previas") + "."
                             + (f" Día volátil: {'lo eligió el especialista en días así' if vol.get('especialista') else 'el modelo de siempre anda bien en días así'}." if vol.get("hoy") else ""), x))
    return out


def resumen_prueba(m: dict) -> dict:
    return {"activo": m.get("activo"), "umbral": m.get("umbral"), "prueba": m.get("prueba"), "motivo": m.get("motivo"),
            "importancia": m.get("importancia")}


def a_array(x):  # para tests
    return np.array(x)
