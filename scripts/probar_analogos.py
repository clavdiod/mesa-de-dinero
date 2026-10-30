"""Patrones parecidos (análogos) con biblioteca de TODOS los gráficos. Examen honesto: para cada fecha del examen (último 30%),
solo se buscan parecidos que terminaron ANTES de esa fecha. Forma = 20 ruedas normalizadas (en USD para ARG).
Predicción = promedio de lo que hicieron los 30 más parecidos en las 20 ruedas siguientes. Se mide el top 10% vs todos."""
import json, traceback
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from mesa.agentes import anticipadores as A
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.cierre import _universo_cedears
a = almacen_por_defecto()
V, H, K, PASO = 20, 20, 30, 5

def probar(nombre, series, meta):
    fechas_todas = sorted({x["fecha"] for f in series.values() for x in f})
    corte = fechas_todas[int(len(fechas_todas) * 0.7)]
    lib_X, lib_y, lib_fin, filas = [], [], [], []
    for tk, f in series.items():
        c = np.array([x["c"] for x in f], dtype=float)
        if len(c) < V + H + 10 or (c <= 0).any():
            continue
        for i in range(V, len(c) - H, PASO):
            w = c[i - V:i]
            z = (w - w.mean()) / (w.std() or 1)
            fut = c[i + H - 1] / c[i - 1] - 1
            mx = c[i:i + H].max() / c[i - 1] - 1
            fin = f[i - 1]["fecha"]; fin_fut = f[i + H - 1]["fecha"]
            lib_X.append(z); lib_y.append((fut, mx)); lib_fin.append(fin_fut)
            if fin >= corte:
                filas.append((fin, z, fut, mx))
    X = np.array(lib_X); Y = np.array(lib_y); FIN = np.array(lib_fin)
    filas = filas[::3] if len(filas) > 6000 else filas
    preds = []
    for fin, z, fut, mx in filas:
        ok = FIN < fin  # solo parecidos cuyo futuro ya se conocía ese día
        if ok.sum() < 500:
            continue
        corr = (X[ok] @ z) / V
        idx = np.argpartition(-corr, K)[:K]
        preds.append((float(Y[ok][idx, 0].mean()), float((Y[ok][idx, 1] >= meta).mean()), float(corr[idx].mean()), fut, mx))
    preds.sort(key=lambda r: -r[0])
    n10 = max(20, len(preds) // 10)
    top = preds[:n10]; bot = preds[-n10:]
    base_ret = np.mean([p[3] for p in preds]) * 100; base_hit = np.mean([p[4] >= meta for p in preds]) * 100
    top_ret = np.mean([p[3] for p in top]) * 100; top_hit = np.mean([p[4] >= meta for p in top]) * 100
    bot_ret = np.mean([p[3] for p in bot]) * 100
    corr_pred = np.corrcoef([p[0] for p in preds], [p[3] for p in preds])[0, 1]
    print(f"::notice::{nombre}: {len(preds)} casos de examen (desde {corte}), biblioteca {len(X)} gráficos | "
          f"top10% de lo que predicen los parecidos: {top_ret:+.2f}% a 20 ruedas, {top_hit:.0f}% tocan +{meta*100:.0f}% | "
          f"todos: {base_ret:+.2f}%, {base_hit:.0f}% | peor 10%: {bot_ret:+.2f}% | correlación predicción-realidad {corr_pred:.3f} | "
          f"parecido promedio {np.mean([p[2] for p in preds]):.2f}")
try:
    panel = (a.get("ui/panel") or {}).get("titulos") or {}
    tks = sorted(tk for tk, x in panel.items() if x and x[4] == "acciones")
    acc, mer, rp, ccl = A.datos_arg(tks, 10)
    probar("Acciones ARG (USD, 10 años)", acc, 0.12)
except Exception:
    print("::notice::ARG ERR " + traceback.format_exc().replace(chr(10), " | ")[-400:])
try:
    uni = _universo_cedears(a)
    with ThreadPoolExecutor(8) as ex:
        ced = {tk: f for tk, f in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "5y"), uni)) if len(f) > 300}
    probar("CEDEARs (5 años)", ced, 0.08)
except Exception:
    print("::notice::CED ERR " + traceback.format_exc().replace(chr(10), " | ")[-400:])
