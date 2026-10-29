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
    d = (a.get("ui/debates") or {}).get("IREN") or {}
    for lado in ("favor", "contra"):
        print(f"::notice::IREN {lado.upper()} " + " || ".join(f"{s.get('agente')} ({s.get('fuerza')}): {s.get('texto')}" for s in (d.get(lado) or []))[:1500])
except Exception:
    print("::notice::ERR " + traceback.format_exc().replace(chr(10), " | ")[-700:])
