"""¿Los anticipadores pueden anticipar subas más grandes a más plazo? 5/10/15/20 ruedas, mismos datos y mismo examen.
Neto = rendimiento promedio del top 10% al final del plazo menos 1,2% de comisión (ida y vuelta)."""
import json, traceback
from concurrent.futures import ThreadPoolExecutor
from mesa.agentes import anticipo, anticipadores as A
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.cierre import _universo_cedears
a = almacen_por_defecto()
HS = [(5, 5.0), (10, 8.0), (15, 10.0), (20, 12.0)]
res = {}
def correr(nombre, fn):
    for h, m in HS:
        try:
            r = fn(horizonte=h, meta=m)
            p = r.get("prueba") or {}
            neto = round(p.get("ret5_top10", 0) - 1.2, 2)
            res.setdefault(nombre, {})[f"{h}"] = {"activo": r.get("activo"), **p, "neto": neto}
            print(f"::notice::{nombre} {h} ruedas (+{m:.0f}%): activo={r.get('activo')} aciertos {p.get('top10_pct')} (azar {p.get('base_pct')}) "
                  f"ret {p.get('ret5_top10')}% (azar {p.get('ret5_base')}) caen {p.get('caen5_top10_pct')} (azar {p.get('caen5_base_pct')}) | neto {neto}% | neto por semana {round(neto / (h / 5), 2)}%")
        except Exception:
            print(f"::notice::{nombre} {h} ERROR " + traceback.format_exc().replace(chr(10), " | ")[-400:])
try:
    panel = (a.get("ui/panel") or {}).get("titulos") or {}
    tks = sorted(tk for tk, x in panel.items() if x and x[4] == "acciones")
    acc, mer, rp, ccl = A.datos_arg(tks, 10)
    correr("ARG", lambda **kw: A.entrenar_arg(acc, mer, rp, ccl, **kw))
except Exception:
    print("::notice::ARG ERROR " + traceback.format_exc().replace(chr(10), " | ")[-400:])
try:
    sp = {f: c for f, c in gratis.yahoo("SPY", "5y")}; vx = {f: c for f, c in gratis.yahoo("^VIX", "5y")}; bt = {f: c for f, c in gratis.yahoo("BTC-USD", "5y")}
    uni = _universo_cedears(a)
    with ThreadPoolExecutor(8) as ex:
        ced = {tk: f for tk, f in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "5y"), uni)) if len(f) > 300}
    correr("CEDEARs", lambda **kw: anticipo.entrenar(ced, sp, vx, bt, **kw))
except Exception:
    print("::notice::CED ERROR " + traceback.format_exc().replace(chr(10), " | ")[-400:])
a.put("pruebas/horizontes", res)
