"""Diagnóstico: muestra los campos crudos de un título de cauciones (2 consultas)."""
import json
from mesa.datos.consumo import Consumo
from mesa.datos.iol import IOL
from mesa.nucleo.almacen import almacen_por_defecto

a = almacen_por_defecto(); c = Consumo(a); iol = IOL(c, almacen=a)
raw = iol._get("/api/v2/Cotizaciones/Cauciones/Todas/argentina", "descubrimiento")
tit = raw.get("titulos", raw) if isinstance(raw, dict) else raw
print("::notice::CAUCION " + json.dumps(tit[:2], ensure_ascii=False)[:2500])
c.guardar()
