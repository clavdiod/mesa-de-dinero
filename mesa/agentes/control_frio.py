"""Control semanal de la revisión en frío (19/11, pedido de Clau: "revisar semanalmente, no sea cosa que por algo así
nos perdamos oportunidades").

Cada viernes, en el reentrenamiento, se vuelve a medir con 10 años de historia cada regla de 'entrada cara' de
ficha_frio. Solo con datos del pasado en cada fecha, operando como la mesa: entrada a la apertura siguiente, stop a 2 veces
el movimiento diario normal (3% a 10%), objetivo 2 veces el riesgo, máximo 20 ruedas y 1,2% de comisiones ida y vuelta.

Para cada regla se miran los casos que frenó SOLO esa regla y se comparan con los que pasan el frío:
- Si lo frenado rinde claramente MEJOR (0,5 puntos o más, con 200 casos o más): la regla es demasiado severa → se avisa.
- Si una regla apagada (REGLAS_APAGADAS) frena casos que rinden claramente PEOR: conviene volver a prenderla → se avisa.
No cambia nada solo: avisa en el informe de la semana y Clau decide.
"""
from __future__ import annotations

import numpy as np

from .ficha_frio import REGLAS_APAGADAS

COM = 0.012
NOMBRES = {"E": "estirada (6% arriba del promedio de 20 ruedas)", "R": "en el techo de su rango de 3 meses",
           "P": "lo que suele subir no paga 1,5 veces el riesgo", "M": "sin lugar hasta el máximo del año",
           "T": "en el 20% más alto del año (CEDEARs)"}
MARGEN, MIN_CASOS = 0.005, 200


def _sma(x, n):
    cs = np.cumsum(np.r_[0, x]); out = np.full(len(x), np.nan); out[n - 1:] = (cs[n:] - cs[:-n]) / n
    return out


def casos(ser: dict, cedear: bool) -> list[tuple]:
    """[(reglas, resultado_neto, subiendo, riesgo)] para cada papel y cada 2 ruedas de la historia."""
    filas = []
    for f in ser.values():
        c = np.array([x["c"] for x in f], float); o = np.array([x.get("o") or x["c"] for x in f], float)
        h = np.array([x.get("h") or x["c"] for x in f], float); l = np.array([x.get("l") or x["c"] for x in f], float)
        n = len(c)
        if n < 520 or (c <= 0).any():
            continue
        m20 = _sma(c, 20); d = c / m20 - 1
        r20 = np.full(n, np.nan); r20[20:] = c[20:] / c[:-20] - 1
        mxf = np.full(n, np.nan)
        for i in range(n - 20):
            mxf[i] = c[i + 1:i + 21].max() / c[i] - 1
        tr = np.maximum(h - l, np.abs(np.r_[0, h[1:] - c[:-1]]))
        atr = _sma(tr, 14)
        for i in range(400, n - 21, 2):
            ent = o[i + 1]
            if not ent or np.isnan(d[i]) or np.isnan(atr[i]):
                continue
            riesgo = float(np.clip(2 * atr[i] / c[i], 0.03, 0.10))
            hi60, lo60 = c[i - 59:i + 1].max(), c[i - 59:i + 1].min()
            pos60 = (c[i] - lo60) / (hi60 - lo60) if hi60 > lo60 else 0.5
            idx = np.arange(max(40, i - 400), i - 20)
            sel = idx[(np.abs(d[idx] - d[i]) <= 0.03) & (np.abs(r20[idx] - r20[i]) <= 0.06)]
            tip = np.median(mxf[sel]) if len(sel) >= 8 else None
            win = c[i - 249:i + 1]
            reglas = {"E": d[i] >= 0.06, "R": pos60 >= 0.85, "P": tip is not None and tip < 1.5 * riesgo,
                      "M": win.max() / c[i] - 1 < 2 * riesgo, "T": cedear and (win < c[i]).mean() >= 0.80}
            st_, ob = ent * (1 - riesgo), ent * (1 + 2 * riesgo)
            res = None
            for j in range(i + 1, i + 21):
                if l[j] <= st_:
                    res = -riesgo; break
                if h[j] >= ob:
                    res = 2 * riesgo; break
            if res is None:
                res = c[i + 20] / ent - 1
            filas.append((reglas, res - COM, bool(r20[i] >= 0.05 and c[i] > m20[i]), riesgo))
    return filas


