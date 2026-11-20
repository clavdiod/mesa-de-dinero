"""20/11: ¿Kostolany tiene razón? 1) El huevo: fase de pánico (cae 10%+ en 20 ruedas con volumen 1,5 veces o más) contra
fase de exageración (sube 10%+ con volumen 1,5 veces o más), a 3 meses, en acciones argentinas (en dólares) y CEDEARs.
2) Dinero: tasas que bajan → acciones que suben. EE.UU.: tasa a 10 años (^TNX) bajó/subió en 3 meses → SPY a 6 meses.
Argentina: tasa BADLAR del BCRA bajó/subió en 3 meses → ARGT a 6 meses."""
import bisect, traceback
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from mesa.agentes import anticipadores as A
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos import gratis
a = almacen_por_defecto(); COM = 0.012
pan = (a.get("ui/panel") or {}).get("titulos") or {}
def huevo(nombre, ser):
    g = {"panico": [], "exageracion": [], "resto": []}
    for f in ser.values():
        c = np.array([x["c"] for x in f], float); v = np.array([x.get("v") or 0 for x in f], float)
        if len(c) < 300 or v.sum() == 0: continue
        for i in range(60, len(c) - 61, 5):
            vb = v[i - 60:i - 20].mean()
            if vb <= 0: continue
            vr = v[i - 19:i + 1].mean() / vb; r = c[i] / c[i - 20] - 1; fw = c[i + 60] / c[i] - 1 - COM
            g["panico" if r <= -0.10 and vr >= 1.5 else "exageracion" if r >= 0.10 and vr >= 1.5 else "resto"].append(fw)
    t = lambda k: (f"{k}: {len(g[k])} · 3 meses mediana {np.median(g[k]) * 100:+.1f}% · suben {np.mean(np.array(g[k]) > 0) * 100:.0f}% · peor 10% {np.percentile(g[k], 10) * 100:+.0f}%" if len(g[k]) > 20 else f"{k}: pocos")
    print(f"::notice::HUEVO {nombre} | " + " | ".join(t(k) for k in g))
try:
    acc = A.datos_arg(sorted(tk for tk, x in pan.items() if x and x[4] == "acciones"), 10)[0]
    huevo("acciones argentinas (USD)", acc)
except Exception:
    print("::notice::ARG ERR " + traceback.format_exc()[-300:])
try:
    uni = [t for t, x in pan.items() if x and len(x) > 4 and x[4] == "cedears" and t.isalpha() and not t.endswith(("D", "C"))][:200]
    with ThreadPoolExecutor(8) as ex:
        ced = {t: v for t, v in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "10y"), uni)) if len(v) > 300}
    huevo("CEDEARs (EE.UU.)", ced)
except Exception:
    print("::notice::CED ERR " + traceback.format_exc()[-300:])
def liquidez(nombre, tasa: dict, acc: dict):
    ft = sorted(tasa); fa = sorted(acc); g = {"tasa baja 3m": [], "tasa sube 3m": []}
    for i in range(63, len(fa) - 127, 5):
        f = fa[i]; j = bisect.bisect_right(ft, f) - 1; j0 = bisect.bisect_right(ft, fa[i - 63]) - 1
        if j < 0 or j0 < 0: continue
        d = tasa[ft[j]] - tasa[ft[j0]]; fw = acc[fa[i + 126]] / acc[f] - 1
        g["tasa baja 3m" if d < 0 else "tasa sube 3m"].append(fw)
    print(f"::notice::DINERO {nombre} | " + " | ".join(f"{k}: {len(v)} · 6 meses mediana {np.median(v) * 100:+.1f}% · suben {np.mean(np.array(v) > 0) * 100:.0f}%" for k, v in g.items() if len(v) > 20))
try:
    tnx = {x["fecha"]: x["c"] for x in gratis.yahoo_ohlcv("^TNX", "max") if x["fecha"] >= "1995"}
    spy = {x["fecha"]: x["c"] for x in gratis.yahoo_ohlcv("SPY", "max")}
    liquidez("EE.UU. (tasa 10 años → SPY)", tnx, spy)
except Exception:
    print("::notice::EEUU ERR " + traceback.format_exc()[-300:])
try:
    from mesa.datos.macro_ar import bcra_serie
    from datetime import date
    bad = {}
    for y in range(2011, 2027, 5):
        bad.update(bcra_serie(7, date(y, 1, 1), min(date(y + 4, 12, 31), date.today())))
    argt = {x["fecha"]: x["c"] for x in gratis.yahoo_ohlcv("ARGT", "max")}
    print(f"::notice::badlar {len(bad)} datos")
    liquidez("Argentina (BADLAR → ARGT)", bad, argt)
except Exception:
    print("::notice::ARG tasa ERR " + traceback.format_exc()[-400:])
