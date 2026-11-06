"""06/11: ¿qué anticipa un volumen anormal? 66 acciones argentinas, 10 años, en dólares CCL. Entrada: apertura del día siguiente.
Se mide a 5 y 20 ruedas, neto de 1,2% de comisión (ida y vuelta)."""
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
K = ["todos", "venta_fuerte_dia", "compra_fuerte_dia", "venta_sostenida_3d", "compra_sostenida_3d", "agotamiento_venta", "absorcion_volumen_sin_mover",
     "venta_fuerte_en_minimo_anual", "compra_fuerte_en_maximo_anual"]
R5 = {k: [] for k in K}; R20 = {k: [] for k in K}
for tk, v in datos.items():
    v = [x for x in v or [] if x.get("c") and x.get("v") and usd(x["fecha"])]
    if len(v) < 300:
        continue
    f = np.array([usd(x["fecha"]) for x in v])
    c = np.array([x["c"] for x in v]) / f; o = np.array([x["o"] for x in v]) / f
    h = np.array([x["h"] for x in v]) / f; l = np.array([x["l"] for x in v]) / f
    vol = np.array([x["v"] for x in v], float)
    for i in range(260, len(c) - 21):
        base = vol[i - 20:i].mean()
        if base <= 0:
            continue
        rel = vol[i] / base; var = c[i] / c[i - 1] - 1
        pos = (c[i] - l[i]) / (h[i] - l[i]) if h[i] > l[i] else 0.5
        r5 = c[i + 5] / o[i + 1] - 1 - 0.012; r20 = c[i + 20] / o[i + 1] - 1 - 0.012
        def add(k):
            R5[k].append(r5); R20[k].append(r20)
        add("todos")
        if rel >= 2.5 and var <= -0.02 and pos <= 0.3: add("venta_fuerte_dia")
        if rel >= 2.5 and var >= 0.02 and pos >= 0.7: add("compra_fuerte_dia")
        rels = [vol[j] / vol[j - 20:j].mean() for j in (i - 2, i - 1, i)]
        vars_ = [c[j] / c[j - 1] - 1 for j in (i - 2, i - 1, i)]
        if sum(1 for r_, x_ in zip(rels, vars_) if r_ >= 2 and x_ < 0) >= 2 and c[i] / c[i - 3] - 1 <= -0.04: add("venta_sostenida_3d")
        if sum(1 for r_, x_ in zip(rels, vars_) if r_ >= 2 and x_ > 0) >= 2 and c[i] / c[i - 3] - 1 >= 0.04: add("compra_sostenida_3d")
        r_ant = vol[i - 1] / vol[i - 21:i - 1].mean()
        if r_ant >= 3 and c[i - 1] / c[i - 2] - 1 <= -0.04 and rel < 1.2 and c[i] >= c[i - 1]: add("agotamiento_venta")
        if rel >= 3 and abs(var) < 0.01: add("absorcion_volumen_sin_mover")
        if rel >= 2.5 and var <= -0.02 and c[i] <= c[i - 252:i].min(): add("venta_fuerte_en_minimo_anual")
        if rel >= 2.5 and var >= 0.02 and c[i] >= c[i - 252:i].max(): add("compra_fuerte_en_maximo_anual")
print(f"::notice::{sum(1 for x in datos.values() if x)} acciones")
for k in K:
    x5, x20 = np.array(R5[k]) * 100, np.array(R20[k]) * 100
    if len(x20) >= 30:
        print(f"::notice::{k}: {len(x20)} casos · 5 ruedas {x5.mean():+.2f}% (suben {np.mean(x5 > 0) * 100:.0f}%) · 20 ruedas {x20.mean():+.2f}% mediana {np.median(x20):+.2f}% suben {np.mean(x20 > 0) * 100:.0f}% · caen 10%+ {np.mean(x20 < -10) * 100:.0f}%")
