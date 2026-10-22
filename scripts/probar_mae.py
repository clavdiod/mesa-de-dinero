"""Resúmenes de resultados de licitaciones."""
from mesa.nucleo.almacen import almacen_por_defecto

av = (almacen_por_defecto().get("eventos/licitaciones") or {}).get("avisos") or {}
print("::notice::" + " ||| ".join(f"{x['titulo'][:45]} => {x.get('resumen') or '-'}" for x in av.get("resultados") or [])[:3900])
print("::notice::" + " ||| ".join(f"{x['titulo'][:45]} => {x.get('resumen') or '-'}" for x in av.get("anuncios") or [])[:3900])
