"""06/11: compra fuerte (volumen anormal comprador): ¿en qué situación anticipa? 66 acciones argentinas, 10 años, en dólares, neto 1,2%."""
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
with ThreadPoolExecutor(8) as ex:
    datos = dict(zip(tks, ex.map(lambda t: gratis.yahoo_ohlcv(t + ".BA", "10y"), tks)))
K = ["todos", "compra_fuerte", "cf_rel4", "cf_2dias", "cf_lejos_del_max", "cf_cerca_min_anual", "cf_tendencia_alcista", "cf_tendencia_bajista",
     "cf_tras_caida_20", "cf_lejos_max_y_rel4", "cf_monto_alto", "cf_merval_no_sube"]
R = {k: [] for k in K}
# Merval aproximado: promedio de retornos diarios del universo
for tk, v in datos.items():
    v = [x for x in v or [] if x.get("c") and x.get("v") and usd(x["fecha"])]
    if len(v) < 300:
        continue
    f = np.array([usd(x["fecha"]) for x in v])
    c = np.array([x["c"] for x in v]) / f; o = np.array([x["o"] for x in v]) / f
    h = np.array([x["h"] for x in v]) / f; l = np.array([x["l"] for x in v]) / f
    vol = np.array([x["v"] for x in v], float); monto = vol * np.array([x["c"] for x in v])
    for i in range(260, len(c) - 21):
        base = vol[i - 20:i].mean()
        if base <= 0:
            continue
        rel = vol[i] / base; var = c[i] / c[i - 1] - 1
        pos = (c[i] - l[i]) / (h[i] - l[i]) if h[i] > l[i] else 0.5
        r20 = c[i + 20] / o[i + 1] - 1 - 0.012
        R["todos"].append(r20)
        if not (rel >= 2.5 and var >= 0.02 and pos >= 0.7):
            continue
        mx, mn = c[i - 252:i].max(), c[i - 252:i].min()
        s50, s200 = c[i - 50:i].mean(), c[i - 200:i].mean()
        R["compra_fuerte"].append(r20)
        if rel >= 4: R["cf_rel4"].append(r20)
        prev = vol[i - 1] / vol[i - 21:i - 1].mean()
        if prev >= 2 and c[i - 1] > c[i - 2]: R["cf_2dias"].append(r20)
        if c[i] < 0.85 * mx: R["cf_lejos_del_max"].append(r20)
        if (c[i] - mn) / (mx - mn + 1e-9) <= 0.3: R["cf_cerca_min_anual"].append(r20)
        if c[i] > s50 > s200: R["cf_tendencia_alcista"].append(r20)
        if c[i] < s50 < s200: R["cf_tendencia_bajista"].append(r20)
        if c[i - 1] / c[i - 60:i].max() - 1 <= -0.20: R["cf_tras_caida_20"].append(r20)
        if c[i] < 0.85 * mx and rel >= 4: R["cf_lejos_max_y_rel4"].append(r20)
        if monto[i] >= np.percentile(monto[i - 250:i], 90) and rel >= 3: R["cf_monto_alto"].append(r20)
for k in K:
    x = np.array(R[k]) * 100
    if len(x) >= 30:
        print(f"::notice::{k}: {len(x)} casos · 20 ruedas {x.mean():+.2f}% mediana {np.median(x):+.2f}% · suben {np.mean(x > 0) * 100:.0f}% · suben 10%+ {np.mean(x > 10) * 100:.0f}% · caen 10%+ {np.mean(x < -10) * 100:.0f}%")
