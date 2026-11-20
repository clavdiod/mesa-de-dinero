"""20/11: ¿la regla "rebote en dólares" sirve para TODAS las acciones argentinas, no solo YPFD? 10 años, en dólares CCL.
Señal: cae 30%+ desde el máximo de 3 meses y 15%+ en el último mes. Se compara entrar ya (A) contra esperar a que el MACD
se dé vuelta dentro de los 20 días siguientes (B, si no se da vuelta no se entra). Resultado a 3 meses con 1,2% de comisión.
Además: con alarma de venta 13% abajo, ¿cuántas veces salta antes de que rebote?"""
import numpy as np
from mesa.agentes import anticipadores as A
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto(); COM = 0.012
panel = (a.get("ui/panel") or {}).get("titulos") or {}
acc = A.datos_arg(sorted(tk for tk, x in panel.items() if x and x[4] == "acciones"), 10)[0]
def ema(x, n):
    k = 2 / (n + 1); o = np.empty(len(x)); o[0] = x[0]
    for i in range(1, len(x)): o[i] = x[i] * k + o[i - 1] * (1 - k)
    return o
A_, B_, base, salta, epis = [], [], [], [], set()
for tk, f in acc.items():
    c = np.array([x["c"] for x in f], float); fs = [x.get("fecha", "") for x in f]
    if len(c) < 300: continue
    h = (ema(c, 12) - ema(c, 26)); h = h - ema(h, 9)
    ult = -999
    for i in range(60, len(c) - 81):
        base.append(c[i + 60] / c[i] - 1 - COM) if i % 5 == 0 else None
        if i - ult < 20: continue
        if c[i] / c[i - 59:i + 1].max() - 1 <= -0.30 and c[i] / c[i - 20] - 1 <= -0.15:
            ult = i; epis.add((tk, fs[i][:7]))
            A_.append(c[i + 60] / c[i] - 1 - COM)
            salta.append(c[i + 1:i + 61].min() / c[i] - 1 <= -0.13)
            j = next((k for k in range(i + 1, i + 21) if h[k] > 0 >= h[k - 1]), None)
            if j: B_.append(c[j + 60] / c[j] - 1 - COM)
A_, B_, base = map(np.array, (A_, B_, base))
t = lambda x: f"{len(x)} casos · mediana {np.median(x) * 100:+.1f}% · promedio {x.mean() * 100:+.1f}% · suben {np.mean(x > 0) * 100:.0f}% · peor 10% {np.percentile(x, 10) * 100:+.1f}%"
print(f"::notice::REBOTE USD acciones argentinas ({len(acc)} papeles, {len({e[1] for e in epis})} meses distintos) | A entrar ya: {t(A_)} | "
      f"B esperar giro del MACD: {t(B_)} | cualquier momento: {t(base)} | alarma 13% abajo saltó antes en {np.mean(salta) * 100:.0f}% de los casos A")