def _st(xs):
    if not xs:
        return {"casos": 0}
    r = np.array([x[1] for x in xs])
    return {"casos": len(xs), "neto_pct": round(float(r.mean()) * 100, 2), "gana_pct": round(float(np.mean(r > 0)) * 100)}


def resumir(filas: list[tuple]) -> dict:
    out = {}
    for grupo, xs in (("todos", filas), ("subiendo", [x for x in filas if x[2]])):
        activas = lambda rg: any(v for k, v in rg.items() if k not in REGLAS_APAGADAS)
        g = {"todos": _st(xs), "pasa": _st([x for x in xs if not activas(x[0])]), "frena": _st([x for x in xs if activas(x[0])]), "reglas": {}}
        for k in NOMBRES:
            solo = [x for x in xs if x[0][k] and sum(x[0].values()) == 1]
            g["reglas"][k] = _st(solo)
        out[grupo] = g
    return out


def alertas(res: dict) -> list[str]:
    """Frases para el informe: reglas demasiado severas y reglas apagadas que conviene volver a prender."""
    lin = []
    for mercado, r in res.items():
        for k, nom in NOMBRES.items():
            ok_sev, ok_vol = True, True
            for grupo in ("todos", "subiendo"):
                g = r.get(grupo) or {}
                s, p = (g.get("reglas") or {}).get(k) or {}, g.get("pasa") or {}
                if s.get("casos", 0) < MIN_CASOS or p.get("casos", 0) < MIN_CASOS:
                    ok_sev = ok_vol = False; break
                ok_sev &= s["neto_pct"] >= p["neto_pct"] + MARGEN * 100
                ok_vol &= s["neto_pct"] <= p["neto_pct"] - MARGEN * 100
            g = (r.get("todos") or {})
            s, p = (g.get("reglas") or {}).get(k) or {}, g.get("pasa") or {}
            if k not in REGLAS_APAGADAS and ok_sev:
                lin.append(f"⚠️ {mercado}: la regla «{nom}» parece demasiado severa: lo que frena solo ella rindió {_p(s['neto_pct'])} "
                           f"contra {_p(p['neto_pct'])} de lo que pasa ({s['casos']} casos). Conviene revisarla.")
            elif k in REGLAS_APAGADAS and ok_vol:
                lin.append(f"⚠️ {mercado}: la regla apagada «{nom}» volvería a servir: esos casos rindieron {_p(s['neto_pct'])} "
                           f"contra {_p(p['neto_pct'])} ({s['casos']} casos). Conviene volver a prenderla.")
    return lin


def _p(x):
    return f"{'+' if x > 0 else ''}{x:.2f}%".replace(".", ",")


def medir(almacen, hoy) -> dict:
    """Corre la prueba con 10 años (Yahoo, gratis) y la guarda en revision/frio."""
    from concurrent.futures import ThreadPoolExecutor
    from . import anticipadores as A
    from ..datos import gratis
    from ..cierre import _universo_cedears
    res = {}
    try:
        panel = (almacen.get("ui/panel") or {}).get("titulos") or {}
        acc = A.datos_arg(sorted(tk for tk, x in panel.items() if x and x[4] == "acciones"), 10)[0]
        res["Acciones argentinas"] = resumir(casos(acc, False))
    except Exception as ex:
        print(f"[control frío] ARG: {ex}")
    try:
        uni = _universo_cedears(almacen)
        with ThreadPoolExecutor(8) as ex:
            ced = {tk: f for tk, f in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "10y"), uni)) if len(f) > 520}
        res["CEDEARs"] = resumir(casos(ced, True))
    except Exception as ex:
        print(f"[control frío] CEDEARs: {ex}")
    out = {"fecha": hoy.isoformat(), "apagadas": sorted(REGLAS_APAGADAS), "mercados": res, "alertas": alertas(res)}
    almacen.put("revision/frio", out)
    return out
