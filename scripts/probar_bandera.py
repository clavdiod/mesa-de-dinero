"""Ruptura de una corrección dentro de una tendencia alcista (setup del platino, 19/10):
venía subiendo (arriba de su promedio de 200), corrigió 8-20% desde su máximo de 60 ruedas, y HOY cierra arriba de su máximo de 10 ruedas
(rompe la directriz de la corrección). Entrada apertura siguiente, 20 y 40 ruedas. Y qué hizo PPLT desde el 19/10."""
import traceback
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from mesa.agentes import anticipadores as A
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.cierre import _universo_cedears
a = almacen_por_defecto()

def probar(nombre, ser):
    base, setup, sin_ruptura = [], [], []
    for tk, f in ser.items():
        c = np.array([x["c"] for x in f], dtype=float); o = np.array([x.get("o") or x["c"] for x in f], dtype=float)
        ult = -99
        for i in range(220, len(c) - 41):
            r20, r40 = c[i + 20] / o[i + 1] - 1, c[i + 40] / o[i + 1] - 1
            if i % 5 == 0:
                base.append((r20, r40))
            mx60 = c[i - 60:i].max(); corr = c[i - 10:i].min() / mx60 - 1
            if c[i - 1] > c[i - 200:i].mean() * 0 and c[i - 30:i].mean() > c[i - 200:i].mean() and -0.20 <= corr <= -0.08:
                if c[i] > c[i - 10:i].max() and i - ult > 20:
                    setup.append((r20, r40)); ult = i
                elif i % 5 == 0:
                    sin_ruptura.append((r20, r40))
    def r(v):
        v = np.array(v) * 100
        return f"{len(v)} casos, 20 ruedas {v[:, 0].mean():+.2f}% (suben 8%+ {np.mean(v[:, 0] >= 8) * 100:.0f}%, caen 8%+ {np.mean(v[:, 0] <= -8) * 100:.0f}%), 40 ruedas {v[:, 1].mean():+.2f}%"
    print(f"::notice::{nombre} | cualquier día: {r(base)} | RUPTURA de corrección en tendencia alcista: {r(setup)} | corrigiendo sin romper todavía: {r(sin_ruptura)}")
try:
    f = gratis.yahoo_ohlcv("PPLT", "3mo")
    print("::notice::PPLT: " + " | ".join(f"{x['fecha'][5:]} {x['c']:.2f}" for x in f if x["fecha"] >= "2026-10-13"))
    uni = sorted(set(_universo_cedears(a)) | {"GLD", "SLV", "PPLT", "GDX", "SPY", "QQQ", "IWM", "XLE", "EWZ", "USO", "COPX"})
    with ThreadPoolExecutor(8) as ex:
        ced = {tk: s for tk, s in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "10y"), uni)) if len(s) > 400}
    probar("CEDEARs y ETFs (10 años)", ced)
    probar("Metales (GLD, SLV, PPLT, GDX, COPX)", {k: v for k, v in ced.items() if k in ("GLD", "SLV", "PPLT", "GDX", "COPX")})
    panel = (a.get("ui/panel") or {}).get("titulos") or {}
    acc, mer, rp, ccl = A.datos_arg(sorted(tk for tk, x in panel.items() if x and x[4] == "acciones"), 10)
    probar("Acciones ARG (USD)", acc)
except Exception:
    print("::notice::ERR " + traceback.format_exc().replace(chr(10), " | ")[-500:])
