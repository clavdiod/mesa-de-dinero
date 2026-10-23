"""Prueba con la historia de las herramientas profesionales (analistas, insiders, sectores) y lista de hoy."""
import json
from concurrent.futures import ThreadPoolExecutor

from mesa.agentes import profesionales as pro
from mesa.cierre import _universo_cedears
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.nucleo.reloj import ahora

a = almacen_por_defecto()
hoy = ahora().date()
uni = _universo_cedears(a)
with ThreadPoolExecutor(8) as ex:
    s5 = {tk: f for tk, f in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "5y"), uni)) if len(f) > 300}
r = pro.entrenar_todo(a, {tk: [[x["fecha"], x["c"]] for x in f] for tk, f in s5.items()}, hoy)
print("::notice::" + f"{len(s5)} papeles, datos {r['datos']} || " + " || ".join(
    f"{k}: activa={v['activa']} plazo={v['plazo']} " + json.dumps(v["horizontes"]) for k, v in r["herramientas"].items())[:3800])
pl = pro.armar_lista(a, list(s5), {tk: f[-1]["c"] for tk, f in s5.items()}, hoy)
print("::notice::LIDERES " + json.dumps(pl["lideres"]) + " " + json.dumps(pl["sectores_3m"]))
print("::notice::HOY " + " | ".join(f"{tk}: " + "; ".join(f"{k}={m[:90]}" for k, m in ev.items()) for tk, ev in list(pl["lista"].items())[:25])[:3800])

import runpy
runpy.run_path("scripts/cargar_estado.py")
