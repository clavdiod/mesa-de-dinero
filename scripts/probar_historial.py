"""Prueba la carga de historial de IOL para algunos papeles (2-4 consultas). No imprime secretos."""
from datetime import timedelta

from mesa.datos.consumo import Consumo
from mesa.datos.iol import IOL
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.nucleo.reloj import ahora

a = almacen_por_defecto()
consumo = Consumo(a)
iol = IOL(consumo, almacen=a)
hasta = ahora().date() - timedelta(days=1)
desde = hasta - timedelta(days=400)
out = []
for tk in ("PAMP", "AAPL", "TXAR"):
    try:
        v = iol.historial(tk, desde, hasta)
        out.append(f"{tk}: {len(v)} velas {v[0]['fecha'] if v else ''}..{v[-1]['fecha'] if v else ''}")
    except Exception as e:
        out.append(f"{tk}: ERROR {type(e).__name__}: {str(e)[:200]}")
idx = a.get("cache/indice") or {}
cargas = {k: a.get(k) for k in (f"cache/cargas/{ahora().date().isoformat()}",)}
consumo.guardar()
print("::notice::" + " | ".join(out) + f" | indice={len(idx)} {sorted(idx)[:40]} | cargas hoy={cargas}")
