"""04/11: ¿qué señal de 'dio vuelta' rindió después de una caída? Acciones argentinas, 10 años, en dólares CCL.
Situación: cayó 15% o más desde su máximo de 60 ruedas (como TRAN y CEPU). Entrada: apertura del día siguiente. Comisión 1,2%."""
import bisect
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos import gratis
a = almacen_por_defecto()
panel = (a.get("ui/panel") or {}).get("titulos") or {}
tks = sorted(tk for tk, x in panel.items() if x and x[4] == "acciones")
ccl = gratis.ccl_historico(); fc = sorted(ccl)
def usd(f):
    i = bisect.bisect_right(fc, f) - 1
    return ccl[fc[i]] if i >= 0 else None
def ema(x, n):
    k = 2 / (n + 1); o = np.empty_like(x); o[0] = x[0]
    for i in range(1, len(x)):
        o[i] = x[i] * k + o[i - 1] * (1 - k)
    return o
with ThreadPoolExecutor(8) as ex:
    datos = dict(zip(tks, ex.map(lambda t: gratis.yahoo_ohlcv(t + ".BA", "10y"), tks)))
R = {k: [] for k in ("caida_todos", "macd_cruza_arriba", "macd_cruza_y_volumen", "supera_max_5r", "supera_media20", "cierra_arriba_media20_2dias", "rompe_linea_bajista", "sigue_cayendo")}
for tk, v in datos.items():
    v = [x for x in v or [] if x.get("cierre") and usd(x["fecha"])]
    if len(v) < 300:
        continue
    c = np.array([x["cierre"] / usd(x["fecha"]) for x in v]); o = np.array([(x.get("apertura") or x["cierre"]) / usd(x["fecha"]) for x in v])
    vol = np.array([x.get("volumen") or 0 for x in v], float)
    m = ema(c, 12) - ema(c, 26); h = m - ema(m, 9)
    for i in range(80, len(c) - 21):
        dd = c[i] / c[i - 59:i + 1].max() - 1
        if dd > -0.15:
            continue
        r = c[i + 20] / o[i + 1] - 1 - 0.012
        R["caida_todos"].append(r)
        m20 = c[i - 19:i + 1].mean(); m20a = c[i - 20:i].mean()
        cruza = h[i] > 0 >= h[i - 1]
        if cruza: R["macd_cruza_arriba"].append(r)
        if cruza and vol[i] >= 1.5 * np.median(vol[i - 20:i] + 1e-9): R["macd_cruza_y_volumen"].append(r)
        if c[i] > c[i - 5:i].max(): R["supera_max_5r"].append(r)
        if c[i] > m20 and c[i - 1] <= m20a: R["supera_media20"].append(r)
        if c[i] > m20 and c[i - 1] > m20a and c[i - 2] <= c[i - 21:i - 1].mean(): R["cierra_arriba_media20_2dias"].append(r)
        # línea bajista: dos últimos máximos de 5 ruedas descendentes de los últimos 60
        piv = [j for j in range(i - 60, i - 3) if c[j] == c[j - 5:j + 6].max()]
        if len(piv) >= 2 and c[piv[-1]] < c[piv[-2]]:
            j1, j2 = piv[-2], piv[-1]; lin = c[j2] + (c[j2] - c[j1]) / (j2 - j1) * (i - j2)
            lin_a = c[j2] + (c[j2] - c[j1]) / (j2 - j1) * (i - 1 - j2)
            if c[i] > lin and c[i - 1] <= lin_a: R["rompe_linea_bajista"].append(r)
        if c[i] < c[i - 5:i].min() and h[i] < 0: R["sigue_cayendo"].append(r)
for k, x in R.items():
    x = np.array(x) * 100
    if len(x) >= 20:
        print(f"::notice::{k}: {len(x)} casos · 20 ruedas neto {x.mean():+.2f}% (mediana {np.median(x):+.2f}%) · suben {np.mean(x > 0) * 100:.0f}% · caen 10%+ {np.mean(x < -10) * 100:.0f}%")
