"""Prueba: panel de opciones con precios (IOL Cotizaciones/Opciones)."""
import json
from mesa.datos.consumo import Consumo
from mesa.datos.iol import IOL
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
iol = IOL(Consumo(a), almacen=a)
try:
    print("::notice::paneles " + json.dumps(iol.paneles_disponibles("Opciones"), ensure_ascii=False)[:600])
except Exception as ex:
    print(f"::notice::paneles ERR {ex}")
for pan in ("Todas", "Opciones", "Merval"):
    try:
        d = iol._get(f"/api/v2/Cotizaciones/Opciones/{pan}/argentina", "opciones")
        t = d.get("titulos", d) if isinstance(d, dict) else d
        con = [x for x in t if (x.get("ultimoPrecio") or 0) > 0]
        print(f"::notice::panel {pan}: {len(t)} filas, {len(con)} con precio | ej: " + json.dumps(con[:1] or t[:1], ensure_ascii=False)[:1200])
        break
    except Exception as ex:
        print(f"::notice::panel {pan} ERR {ex}")
