"""19/11: ¿hay un momento en que comprar VXX (cobertura) paga? Pedido de Clau tras la suba de VXX del 12 al 19/11.
VXX y el VIX de Yahoo (gratis, 10 años, ajustado por agrupamientos). Para cada día: rinde de VXX a 5, 10 y 20 ruedas
y una operación con objetivo +20% / stop -10% en 20 ruedas, menos 1,2% de comisiones. Se comparan momentos."""
import numpy as np
from mesa.datos import gratis
vx = gratis.yahoo_ohlcv("VXX", "10y"); vi = {x["fecha"]: x["c"] for x in gratis.yahoo_ohlcv("^VIX", "10y")}
spy = {x["fecha"]: x["c"] for x in gratis.yahoo_ohlcv("SPY", "10y")}
f = [x for x in vx if x["fecha"] in vi and x["fecha"] in spy]
c = np.array([x["c"] for x in f]); h = np.array([x.get("h") or x["c"] for x in f]); l = np.array([x.get("l") or x["c"] for x in f])
v = np.array([vi[x["fecha"]] for x in f]); s = np.array([spy[x["fecha"]] for x in f]); n = len(c)
print(f"::notice::{n} días · VXX de {f[0]['fecha']} a {f[-1]['fecha']} · VIX hoy {v[-1]:.1f}")
COM = 0.012
def oper(i):
    for j in range(i + 1, min(i + 21, n)):
        if l[j] <= c[i] * 0.90: return -0.10 - COM
        if h[j] >= c[i] * 1.20: return 0.20 - COM
    return c[min(i + 20, n - 1)] / c[i] - 1 - COM
grupos = {}
def add(k, i):
    grupos.setdefault(k, []).append(i)
for i in range(252, n - 21):
    pct = (v[i - 251:i + 1] < v[i]).mean()
    add("todos los días", i)
    if v[i] < 13: add("VIX < 13", i)
    if v[i] < 15: add("VIX < 15", i)
    if pct <= 0.10: add("VIX en el 10% más bajo del año", i)
    if pct <= 0.20: add("VIX en el 20% más bajo del año", i)
    if pct <= 0.20 and s[i] >= s[i - 251:i + 1].max() * 0.98: add("VIX bajo + S&P en máximos (exceso de confianza)", i)
    if pct <= 0.30 and v[i] / v[i - 1] - 1 >= 0.10: add("VIX bajo que salta 10%+ en el día (primer susto)", i)
    if v[i] >= 25: add("VIX >= 25 (ya hay miedo: tarde)", i)
    if c[i] / c[i - 5] - 1 >= 0.15: add("VXX ya subió 15%+ en 5 ruedas (persiguiendo)", i)
for k, idx in grupos.items():
    idx = np.array(idx)
    r = {d: c[idx + d] / c[idx] - 1 - COM for d in (5, 10, 20)}
    op = np.array([oper(i) for i in idx])
    print(f"::notice::{k}: {len(idx)} días | 5r {np.mean(r[5]) * 100:+.1f}% (gana {np.mean(r[5] > 0) * 100:.0f}%) | 10r {np.mean(r[10]) * 100:+.1f}% | "
          f"20r {np.mean(r[20]) * 100:+.1f}% (gana {np.mean(r[20] > 0) * 100:.0f}%) | operación +20/-10: {op.mean() * 100:+.1f}% gana {np.mean(op > 0) * 100:.0f}% · años distintos {len({f[i]['fecha'][:4] for i in idx})}")
