"""Prueba con 5 años de las herramientas de Wall Street para anticipar ganadores (CEDEARs, en dólares)."""
import json
from concurrent.futures import ThreadPoolExecutor

from mesa.agentes import ganadores
from mesa.cierre import _universo_cedears
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto

a = almacen_por_defecto()
uni = _universo_cedears(a)
with ThreadPoolExecutor(8) as ex:
    series = {tk: f for tk, f in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "5y"), uni)) if len(f) > 300}
r = ganadores.entrenar(series)
a.put("ganadores/prueba", r)
lista = ganadores.lista_hoy(series)
a.put("ganadores/lista", {"fecha": lista[0]["fecha"] if lista else None, "lista": lista[:15]})
print("::notice::" + f"{len(series)} papeles || base {json.dumps(r['base'])} || " + " || ".join(
    f"{v['nombre']}: activa={v['activa']} plazo={v['plazo']} " + json.dumps(v["horizontes"]) for v in r["estrategias"].values())[:3800])
print("::notice::HOY " + " | ".join(f"{x['ticker']}: {', '.join(x['estrategias'])}" for x in lista[:15]))
