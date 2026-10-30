import traceback
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
try:
    e = a.get("ui/estado") or {}
    print(f"::notice::ronda {e.get('hora')}")
    for tk, g in (e.get("seguimiento_cartera") or {}).items():
        p = (e.get("proyeccion_cartera") or {}).get(tk) or {}
        print(f"::notice::{tk}: {g.get('titular')} | sug {g.get('sugerida')} | {g.get('por_que')} | res {g.get('resultado_pct')} | precio {g.get('precio')} | "
              f"piso {g.get('piso')} obj {g.get('objetivo')} | consejo {p.get('consejo')} | fuente {p.get('fuente_objetivo')} | max {p.get('max_desde_compra')} | "
              f"mesa {p.get('mesa')} f{p.get('favor')} c{p.get('contra')} | rango {p.get('rango_1m')} | rev {g.get('revision')} | cambios {g.get('cambios')}")
    for tk, p in (e.get("proyeccion_cartera") or {}).items():
        if p.get("grupo") in ("soberanos", "ons", "letras", "bonos", "provinciales") or tk in ("PR17", "BAO27"):
            print(f"::notice::RF {tk}: {p.get('consejo')} | {p.get('motivo')} | {p.get('proyeccion')} | precio {p.get('precio')} res {p.get('resultado_pct')}")
    print("::notice::cobros " + str([(c.get('fecha'), c.get('ticker'), c.get('total'), c.get('moneda')) for c in (e.get('cobros') or [])][:8]))
except Exception:
    print("::notice::ERR " + traceback.format_exc().replace(chr(10), " | ")[-700:])
