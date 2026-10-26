import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
est = a.get("ui/estado") or {}
mu = est.get("mundo") or {}
print(f"::notice::{est.get('hora')} temas: " + " | ".join(f"{t.get('id') or t.get('tema')}: {t.get('nombre')} n={t.get('n')} base={t.get('base')} " + "; ".join(x.get('titulo', '')[:80] for x in (t.get('titulares') or [])[:2]) for t in (mu.get("temas") or []))[:3500])
sen = [s for s in (est.get("senales") or []) if s.get("agente") == "mundo"]
print("::notice::senales mundo: " + " | ".join(f"{s['ticker']} {s.get('direccion')} {s.get('texto','')[:80]}" for s in sen[:15]))
