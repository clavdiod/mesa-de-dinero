"""20/11: ¿lo de Lynch funciona con los CEDEARs? Igual que Graham: con lo publicado en la SEC hasta cada fecha, el día
después de cada balance anual, rendimiento de los 12 meses siguientes contra el S&P 500."""
import bisect, time
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.cierre import _universo_cedears
from mesa.agentes import biblioteca as B
from mesa.agentes.fundamentos import _ciks, NO_EMPRESA
from mesa.datos import gratis
a = almacen_por_defecto()
pan = (a.get("ui/panel") or {}).get("titulos") or {}
uni = list(dict.fromkeys([t for t in _universo_cedears(a) if t not in NO_EMPRESA] + [t for t, x in pan.items() if x and len(x) > 4 and x[4] == "cedears" and t.isalpha() and not t.endswith(("D", "C")) and t not in NO_EMPRESA]))[:160]
cik = _ciks()
spy = gratis.yahoo_ohlcv("SPY", "max"); sf = [x["fecha"] for x in spy]; sc = [x["c"] for x in spy]
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
        v = gratis.yahoo_ohlcv(t.replace(".", "-"), "max"); fs = [x["fecha"] for x in v]; cs = [x["c"] for x in v]
        out = []
        for fin, pub, _ in s["ganancia"]:
            p0, i = px(fs, cs, pub)
            if not p0 or i + 250 >= len(cs): continue
            ev = B.evaluar_lynch(s, p0, pub)
            s0, j = px(sf, sc, pub)
            if not ev or not s0 or j + 250 >= len(sc): continue
            out.append((t, pub, ev, cs[i + 250] / p0 - 1 - (sc[j + 250] / s0 - 1)))
        return out
    except Exception:
        return []
with ThreadPoolExecutor(3) as ex:
    F = [x for xs in ex.map(uno, uni) for x in xs]
print(f"::notice::{len(F)} balances de {len({f[0] for f in F})} empresas ({min(f[1] for f in F)[:4]}-{max(f[1] for f in F)[:4]})")
def t(nom, xs):
    if len(xs) < 25: return f"{nom}: {len(xs)} (pocos)"
    e = np.array([x[3] for x in xs])
    return f"{nom}: {len(xs)} · contra el S&P mediana {np.median(e) * 100:+.1f}% · le gana {np.mean(e > 0) * 100:.0f}% · peor 10% {np.percentile(e, 10) * 100:+.0f}%"
g = lambda f: [x for x in F if f(x[2])]
print("::notice::TODAS " + t("todas", F))
print("::notice::PEG " + " | ".join([t("PEG<0,5", g(lambda e: e["peg"] is not None and e["peg"] < 0.5)), t("0,5-1", g(lambda e: e["peg"] is not None and 0.5 <= e["peg"] < 1)),
                                    t("1-2", g(lambda e: e["peg"] is not None and 1 <= e["peg"] < 2)), t(">2", g(lambda e: e["peg"] is not None and e["peg"] >= 2)), t("sin PEG (no crece o pierde)", g(lambda e: e["peg"] is None))]))
print("::notice::DEUDA " + " | ".join([t("deuda/patrimonio <0,33", g(lambda e: e["deuda_patrimonio"] is not None and e["deuda_patrimonio"] < 0.33)), t("0,33-1", g(lambda e: e["deuda_patrimonio"] is not None and 0.33 <= e["deuda_patrimonio"] <= 1)),
                                      t(">1", g(lambda e: e["deuda_patrimonio"] is not None and e["deuda_patrimonio"] > 1)), t("caja neta >10% del precio", g(lambda e: (e["caja_neta_pct"] or 0) > 10))]))
print("::notice::RECOMPRA " + " | ".join([t("recompra 2%+", g(lambda e: e["recompra"])), t("emite 2%+", g(lambda e: (e["acciones_1a_pct"] or 0) >= 2)), t("igual", g(lambda e: not e["recompra"] and (e["acciones_1a_pct"] or 0) < 2))]))
print("::notice::CATEGORIAS " + " | ".join(t(c, g(lambda e, c=c: e["categoria"] == c)) for c in ("rapida", "robusta", "lenta", "ciclica", "recuperacion")))
cic = g(lambda e: e["categoria"] == "ciclica")
print("::notice::CICLICAS " + " | ".join([t("cíclica P/E bajo (<10)", [x for x in cic if x[2]["pe"] and x[2]["pe"] < 10]), t("cíclica P/E alto (>20) o pérdida", [x for x in cic if not x[2]["pe"] or x[2]["pe"] > 20])]))
print("::notice::COMBO " + t("rápida o robusta + PEG<1 + poca deuda", g(lambda e: e["categoria"] in ("rapida", "robusta") and e["peg"] is not None and e["peg"] < 1 and (e["deuda_patrimonio"] or 0) < 0.33)))
