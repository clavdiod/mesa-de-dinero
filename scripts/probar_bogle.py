"""20/11: ¿Bogle tiene razón con los CEDEARs? 10 años de Yahoo (gratis), cada 21 ruedas:
1) ¿Cuántas acciones sueltas le ganan al S&P 500 (SPY) a 1 año y a 5 años?
2) Vuelta al promedio: las que más subieron en 12 meses (10% de arriba), ¿cómo les va el año siguiente contra SPY?
   ¿Y las que más bajaron?
3) Costos: cuánto le resta operar seguido (con la comisión de 1,2% ida y vuelta).
Ojo: solo están las empresas que siguen cotizando hoy (las que quebraron no aparecen): esto favorece a las acciones sueltas."""
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos import gratis
from mesa.agentes.fundamentos import NO_EMPRESA
a = almacen_por_defecto()
pan = (a.get("ui/panel") or {}).get("titulos") or {}
uni = [t for t, x in pan.items() if x and len(x) > 4 and x[4] == "cedears" and t.isalpha() and not t.endswith(("D", "C")) and t not in NO_EMPRESA]
with ThreadPoolExecutor(8) as ex:
    ser = {t: {x["fecha"]: x["c"] for x in v} for t, v in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "10y"), uni)) if len(v) > 600}
spy = {x["fecha"]: x["c"] for x in gratis.yahoo_ohlcv("SPY", "10y")}
fs = sorted(spy); idx = {f: i for i, f in enumerate(fs)}
uno, cinco, top, fondo = [], [], [], []
for k in range(252, len(fs) - 252, 21):
    f0, f1, fa = fs[k], fs[k + 252], fs[k - 252]
    rs = spy[f1] / spy[f0] - 1
    trailing = []
    for t, s in ser.items():
        if f0 in s and f1 in s:
            ex_ = s[f1] / s[f0] - 1 - rs
            uno.append(ex_)
            if fa in s:
                trailing.append((s[f0] / s[fa] - 1, ex_))
        if k + 1260 < len(fs) and f0 in s and fs[k + 1260] in s:
            cinco.append(s[fs[k + 1260]] / s[f0] - spy[fs[k + 1260]] / spy[f0])
    if len(trailing) >= 30:
        trailing.sort(); n = len(trailing) // 10
        top += [e for _, e in trailing[-n:]]; fondo += [e for _, e in trailing[:n]]
uno, cinco, top, fondo = map(np.array, (uno, cinco, top, fondo))
print(f"::notice::{len(ser)} acciones con 10 años · 1) a 1 año le ganan al SPY {np.mean(uno > 0) * 100:.0f}% de las veces (diferencia mediana {np.median(uno) * 100:+.1f}%) · "
      f"a 5 años le ganan {np.mean(cinco > 0) * 100:.0f}% (mediana {np.median(cinco) * 100:+.0f}%)")
print(f"::notice::2) vuelta al promedio: las que más subieron en 12 meses, el año siguiente contra SPY: mediana {np.median(top) * 100:+.1f}%, le ganan {np.mean(top > 0) * 100:.0f}% · "
      f"las que más bajaron: mediana {np.median(fondo) * 100:+.1f}%, le ganan {np.mean(fondo > 0) * 100:.0f}%")
for ops in (4, 12, 24, 52):
    print(f"::notice::3) operar {ops} veces por año cuesta {ops * 1.2:.0f}% de comisiones al año (sin contar la diferencia entre puntas)")
sim = a.get("sim/resumen") or {}
print("::notice::SIMULACION de la mesa: " + str({k: sim.get(k) for k in list(sim)[:12]})[:600])
