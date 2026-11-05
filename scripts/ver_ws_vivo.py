from mesa.nucleo.almacen import almacen_por_defecto
e = almacen_por_defecto().get("ui/estado") or {}
w = e.get("ws_vivo") or {}
print(f"::notice::ronda {e.get('hora')} · {w.get('titulo')} · {len(w.get('lineas') or [])} líneas · NY {w.get('hora_ny')}")
