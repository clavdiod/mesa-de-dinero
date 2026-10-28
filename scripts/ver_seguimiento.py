from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
e = a.get("ui/estado") or {}
print(f"::notice::ronda {e.get('hora')}")
for tk, g in (e.get("seguimiento_cartera") or {}).items():
    p = (e.get("proyeccion_cartera") or {}).get(tk) or {}
    print(f"::notice::{tk}: {g.get('titular')} | sug {g.get('sugerida')} | {g.get('por_que')} | res {g.get('resultado_pct')} | precio {g.get('precio')} | "
          f"piso {g.get('piso')} obj {g.get('objetivo')} | consejo {p.get('consejo')}: {p.get('motivo')} | fuente {p.get('fuente_objetivo')} | max {p.get('max_desde_compra')} | rev {g.get('revision')}")
