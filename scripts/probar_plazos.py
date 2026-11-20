"""20/11 (Clau: "qué tiempo aprox creen los analistas que sirve para tenerla y tener una ganancia"): para cada regla de
posiciones, cuánto tardó en llegar a +5% (ganancia que ya paga la comisión) y qué parte llegó en 1, 3, 6 y 12 meses."""
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from mesa.agentes import anticipadores as A
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos import gratis
from mesa.agentes.posiciones import APALANCADOS
from mesa.agentes.ficha_frio import COBERTURAS
a = almacen_por_defecto(); pan = (a.get("ui/panel") or {}).get("titulos") or {}
def plazos(nom, ser, regla):
    dias = []; n = 0
    for f in ser.values():
        c = np.array([x["c"] for x in f], float); v = np.array([x.get("v") or 0 for x in f], float)
        if len(c) < 300: continue
        ult = -999
        for i in range(60, len(c) - 253):
            if i - ult < 20 or not regla(c, v, i): continue
            ult = i; n += 1
            hit = np.nonzero(c[i + 1:i + 253] >= c[i] * 1.05)[0]
            dias.append(hit[0] + 1 if len(hit) else 999)
    d = np.array(dias)
    print(f"::notice::{nom}: {n} casos · llegó a +5% en 1 mes {np.mean(d <= 21) * 100:.0f}% · 3 meses {np.mean(d <= 63) * 100:.0f}% · 6 meses {np.mean(d <= 126) * 100:.0f}% · "
          f"12 meses {np.mean(d <= 252) * 100:.0f}% · mediana {int(np.median(d)) if np.median(d) < 999 else 'más de 1 año'} ruedas")
reb = lambda c, v, i: c[i] / c[i - 59:i + 1].max() - 1 <= -0.30 and c[i] / c[i - 20] - 1 <= -0.15
def pan_(c, v, i):
    vb = v[i - 60:i - 20].mean()
    return vb > 0 and v[i - 19:i + 1].mean() / vb >= 1.5 and c[i] / c[i - 20] - 1 <= -0.10
cualq = lambda c, v, i: i % 20 == 0
acc = A.datos_arg(sorted(tk for tk, x in pan.items() if x and x[4] == "acciones"), 10)[0]
plazos("Rebote en dólares (acciones argentinas)", acc, reb)
plazos("Pánico Kostolany (acciones argentinas USD)", acc, pan_)
plazos("Cualquier momento (acciones argentinas USD)", acc, cualq)
uni = [t for t, x in pan.items() if x and len(x) > 4 and x[4] == "cedears" and t.isalpha() and not t.endswith(("D", "C")) and t not in APALANCADOS | COBERTURAS][:250]
with ThreadPoolExecutor(8) as ex:
    ced = {t: v for t, v in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "10y"), uni)) if len(v) > 300}
plazos("Pánico Kostolany (CEDEARs)", ced, pan_)
plazos("Cualquier momento (CEDEARs)", ced, cualq)
