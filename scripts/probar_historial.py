"""Muestra la forma cruda del historial sin ajustar de un CEDEAR (1 consulta). No imprime secretos."""
from datetime import timedelta
import json

from mesa.datos.consumo import Consumo
from mesa.datos.iol import IOL
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.nucleo.reloj import ahora

a = almacen_por_defecto()
consumo = Consumo(a)
iol = IOL(consumo, almacen=a)
hasta = ahora().date() - timedelta(days=1)
data = iol._get(f"/api/v2/bCBA/Titulos/AAPL/Cotizacion/seriehistorica/{(hasta - timedelta(days=6)).isoformat()}/{hasta.isoformat()}/sinAjustar", "historial")
consumo.guardar()
campos = ("fechaHora", "ultimoPrecio", "apertura", "maximo", "minimo", "volumenNominal", "montoOperado", "cantidadOperaciones", "cierreAnterior")
print("::notice::n=" + str(len(data)) + " " + json.dumps([{k: d.get(k) for k in campos} for d in data[:12]], ensure_ascii=False)[:3800])
