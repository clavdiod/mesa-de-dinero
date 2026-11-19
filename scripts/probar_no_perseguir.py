"""19/11: ¿sirve 'no perseguir'? (pedido de Clau). Si un papel sube 2,5% o más en el día, la mesa pone el límite medio
movimiento diario (0,5 ATR) abajo. Con 10 años de velas diarias: señal al cierre de un día que subió 2,5% o más.
A) comprar al precio (apertura siguiente).  B) límite 0,5 ATR debajo del cierre, válido la rueda siguiente.
C) límite 0,25 ATR abajo. Todas con stop a 2 ATR (3% a 10%), objetivo 2 veces el riesgo, 20 ruedas y 1,2% de comisiones.
Se compara lo que rinde cada una POR SEÑAL (si el límite no entra, esa señal da 0)."""
import traceback
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from mesa.agentes import anticipadores as A
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.cierre import _universo_cedears
from mesa.agentes.control_frio import _sma
a = almacen_por_defecto(); COM = 0.012


def operar(h, l, c, i0, ent, riesgo):
    st_, ob = ent * (1 - riesgo), ent * (1 + 2 * riesgo)
    for j in range(i0, min(i0 + 20, len(c))):
        if l[j] <= st_: return -riesgo - COM
        if h[j] >= ob: return 2 * riesgo - COM
    return c[min(i0 + 19, len(c) - 1)] / ent - 1 - COM


def probar(nombre, ser):
    res = {k: [] for k in ("A", "B", "C")}; llenas = {"B": 0, "C": 0}; n_sen = 0; perdidas = []
    for f in ser.values():
        c = np.array([x["c"] for x in f], float); o = np.array([x.get("o") or x["c"] for x in f], float)
        h = np.array([x.get("h") or x["c"] for x in f], float); l = np.array([x.get("l") or x["c"] for x in f], float)
        if len(c) < 300 or (c <= 0).any(): continue
        tr = np.maximum(h - l, np.abs(np.r_[0, h[1:] - c[:-1]])); atr = _sma(tr, 14)
        for i in range(20, len(c) - 22):
            if c[i] / c[i - 1] - 1 < 0.025 or np.isnan(atr[i]): continue
            n_sen += 1; riesgo = float(np.clip(2 * atr[i] / c[i], 0.03, 0.10))
            ra = operar(h, l, c, i + 1, o[i + 1], riesgo); res["A"].append(ra)
            for k, m in (("B", 0.5), ("C", 0.25)):
                lim = c[i] - m * atr[i]
                if l[i + 1] <= lim:
                    llenas[k] += 1; ent = min(o[i + 1], lim)
                    res[k].append(operar(h, l, c, i + 1, ent, riesgo))
                else:
                    res[k].append(0.0)
                    if k == "B": perdidas.append(ra)
    if not n_sen:
        print(f"::notice::{nombre}: sin datos"); return
    r = {k: np.array(v) for k, v in res.items()}
    fb = [x for x, y in zip(res["B"], res["A"]) if x != 0.0]
    print(f"::notice::{nombre}: {n_sen} señales (subió 2,5% o más en el día) | "
          f"A comprar al precio: {r['A'].mean() * 100:+.2f}% por señal, gana {np.mean(r['A'] > 0) * 100:.0f}% | "
          f"B límite 0,5 ATR: entra {llenas['B'] / n_sen * 100:.0f}% de las veces, {r['B'].mean() * 100:+.2f}% por señal, cuando entra {np.mean(fb) * 100:+.2f}% | "
          f"C límite 0,25 ATR: entra {llenas['C'] / n_sen * 100:.0f}%, {r['C'].mean() * 100:+.2f}% por señal | "
          f"las que B se pierde (no entra) hubieran rendido {np.mean(perdidas) * 100:+.2f}% comprando al precio")


try:
    panel = (a.get("ui/panel") or {}).get("titulos") or {}
    probar("ARG", A.datos_arg(sorted(tk for tk, x in panel.items() if x and x[4] == "acciones"), 10)[0])
except Exception:
    print("::notice::ARG ERR " + traceback.format_exc().replace(chr(10), " | ")[-400:])
try:
    uni = _universo_cedears(a)
    with ThreadPoolExecutor(8) as ex:
        ced = {tk: f for tk, f in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "10y"), uni)) if len(f) > 300}
    probar("CEDEARs", ced)
except Exception:
    print("::notice::CED ERR " + traceback.format_exc().replace(chr(10), " | ")[-400:])
