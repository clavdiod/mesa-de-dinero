"""¿Se pueden anticipar saltos grandes? Comprar al cierre de hoy (CI) y vender en 1-2 ruedas. Acciones ARG (10 años, USD) y CEDEARs (5 años).
Neto = rendimiento promedio al cierre del plazo del top 10% marcado, menos 1,2% de comisión. Solo papeles con volumen (los que se pueden vender)."""
import json, traceback
from concurrent.futures import ThreadPoolExecutor
from mesa.agentes import anticipo, anticipadores as A
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.cierre import _universo_cedears
a = almacen_por_defecto()
CASOS = [(1, 5.0), (1, 8.0), (2, 8.0), (2, 10.0), (3, 10.0)]
def correr(nombre, fn):
    for h, m in CASOS:
        try:
            r = fn(horizonte=h, meta=m, realista=False)
            p = r.get("prueba") or {}
            print(f"::notice::{nombre} {h}d +{m:.0f}%: activo={r.get('activo')} top10 {p.get('top10_pct')} top5 {p.get('top5_pct')} (azar {p.get('base_pct')}) "
                  f"ret {p.get('ret5_top10')}% (azar {p.get('ret5_base')}) caen {p.get('caen5_top10_pct')} (azar {p.get('caen5_base_pct')}) neto {round((p.get('ret5_top10') or 0) - 1.2, 2)} | {str(r.get('importancia'))[:160]}")
        except Exception:
            print(f"::notice::{nombre} {h} ERR " + traceback.format_exc().replace(chr(10), " | ")[-300:])
def liquidas(ser, minimo):
    return {tk: f for tk, f in ser.items() if len(f) > 300 and sorted(x["v"] * x["c"] for x in f[-250:])[125] >= minimo}
try:
    panel = (a.get("ui/panel") or {}).get("titulos") or {}
    tks = sorted(tk for tk, x in panel.items() if x and x[4] == "acciones")
    acc, mer, rp, ccl = A.datos_arg(tks, 10)
    liq = liquidas(acc, 20000)  # mediana de 20.000 USD por día operados
    print(f"::notice::ARG {len(acc)} acciones, líquidas {len(liq)}: " + ", ".join(sorted(liq)))
    correr("ARG", lambda **kw: A.entrenar_arg(liq, mer, rp, ccl, **kw))
except Exception:
    print("::notice::ARG ERR " + traceback.format_exc().replace(chr(10), " | ")[-400:])
try:
    sp = {f: c for f, c in gratis.yahoo("SPY", "5y")}; vx = {f: c for f, c in gratis.yahoo("^VIX", "5y")}; bt = {f: c for f, c in gratis.yahoo("BTC-USD", "5y")}
    uni = _universo_cedears(a)
    with ThreadPoolExecutor(8) as ex:
        ced = {tk: f for tk, f in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "5y"), uni)) if len(f) > 300}
    correr("CEDEARs", lambda **kw: anticipo.entrenar(ced, sp, vx, bt, **kw))
except Exception:
    print("::notice::CED ERR " + traceback.format_exc().replace(chr(10), " | ")[-400:])
