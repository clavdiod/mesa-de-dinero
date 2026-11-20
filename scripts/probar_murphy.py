"""20/11: reglas de Murphy (Análisis técnico de los mercados financieros) que la mesa no había probado. 10 años, a 3 meses,
con 1,2% de comisión. Acciones argentinas (en dólares) y CEDEARs (datos de EE.UU.)."""
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
def ema(x, n):
    k = 2 / (n + 1); o = np.empty(len(x)); o[0] = x[0]
    for i in range(1, len(x)): o[i] = x[i] * k + o[i - 1] * (1 - k)
    return o
def rsi(c):
    d = np.diff(c); u = ema(np.maximum(d, 0), 27); dn = ema(np.maximum(-d, 0), 27)
    return np.r_[50, 100 - 100 / (1 + u / np.where(dn == 0, 1e-12, dn))]
def probar(nom, ser):
    G = {}
    add = lambda k, r: G.setdefault(k, []).append(r)
    for f in ser.values():
        c = np.array([x["c"] for x in f], float); v = np.array([x.get("v") or 0 for x in f], float)
        if len(c) < 400: continue
        m50, m200, R = sma(c, 50), sma(c, 200), rsi(c)
        for i in range(260, len(c) - 64):
            fw = c[i + 63] / c[i] - 1 - COM
            if i % 5 == 0:
                add("cualquier momento", fw)
                add("arriba del promedio de 200" if c[i] > m200[i] else "abajo del promedio de 200", fw)
            if m50[i] > m200[i] and m50[i - 1] <= m200[i - 1]: add("cruce dorado (50 pasa arriba del 200)", fw)
            if m50[i] < m200[i] and m50[i - 1] >= m200[i - 1]: add("cruce de la muerte (50 baja del 200)", fw)
            vb = v[i - 60:i].mean()
            if c[i] >= c[i - 252:i].max() and c[i - 1] < c[i - 253:i - 1].max() and vb > 0 and v[i] >= 1.5 * vb:
                add("quiebre del máximo del año con volumen", fw)
            if c[i] >= c[i - 252:i].max() and c[i - 1] < c[i - 253:i - 1].max() and vb > 0 and v[i] < vb:
                add("quiebre del máximo del año SIN volumen", fw)
            if R[i] < 30 and R[i - 1] >= 30:
                add("RSI baja de 30 con tendencia alcista (arriba del 200)" if c[i] > m200[i] else "RSI baja de 30 con tendencia bajista", fw)
            if R[i] < 40 and i >= 30:
                j = i - 5 - int(np.argmin(c[i - 30:i - 5]))
                if c[i] < c[j] and R[i] > R[j] + 5 and c[i] == c[i - 5:i + 1].min():
                    add("divergencia alcista (precio hace mínimo más bajo, RSI no)", fw)
    out = []
    for k, xs in sorted(G.items()):
        x = np.array(xs)
        if len(x) >= 30:
            out.append(f"{k}: {len(x)} · 3 meses mediana {np.median(x) * 100:+.1f}% · suben {np.mean(x > 0) * 100:.0f}% · peor 10% {np.percentile(x, 10) * 100:+.0f}%")
    print(f"::notice::{nom} | " + " | ".join(out))
acc = A.datos_arg(sorted(tk for tk, x in pan.items() if x and x[4] == "acciones"), 10)[0]
probar("ACCIONES ARGENTINAS (USD)", acc)
uni = [t for t, x in pan.items() if x and len(x) > 4 and x[4] == "cedears" and t.isalpha() and not t.endswith(("D", "C")) and t not in APALANCADOS | COBERTURAS][:250]
with ThreadPoolExecutor(8) as ex:
    ced = {t: v for t, v in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "10y"), uni)) if len(v) > 400}
probar("CEDEARs", ced)
