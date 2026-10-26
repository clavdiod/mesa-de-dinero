"""Control de "trampa con el futuro" (como lookahead-analysis de freqtrade): cada prueba se corre dos veces,
entrando al cierre del día de la señal (lo que se hacía) y entrando cuando de verdad se puede (apertura siguiente).
Si el resultado se cae mucho, la prueba vieja estaba inflada. No escribe nada: solo informa."""
import json
from concurrent.futures import ThreadPoolExecutor

from mesa.agentes import anticipo, ganadores, profesionales as pro
from mesa.cierre import _universo_cedears
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.nucleo.reloj import ahora

a = almacen_por_defecto()
uni = _universo_cedears(a)
with ThreadPoolExecutor(8) as ex:
    s5 = {tk: f for tk, f in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "5y"), uni)) if len(f) > 300}

def corto(d):
    return {k: {h: {x: v.get(x) for x in ("casos", "exceso", "acierto")} for h, v in (e.get("horizontes") or {}).items()} | {"activa": e.get("activa")}
            for k, e in d.items()}

g_v, g_r = ganadores.entrenar(s5, realista=False), ganadores.entrenar(s5, realista=True)
print("::notice::GANADORES viejo " + json.dumps(corto(g_v["estrategias"])) + " || REALISTA " + json.dumps(corto(g_r["estrategias"])))

spy = {f: c for f, c in gratis.yahoo("SPY", "5y")}
vix = {f: c for f, c in gratis.yahoo("^VIX", "5y")}
btc = {f: c for f, c in gratis.yahoo("BTC-USD", "5y")}
a_v = anticipo.entrenar(s5, spy, vix, btc, realista=False)
a_r = anticipo.entrenar(s5, spy, vix, btc, realista=True)
print("::notice::ANTICIPADOR viejo " + json.dumps({k: a_v.get(k) for k in ("activo", "prueba", "umbral")}) +
      " || REALISTA " + json.dumps({k: a_r.get(k) for k in ("activo", "prueba", "umbral")}))

p5 = {tk: [[x["fecha"], x["c"]] for x in f] for tk, f in s5.items()}
etfs = {e: gratis.yahoo(e, "5y") for e in pro.NOMBRE_SECTOR}
sect = {k: v for k, v in (a.get("profesionales/sectores") or {}).items() if v}
cons = (a.get("profesionales/consensos") or {}).get("datos") or {}
ins = (a.get("profesionales/insiders_hist") or {}).get("lista") or []
pro.REALISTA = False
p_v = pro.entrenar(p5, etfs, sect, cons, ins)
pro.REALISTA = True
p_r = pro.entrenar(p5, etfs, sect, cons, ins)
print("::notice::PROFESIONALES viejo " + json.dumps(corto(p_v["herramientas"])) + " || REALISTA " + json.dumps(corto(p_r["herramientas"])))
