from mesa.nucleo.almacen import almacen_por_defecto
e = almacen_por_defecto().get("ui/estado") or {}
s = e.get("seguimiento_cartera") or {}
print(f"::notice::ronda {e.get('hora')} · " + " | ".join(f"{tk}: {g.get('titular')} · sug={g.get('sugerida')}" for tk, g in s.items()))
