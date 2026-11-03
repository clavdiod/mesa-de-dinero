"""Prueba: cadena de opciones de GGAL desde la conexión de la mesa (2 consultas). Muestra los campos crudos."""
import json
from mesa.datos.consumo import Consumo
from mesa.datos.iol import IOL
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
iol = IOL(Consumo(a), almacen=a)
for tk in ("GGAL", "YPFD"):
    try:
        x = iol.opciones(tk)
        print(f"::notice::{tk}: {len(x)} opciones | ejemplo: " + json.dumps(x[:2], ensure_ascii=False)[:1500])
    except Exception as ex:
        print(f"::notice::{tk}: ERR {ex}")
