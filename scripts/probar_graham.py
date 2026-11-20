"""20/11: ¿lo de Graham funciona con los CEDEARs? Con lo publicado en la SEC hasta cada fecha (sin mirar el futuro):
el día después de cada balance anual se miden los 7 criterios y el margen de seguridad, y se ve cuánto rindió la acción
en los 12 meses siguientes contra el S&P 500 (SPY) en el mismo período."""
import bisect, time, traceback
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.cierre import _universo_cedears
from mesa.agentes import biblioteca as B
from mesa.agentes.fundamentos import _ciks, NO_EMPRESA
from mesa.datos import gratis
a = almacen_por_defecto()
uni = [t for t in _universo_cedears(a) if t not in NO_EMPRESA][:120]
cik = _ciks()
spy = gratis.yahoo_ohlcv("SPY", "10y"); sf = [x["fecha"] for x in spy]; sc = [x["c"] for x in spy]
def px(fs, cs, f):
    i = bisect.bisect_left(fs, f)
    return (cs[i], i) if i < len(fs) else (None, None)
def uno(t):
    try:
        c = cik.get(t.replace(".", "-"))
        if not c: return []
        time.sleep(0.3)
        s = B.datos_sec(c)
        if not s: return []
        v = gratis.yahoo_ohlcv(t.replace(".", "-"), "10y")
        fs = [x["fecha"] for x in v]; cs = [x["c"] for x in v]
        out = []
        for fin, pub, _ in s["eps"]:
            p0, i = px(fs, cs, pub)
            if not p0 or i + 250 >= len(cs): continue
            ev = B.evaluar(s, p0, pub)
            if not ev or ev["anios_eps"] < 5: continue
            s0, j = px(sf, sc, pub)
            if not s0 or j + 250 >= len(sc): continue
            r = cs[i + 250] / p0 - 1; rs = sc[j + 250] / s0 - 1
            out.append((t, pub, ev["cumple"], ev.get("margen_pct"), ev["criterios"], r, r - rs))
        return out
    except Exception:
        return []
with ThreadPoolExecutor(3) as ex:
    filas = [x for xs in ex.map(uno, uni) for x in xs]
print(f"::notice::{len(filas)} balances anuales de {len({f[0] for f in filas})} empresas ({min(f[1] for f in filas)[:4]}-{max(f[1] for f in filas)[:4]})")
def t(nom, xs):
    if len(xs) < 15: return f"{nom}: {len(xs)} casos (pocos)"
    r = np.array([x[5] for x in xs]); e = np.array([x[6] for x in xs])
    return f"{nom}: {len(xs)} casos · 12 meses mediana {np.median(r) * 100:+.1f}% · contra el S&P {np.median(e) * 100:+.1f}% (le gana {np.mean(e > 0) * 100:.0f}%) · peor 10% {np.percentile(r, 10) * 100:+.1f}%"
print("::notice::" + " | ".join([t("todas", filas), t("cumple 0-2", [f for f in filas if f[2] <= 2]), t("cumple 3-4", [f for f in filas if 3 <= f[2] <= 4]),
                                 t("cumple 5-7", [f for f in filas if f[2] >= 5])]))
print("::notice::" + " | ".join([t("con margen de seguridad (precio < número de Graham)", [f for f in filas if (f[3] or -1) > 0]),
                                 t("margen de 30%+", [f for f in filas if (f[3] or -1) >= 30]), t("sin margen", [f for f in filas if f[3] is not None and f[3] <= 0]),
                                 t("pierde plata / sin fórmula", [f for f in filas if f[3] is None])]))
for k in ("tamano", "solidez", "deuda", "estabilidad", "dividendos", "crecimiento", "precio"):
    si = [f for f in filas if f[4][k]]; no = [f for f in filas if not f[4][k]]
    print(f"::notice::criterio {k}: " + t("cumple", si) + " || " + t("no cumple", no))
