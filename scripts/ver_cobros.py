"""Lo que muestra la app en Tus cobros."""
from mesa.datos import cobros as c
from mesa.nucleo.almacen import almacen_por_defecto

est = almacen_por_defecto().get("ui/estado") or {}
cs = est.get("cobros") or []
print("::notice::" + f"ronda {est.get('hora')} · {len(cs)} cobros · flujos {sorted((est.get('flujos_bonos') or {}).keys())} || "
      + " | ".join(f"{x['fecha']} {c.texto(x)}" for x in cs[:25]))
