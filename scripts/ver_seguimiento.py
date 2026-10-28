from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
e = a.get("ui/estado") or {}
print(f"::notice::ronda {e.get('hora')}")
for tk, g in (e.get("seguimiento_cartera") or {}).items():
    print(f"::notice::{tk}: {g.get('titular')} | {g.get('por_que')} | res {g.get('resultado_pct')} | obj {g.get('objetivo')}")
