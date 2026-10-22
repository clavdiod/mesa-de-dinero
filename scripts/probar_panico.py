"""¿Comprar la capitulación de un CEDEAR rinde más si se espera la confirmación del rebote?"""
import statistics as st

from mesa.cierre import _datos_ws
from mesa.nucleo.almacen import almacen_por_defecto

d = _datos_ws(almacen_por_defecto(), None, "5y")
res = {}
for tk, serie in d["precios"].items():
    x = [c for _, c in serie]
    ultimo = -99
    for i in range(230, len(x) - 20):
        r10 = (x[i] / x[i - 10] - 1) * 100
        if r10 > -15 or x[i - 20] <= sum(x[i - 220:i - 20]) / 200 or i - ultimo < 15:
            continue
        variantes = {
            "sin_confirmar": True,
            "rebote_1d": x[i] > x[i - 1],
            "rebote_2d": x[i] > x[i - 1] > x[i - 2],
            "sobre_min3": x[i] > min(x[i - 3:i]) * 1.03,
            "cae_menos_que_sp": True,
        }
        for k, ok in variantes.items():
            if ok:
                for h in (10, 20):
                    res.setdefault((k, h), []).append((x[i + h] / x[i] - 1) * 100)
        ultimo = i
out = []
for (k, h), v in sorted(res.items()):
    out.append(f"{k}@{h}: n={len(v)} acierto {sum(1 for r in v if r > 0) / len(v) * 100:.0f}% prom {st.mean(v):+.2f}% mediana {st.median(v):+.2f}%")
print("::notice::" + " | ".join(out))
