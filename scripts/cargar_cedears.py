"""Carga historial gratis (EE.UU. × CCL) para los CEDEARs más operados y re-entrena la calibración.
Usa 1-2 consultas de IOL (el panel de CEDEARs) para saber cuáles se operan más."""
from mesa.cierre import entrenar
from mesa.datos.cache import CacheHistorico
from mesa.datos.consumo import Consumo
from mesa.datos.iol import IOL
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.ronda import cargar_paneles

a = almacen_por_defecto()
consumo = Consumo(a)
iol = IOL(consumo, almacen=a)
paneles = cargar_paneles(iol, consumo, a, False)
simb = {t.get("simbolo") for t in paneles.get("cedears", [])}
ced = [t for t in paneles.get("cedears", []) if t.get("simbolo") and t.get("monto") and t.get("ultimo")
       and not (t["simbolo"][-1:] in ("D", "C") and t["simbolo"][:-1] in simb)]
ced.sort(key=lambda t: t["monto"], reverse=True)
cache = CacheHistorico(a)
from mesa.datos import gratis
prueba = ced[0] if ced else None
diag = f"cedears_panel={len(paneles.get('cedears', []))} candidatos={len(ced)} primeros={[t['simbolo'] for t in ced[:6]]}"
if prueba:
    us = gratis.precios_eeuu(prueba["simbolo"])
    diag += f" | prueba {prueba['simbolo']}: eeuu={len(us)} ccl={len(gratis.ccl_historico())} hist={len(gratis.historial_cedear(prueba['simbolo'], prueba['ultimo']))}"
print("::notice::" + diag)
ok = []
for t in ced[:40]:
    if cache.asegurar_cedear(t["simbolo"], t["ultimo"]):
        ok.append(t["simbolo"])
cache.guardar()
consumo.guardar()
r = entrenar()
print(f"::notice::CEDEARs con historial nuevo: {len(ok)} {ok} | {str(r)[:2500]}")
