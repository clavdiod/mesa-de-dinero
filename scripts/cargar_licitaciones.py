"""Carga ya las licitaciones del MAE (la mesa igual las actualiza sola cada mañana)."""
from mesa.datos.eventos import actualizar_licitaciones
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.nucleo.reloj import ahora

a = almacen_por_defecto()
r = actualizar_licitaciones(a, ahora().date(), ahora().strftime("%H:%M"), forzar=True)
print("::notice::" + f"{len(r.get('eventos') or [])} licitaciones, {len(r.get('noticias') or [])} titulares || "
      + " || ".join(n["titulo"] for n in r.get("noticias") or [])[:3000])
