"""Lo que muestra la app del Ministro."""
import json

from mesa.nucleo.almacen import almacen_por_defecto

est = almacen_por_defecto().get("ui/estado") or {}
m = est.get("ministro") or {}
print("::notice::" + f"ronda {est.get('hora')} || " + json.dumps({k: m.get(k) for k in ("reglas", "titulares")}, ensure_ascii=False)[:2500]
      + " || activas " + json.dumps({k: v.get("activa") for k, v in (m.get("prueba") or {}).items()}))
