"""Estructura (análisis tipo Edu Páez): ¿máximos y mínimos descendentes + debajo de un promedio de 20 que baja predicen peores 20 ruedas?
Estados: CAYENDO (máx y mín descendentes y debajo de un promedio 20 que baja), CONFIRMADO (arriba del promedio 20 que dejó de bajar),
ALCISTA (máx y mín ascendentes). Rendimiento a 20 ruedas desde la apertura siguiente."""
import traceback
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from mesa.agentes import anticipadores as A
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.cierre import _universo_cedears
a = almacen_por_defecto()

def pivotes(c, n=5):
    hi = [i for i in range(n, len(c) - n) if c[i] == max(c[i - n:i + n + 1])]
    lo = [i for i in range(n, len(c) - n) if c[i] == min(c[i - n:i + n + 1])]
    return hi, lo

def estado(c, i):
    w = c[max(0, i - 120):i + 1]
    hi, lo = pivotes(w)
    hi, lo = [h for h in hi if h < len(w) - 5], [l for l in lo if l < len(w) - 5]  # solo pivotes ya confirmados
    m20, ant = np.mean(c[i - 19:i + 1]), np.mean(c[i - 24:i - 4])
    baj = len(hi) >= 2 and len(lo) >= 2 and w[hi[-1]] < w[hi[-2]] and w[lo[-1]] < w[lo[-2]]
    alc = len(hi) >= 2 and len(lo) >= 2 and w[hi[-1]] > w[hi[-2]] and w[lo[-1]] > w[lo[-2]]
    if baj and c[i] < m20 and m20 < ant:
        return "CAYENDO"
    if c[i] > m20 and m20 >= ant:
        return "ALCISTA" if alc else "CONFIRMADO"
    return "OTRO"

def probar(nombre, series):
    res = {}
    for tk, f in series.items():
        c = np.array([x["c"] for x in f], dtype=float); o = np.array([x.get("o") or x["c"] for x in f], dtype=float)
        for i in range(130, len(c) - 21, 3):
            r = c[i + 20] / o[i + 1] - 1
            mitad = "1ra mitad" if i < len(c) / 2 else "2da mitad"
            for k in (estado(c, i), estado(c, i) + " " + mitad):
                res.setdefault(k, []).append(r)
    todos = np.concatenate([np.array(v) for k, v in res.items() if " " not in k]) * 100
    print(f"::notice::{nombre} todos: {len(todos)} casos, {todos.mean():+.2f}% a 20 ruedas, suben 5%+: {np.mean(todos >= 5) * 100:.0f}%, caen 10%+: {np.mean(todos <= -10) * 100:.0f}%")
    print(f"::notice::{nombre} | " + " | ".join(f"{k}: {len(res[k])} {np.mean(res[k]) * 100:+.2f}% s5 {np.mean(np.array(res[k]) >= .05) * 100:.0f}% c10 {np.mean(np.array(res[k]) <= -.10) * 100:.0f}%" for k in sorted(res)))
try:
    panel = (a.get("ui/panel") or {}).get("titulos") or {}
    tks = sorted(tk for tk, x in panel.items() if x and x[4] == "acciones")
    pass
except Exception:
    print("::notice::ARG ERR " + traceback.format_exc().replace(chr(10), " | ")[-400:])
try:
    uni = _universo_cedears(a)
    with ThreadPoolExecutor(8) as ex:
        ced = {tk: f for tk, f in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "5y"), uni)) if len(f) > 300}
    probar("CEDEARs", ced)
except Exception:
    print("::notice::CED ERR " + traceback.format_exc().replace(chr(10), " | ")[-400:])
