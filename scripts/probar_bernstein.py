"""20/11: Bernstein (The Intelligent Asset Allocator): repartir entre acciones y bonos y REBALANCEAR una vez por año, contra
dejarlo quieto. SPY (acciones EE.UU.) e IEF (bonos del Tesoro 7-10 años), 2003-2026, con dividendos (precio ajustado)."""
import numpy as np
from mesa.datos import gratis
spy = {x["fecha"]: x["c"] for x in gratis.yahoo_ohlcv("SPY", "max")}; ief = {x["fecha"]: x["c"] for x in gratis.yahoo_ohlcv("IEF", "max")}
fs = sorted(set(spy) & set(ief))
def corrida(w, rebal):
    a, b = w, 1 - w; va = [a + b]; pico, peor = 1, 0; ult = fs[0][:4]
    for i in range(1, len(fs)):
        a *= spy[fs[i]] / spy[fs[i - 1]]; b *= ief[fs[i]] / ief[fs[i - 1]]; v = a + b
        if rebal and fs[i][:4] != ult:
            a, b = v * w, v * (1 - w)
        ult = fs[i][:4]; pico = max(pico, v); peor = min(peor, v / pico - 1); va.append(v)
    anios = len(fs) / 252
    return v ** (1 / anios) - 1, peor
for w in (1.0, 0.8, 0.6, 0.4):
    r1, d1 = corrida(w, True); r0, d0 = corrida(w, False)
    print(f"::notice::{int(w * 100)}% acciones / {int(100 - w * 100)}% bonos ({fs[0][:4]}-{fs[-1][:4]}): rebalanceando cada año rinde {r1 * 100:.1f}% anual, peor caída {d1 * 100:.0f}% · sin tocar {r0 * 100:.1f}% anual, peor caída {d0 * 100:.0f}%")
