"""04/11: busca velas imposibles en el historial guardado (máximo o cierre 3 veces arriba de sus vecinas) y las corrige."""
import numpy as np
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
tks = sorted({c["ticker"] for c in a.get("usuario/cartera") or []} | set(a.get("cache/indice") or {}))
arreglos = []
for tk in tks:
    v = a.get(f"cache/diario/{tk}") or []
    if len(v) < 10:
        continue
    cambio = False
    for i, x in enumerate(v):
        vec = [y["cierre"] for y in v[max(0, i - 5):i] + v[i + 1:i + 6] if y.get("cierre")]
        if not vec:
            continue
        m = float(np.median(vec))
        for k in ("maximo", "cierre", "apertura", "minimo"):
            val = x.get(k)
            if val and (val > 3 * m or val < m / 3):
                arreglos.append(f"{tk} {x.get('fecha')} {k} {val}→{round(m, 2)}")
                x[k] = round(m, 2); cambio = True
    if cambio:
        a.put(f"cache/diario/{tk}", v)
print(f"::notice::{len(arreglos)} velas corregidas: " + " | ".join(arreglos[:60]))
