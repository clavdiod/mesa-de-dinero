"""Capacitación para tiempos volátiles: los 3 anticipadores (CEDEARs, ARG, Mundo). Guarda el bloque 'volatil' en cada modelo."""
import json, traceback
from concurrent.futures import ThreadPoolExecutor
from mesa.agentes import anticipo, anticipadores as A, volatil as V, profesionales as PRO
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.cierre import _universo_cedears
a = almacen_por_defecto()
res = {}
# ---- datos del mundo (5 años) ----
sp = {f: c for f, c in gratis.yahoo("SPY", "5y")}
vx = {f: c for f, c in gratis.yahoo("^VIX", "5y")}
bt = {f: c for f, c in gratis.yahoo("BTC-USD", "5y")}
uni = _universo_cedears(a)
with ThreadPoolExecutor(8) as ex:
    ced = {tk: f for tk, f in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "5y"), uni)) if len(f) > 300}
dm, um = V.dias_mundo(sp, vx)
print(f"::notice::Mundo: {len(ced)} CEDEARs; {len(dm)} días volátiles de {len(sp)} (umbral vol S&P {um:.2f})")
# ---- Anticipador (CEDEARs) ----
try:
    mod = a.get("anticipo/modelo") or {}
    v = V.capacitar(lambda **kw: anticipo.entrenar(ced, sp, vx, bt, **kw), dm, um, "Anticipador")
    mod["volatil"] = v; a.put("anticipo/modelo", mod); res["anticipador"] = v
    print("::notice::" + v["texto"])
except Exception:
    print("::notice::anticipador ERROR " + traceback.format_exc().replace(chr(10), " | ")[-500:])
# ---- Anticipador Mundo ----
try:
    mm = a.get("anticipo_mundo/modelo") or {}
    g5 = {k: {f: c for f, c in gratis.yahoo(sym, "5y")} for k, sym in A.GLOBALES.items()}
    e5 = {e: {f: c for f, c in gratis.yahoo(e, "5y")} for e in PRO.NOMBRE_SECTOR}
    sect = {k: x for k, x in (a.get("profesionales/sectores") or {}).items() if x}
    v = V.capacitar(lambda **kw: A.entrenar_mundo(ced, sp, vx, bt, g5, sect, e5, **kw), dm, um, "Anticipador Mundo")
    mm["volatil"] = v; a.put("anticipo_mundo/modelo", mm); res["anticipador_mundo"] = v
    print("::notice::" + v["texto"])
except Exception:
    print("::notice::mundo ERROR " + traceback.format_exc().replace(chr(10), " | ")[-500:])
# ---- Anticipador ARG (10 años en dólares) ----
try:
    ma = a.get("anticipo_arg/modelo") or {}
    panel = (a.get("ui/panel") or {}).get("titulos") or {}
    tks = sorted(tk for tk, x in panel.items() if x and x[4] == "acciones")
    acc, mer, rp, ccl = A.datos_arg(tks, 10)
    da, ua = V.dias_arg(mer, rp)
    print(f"::notice::ARG: {len(acc)} acciones; {len(da)} días volátiles de {len(mer)} (umbral vol Merval USD {ua:.2f})")
    v = V.capacitar(lambda **kw: A.entrenar_arg(acc, mer, rp, ccl, **kw), da, ua, "Anticipador ARG")
    ma["volatil"] = v; a.put("anticipo_arg/modelo", ma); res["anticipador_arg"] = v
    print("::notice::" + v["texto"])
except Exception:
    print("::notice::arg ERROR " + traceback.format_exc().replace(chr(10), " | ")[-500:])
from datetime import date
a.put("capacitacion/volatil", {"fecha": date.today().isoformat(),
                               "agentes": {k: {kk: x.get(kk) for kk in ("texto", "general", "especialista", "usar_especialista", "bueno", "peso", "dias")} for k, x in res.items()}})
