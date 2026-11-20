"""20/11: Greenblatt (fórmula mágica) y Buffett (Hagstrom), con lo publicado en la SEC hasta cada fecha, a 12 meses contra el S&P."""
import bisect, time
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.cierre import _universo_cedears
from mesa.agentes import biblioteca as B
from mesa.agentes.fundamentos import _ciks, NO_EMPRESA
from mesa.datos import gratis
a = almacen_por_defecto(); pan = (a.get("ui/panel") or {}).get("titulos") or {}
uni = list(dict.fromkeys([t for t in _universo_cedears(a) if t not in NO_EMPRESA] + [t for t, x in pan.items() if x and len(x) > 4 and x[4] == "cedears" and t.isalpha() and not t.endswith(("D", "C")) and t not in NO_EMPRESA]))[:160]
cik = _ciks(); spy = gratis.yahoo_ohlcv("SPY", "max"); sf = [x["fecha"] for x in spy]; sc = [x["c"] for x in spy]
def px(fs, cs, f):
    i = bisect.bisect_left(fs, f); return (cs[i], i) if i < len(fs) else (None, None)
def uno(t):
    try:
        c = cik.get(t.replace(".", "-"))
        if not c: return []
        time.sleep(0.3); s = B.datos_sec(c)
        if not s: return []
        v = gratis.yahoo_ohlcv(t.replace(".", "-"), "max"); fs = [x["fecha"] for x in v]; cs = [x["c"] for x in v]
        out = []
        for fin, pub, _ in s["ganancia"]:
            p0, i = px(fs, cs, pub); s0, j = px(sf, sc, pub)
            if not p0 or not s0 or i + 250 >= len(cs) or j + 250 >= len(sc): continue
            q = B.evaluar_calidad(s, p0, pub, t)
            if q: out.append((t, pub, q, cs[i + 250] / p0 - 1 - (sc[j + 250] / s0 - 1)))
        return out
    except Exception:
        return []
with ThreadPoolExecutor(3) as ex:
    F = [x for xs in ex.map(uno, uni) for x in xs]
def t(nom, xs):
    if len(xs) < 25: return f"{nom}: {len(xs)} (pocos)"
    e = np.array([x[3] for x in xs]); return f"{nom}: {len(xs)} · contra el S&P mediana {np.median(e) * 100:+.1f}% · le gana {np.mean(e > 0) * 100:.0f}% · peor 10% {np.percentile(e, 10) * 100:+.0f}%"
print(f"::notice::{len(F)} balances de {len({f[0] for f in F})} empresas · " + t("todas", F))
print("::notice::GREENBLATT " + " | ".join([t("fórmula mágica (rinde 8%+ y retorno sobre capital 25%+)", [f for f in F if B.es_formula_magica(f[2])]),
      t("rinde 8%+ sola", [f for f in F if (f[2]["ey"] or 0) >= 8]), t("retorno sobre capital 25%+ solo", [f for f in F if (f[2]["roc"] or 0) >= 25]),
      t("ninguna", [f for f in F if not ((f[2]["ey"] or 0) >= 8 or (f[2]["roc"] or 0) >= 25)])]))
print("::notice::BUFFETT " + " | ".join([t("ROE 15%+ los 3 años y poca deuda", [f for f in F if B.es_buffett(f[2])]),
      t("ROE 15%+ los 3 años", [f for f in F if (f[2]["roe_min"] or 0) >= 15]), t("ROE bajo o irregular", [f for f in F if f[2]["roe_min"] is not None and f[2]["roe_min"] < 15]),
      t("Buffett + fórmula mágica", [f for f in F if B.es_buffett(f[2]) and B.es_formula_magica(f[2])])]))
