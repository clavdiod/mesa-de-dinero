"""25/11: estado del Vigía por agente (solo lectura; nada de la cartera)."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
v = (almacen_por_defecto().get("ui/estado") or {}).get("vigia") or {}
print(f"::notice::vigia {v.get('fecha')} {v.get('hora')} mudos={v.get('mudos')}")
for k, x in sorted((v.get("agentes") or {}).items()):
    print(f"::notice::{k} " + json.dumps(x))
