"""Busca qué papel sugerido anda cerca de un precio (para cuando el usuario dice 'esta a 32400')."""
import json, traceback
from mesa.nucleo.almacen import almacen_por_defecto
P = 32400
a = almacen_por_defecto()
e = a.get("ui/estado") or {}
try:
    print(f"::notice::ronda {e.get('fecha')} {e.get('hora')}")
    fuentes = {"anticipador": e.get("anticipo_lista") or {}, **(e.get("anticipo_listas") or {}), **(e.get("anticipo_listas_obs") or {})}
    for k in ("ganadores/lista", "profesionales/lista"):
        fuentes[k] = a.get(k) or {}
    for ag, l in fuentes.items():
        for x in [y for y in (l.get("lista") or []) if isinstance(y, dict)]:
            pr = (x.get("plan") or {}).get("precio") or x.get("precio") or ((x.get("precios_usd") or {}) if False else None)
            print(f"::notice::{ag} {x.get('ticker')} precio {pr} prob {x.get('prob')} prio {x.get('prioridad')}") if pr and 0.85 * P <= float(pr) <= 1.15 * P else None
    panel = (a.get("ui/panel") or {}).get("titulos") or {}
    cerca = sorted((tk for tk, x in panel.items() if x and isinstance(x[0], (int, float)) and 0.97 * P <= float(x[0]) <= 1.03 * P), key=lambda t: abs(float(panel[t][0]) - P))
    print("::notice::PANEL cerca de 32400: " + ", ".join(f"{t} {panel[t][0]} ({panel[t][4]})" for t in cerca[:15]))
    print("::notice::COMITE " + json.dumps([(c.get("ticker"), c.get("aprobada")) for c in (e.get("comite") or {}).get("acta", [])][:12]))
except Exception:
    print("::notice::ERR " + traceback.format_exc().replace(chr(10), " | ")[-700:])
