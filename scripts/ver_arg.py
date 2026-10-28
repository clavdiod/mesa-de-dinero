import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
for k in ("anticipo_arg/lista", "anticipo_mundo/lista"):
    l = a.get(k) or {}
    print(f"::notice::{k} fecha {l.get('fecha')} activo {l.get('activo')} " + " | ".join(f"{x['ticker']} {x['prob']}" for x in l.get("lista") or []))
