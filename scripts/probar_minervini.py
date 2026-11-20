"""20/11: Mark Minervini (Think & Trade Like a Champion): ¿la "plantilla de tendencia" (etapa 2) sirve? 10 años, a 3 meses,
con 1,2% de comisión. Plantilla: precio arriba de sus promedios de 150 y 200; el de 200 subiendo hace un mes; 50 > 150 > 200;
precio 30%+ arriba del mínimo del año y a menos de 25% del máximo; fuerza relativa entre el 30% mejor del universo.
Además: su regla de cortar la pérdida en 7-8% contra no cortar."""
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from mesa.agentes import anticipadores as A
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos import gratis
from mesa.agentes.posiciones import APALANCADOS
from mesa.agentes.ficha_frio import COBERTURAS
a = almacen_por_defecto(); pan = (a.get("ui/panel") or {}).get("titulos") or {}; COM = 0.012
def sma(x, n):
    cs = np.cumsum(np.r_[0, x]); o = np.full(len(x), np.nan); o[n - 1:] = (cs[n:] - cs[:-n]) / n; return o
def probar(nom, ser):
    S = {t: (np.array([x["fecha"] for x in f]), np.array([x["c"] for x in f], float), np.array([x.get("l") or x["c"] for x in f], float)) for t, f in ser.items() if len(f) > 400}
    # fuerza relativa: rendimiento de 12 meses, rankeado entre todos los papeles en cada fecha
    r12 = {}
    for t, (fs, c, l) in S.items():
        for i in range(252, len(c)):
            r12.setdefault(fs[i], []).append(c[i] / c[i - 252] - 1)
    corte = {f: np.percentile(v, 70) for f, v in r12.items() if len(v) >= 20}
    G = {"plantilla (etapa 2)": [], "plantilla + corte 8%": [], "cualquier momento": []}
    for t, (fs, c, l) in S.items():
        m50, m150, m200 = sma(c, 50), sma(c, 150), sma(c, 200)
        for i in range(260, len(c) - 64, 3):
            fw = c[i + 63] / c[i] - 1 - COM
            G["cualquier momento"].append(fw)
            lo, hi = c[i - 251:i + 1].min(), c[i - 251:i + 1].max()
            ok = (c[i] > m150[i] and c[i] > m200[i] and m200[i] > m200[i - 21] and m50[i] > m150[i] > m200[i]
                  and c[i] >= lo * 1.30 and c[i] >= hi * 0.75 and fs[i] in corte and c[i] / c[i - 252] - 1 >= corte[fs[i]])
            if ok:
                G["plantilla (etapa 2)"].append(fw)
                st = np.nonzero(l[i + 1:i + 64] <= c[i] * 0.92)[0]
                G["plantilla + corte 8%"].append(-0.08 - COM if len(st) else fw)
    print(f"::notice::{nom} | " + " | ".join(f"{k}: {len(v)} · 3 meses mediana {np.median(v) * 100:+.1f}% · promedio {np.mean(v) * 100:+.1f}% · suben {np.mean(np.array(v) > 0) * 100:.0f}% · peor 10% {np.percentile(v, 10) * 100:+.0f}%" for k, v in G.items() if len(v) > 30))
acc = A.datos_arg(sorted(tk for tk, x in pan.items() if x and x[4] == "acciones"), 10)[0]
probar("ACCIONES ARGENTINAS (USD)", acc)
uni = [t for t, x in pan.items() if x and len(x) > 4 and x[4] == "cedears" and t.isalpha() and not t.endswith(("D", "C")) and t not in APALANCADOS | COBERTURAS][:250]
with ThreadPoolExecutor(8) as ex:
    ced = {t: v for t, v in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "10y"), uni)) if len(v) > 400}
probar("CEDEARs", ced)
