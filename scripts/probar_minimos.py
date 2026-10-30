"""Ruptura de soporte: cierre debajo del mínimo de las 250 ruedas anteriores (mínimo anual nuevo).
¿Qué pasa en las 20 ruedas siguientes? Y si dentro de 10 ruedas vuelve arriba de ese mínimo (ruptura falsa), ¿qué pasa después?
CEDEARs + ETFs (GLD, SLV, SPY...) 10 años y acciones ARG 10 años en USD. Entrada a la apertura siguiente."""
import traceback
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from mesa.agentes import anticipadores as A
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.cierre import _universo_cedears
a = almacen_por_defecto()

def probar(nombre, series):
    base, rot, falsa, sigue = [], [], [], []
    for tk, f in series.items():
        c = np.array([x["c"] for x in f], dtype=float); o = np.array([x.get("o") or x["c"] for x in f], dtype=float)
        ult = -99
        for i in range(260, len(c) - 31):
            if i % 5 == 0:
                base.append(c[i + 20] / o[i + 1] - 1)
            sop = c[i - 250:i].min()
            if c[i] < sop and c[i - 1] >= sop and i - ult > 20:
                ult = i
                rot.append(c[i + 20] / o[i + 1] - 1)
                j = next((k for k in range(i + 1, i + 11) if c[k] > sop), None)
                if j is not None:
                    falsa.append(c[j + 20] / o[j + 1] - 1)
                else:
                    sigue.append(c[i + 30] / o[i + 11] - 1)
    def r(v):
        v = np.array(v) * 100
        return f"{len(v)} casos {v.mean():+.2f}% (mediana {np.median(v):+.2f}%), suben 5%+ {np.mean(v >= 5) * 100:.0f}%, caen 5%+ {np.mean(v <= -5) * 100:.0f}%"
    print(f"::notice::{nombre} | cualquier día: {r(base)} | mínimo anual nuevo: {r(rot)} | ruptura falsa (vuelve arriba en ≤10 ruedas, se compra ahí): {r(falsa)} | sigue abajo 10 ruedas (se compra ahí): {r(sigue)}")
try:
    uni = sorted(set(_universo_cedears(a)) | {"GLD", "SLV", "SPY", "QQQ", "IWM", "XLE", "EWZ", "GDX", "USO"})
    with ThreadPoolExecutor(8) as ex:
        ced = {tk: f for tk, f in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "10y"), uni)) if len(f) > 600}
    probar("CEDEARs y ETFs (10 años)", ced)
    probar("Solo metales y ETFs", {k: v for k, v in ced.items() if k in ("GLD", "SLV", "GDX", "SPY", "QQQ", "IWM", "XLE", "EWZ", "USO")})
except Exception:
    print("::notice::CED ERR " + traceback.format_exc().replace(chr(10), " | ")[-400:])
try:
    panel = (a.get("ui/panel") or {}).get("titulos") or {}
    acc, mer, rp, ccl = A.datos_arg(sorted(tk for tk, x in panel.items() if x and x[4] == "acciones"), 10)
    probar("Acciones ARG (USD)", acc)
except Exception:
    print("::notice::ARG ERR " + traceback.format_exc().replace(chr(10), " | ")[-400:])
