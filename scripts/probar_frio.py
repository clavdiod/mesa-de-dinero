"""19/11: ¿la revisión en frío es muy severa? Corre el control semanal (mesa/agentes/control_frio.py) a mano y muestra todo."""
import json
from datetime import date
from mesa.agentes import control_frio
from mesa.nucleo.almacen import almacen_por_defecto
r = control_frio.medir(almacen_por_defecto(), date.today())
for m, g in r["mercados"].items():
    for grupo, x in g.items():
        print(f"::notice::{m} {grupo} | todos {x['todos']} | pasa {x['pasa']} | frena {x['frena']} | dudosos {x['dudosos']} | solo por regla: " + json.dumps(x["reglas"], ensure_ascii=False))
print("::notice::ALERTAS " + (" || ".join(r["alertas"]) or "ninguna"))
