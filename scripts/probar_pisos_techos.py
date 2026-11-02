"""¿Sirven los pisos y techos del gráfico? Para cada día: distancia al piso más cercano abajo (soporte con 2+ toques) y al techo
más cercano arriba (resistencia con 2+ toques), con los pivotes de los 250 días ANTERIORES. Se agrupa por
'espacio' = (techo - precio) / (precio - piso). Rendimiento a 20 ruedas, cuántas veces llega al techo y cuántas perfora el piso.
Además: cerca del máximo del año (top 10%) vs lejos; volumen alto vs normal en el día."""
import traceback
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from mesa.agentes import anticipadores as A
from mesa.agentes.grafico import _pivotes, _niveles
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.cierre import _universo_cedears
a = almacen_por_defecto()

def probar(nombre, ser):
    grupos = {}
    def add(k, r, llego, perforo):
        grupos.setdefault(k, []).append((r, llego, perforo))
    for tk, f in ser.items():
        c = np.array([x["c"] for x in f], dtype=float); o = np.array([x.get("o") or x["c"] for x in f], dtype=float)
        vol = np.array([x.get("v") or 0 for x in f], dtype=float)
        for i in range(260, len(c) - 21, 4):
            w = list(c[i - 250:i])
            hi, lo = _pivotes(w)
            p = c[i]
            sop = [d for d in _niveles([w[j] for j in lo], p, True) if d["toques"] >= 2]
            res = [d for d in _niveles([w[j] for j in hi], p, False) if d["toques"] >= 2]
            fut = c[i + 1:i + 21]; r = c[i + 20] / o[i + 1] - 1
            mx = max(w)
            add("todos", r, None, None)
            add("cerca del máximo del año (10%)" if p >= mx * 0.9 else "lejos del máximo del año", r, None, None)
            if vol[i - 20:i].mean() > 0:
                add("volumen 2x+ hoy" if vol[i] >= 2 * vol[i - 20:i].mean() else "volumen normal", r, None, None)
            sop = [d for d in sop if d["nivel"] < p]; res = [d for d in res if d["nivel"] > p]
            if sop and res:
                s_, t_ = max(d["nivel"] for d in sop), min(d["nivel"] for d in res)
                esp = (t_ - p) / (p - s_) if p > s_ else 99
                llego = bool((fut >= t_).any()); perf = bool((fut < s_ * 0.98).any())
                k = "espacio 3x+ (cerca del piso)" if esp >= 3 else "espacio 1-3x" if esp >= 1 else "espacio <1x (cerca del techo)"
                add(k, r, llego, perf)
                if p <= s_ * 1.03:
                    add("a menos de 3% de un piso", r, llego, perf)
                if p >= t_ * 0.97:
                    add("a menos de 3% de un techo", r, llego, perf)
    lin = []
    for k, v in sorted(grupos.items()):
        rr = np.array([x[0] for x in v]) * 100
        ll = [x[1] for x in v if x[1] is not None]; pp = [x[2] for x in v if x[2] is not None]
        lin.append(f"{k}: {len(v)} · {rr.mean():+.2f}% (med {np.median(rr):+.1f}%)" + (f" · llega al techo {np.mean(ll) * 100:.0f}% · perfora piso {np.mean(pp) * 100:.0f}%" if ll else ""))
    print(f"::notice::{nombre} | " + " | ".join(lin))
try:
    panel = (a.get("ui/panel") or {}).get("titulos") or {}
    acc, mer, rp, ccl = A.datos_arg(sorted(tk for tk, x in panel.items() if x and x[4] == "acciones"), 10)
    probar("ARG", acc)
except Exception:
    print("::notice::ARG ERR " + traceback.format_exc().replace(chr(10), " | ")[-400:])
try:
    raise SystemExit
    uni = _universo_cedears(a)
    with ThreadPoolExecutor(8) as ex:
        ced = {tk: f for tk, f in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "10y"), uni)) if len(f) > 400}
    probar("CEDEARs", ced)
except Exception:
    print("::notice::CED ERR " + traceback.format_exc().replace(chr(10), " | ")[-400:])
