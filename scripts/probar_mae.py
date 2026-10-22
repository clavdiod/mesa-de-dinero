"""¿Por qué no hay resultados en los avisos?"""
from mesa.datos.eventos import _yaml  # noqa
from mesa.nucleo.almacen import almacen_por_defecto

lic = almacen_por_defecto().get("eventos/licitaciones") or {}
av = lic.get("avisos") or {}
print("::notice::" + f"claves {list(av)} anuncios {len(av.get('anuncios') or [])} resultados {len(av.get('resultados') or [])} || "
      + " | ".join(f"{x['titulo'][:40]} res={bool(x.get('resumen'))}" for x in av.get("resultados") or []))
