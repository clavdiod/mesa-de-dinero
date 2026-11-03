import json
from datetime import date
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
for x in (a.get("ui/alertas") or [])[:15]:
    if x.get("fecha") == date.today().isoformat():
        print("::notice::" + json.dumps(x, ensure_ascii=False)[:400])
print("::notice::avisados " + json.dumps(a.get("cartera/avisados"), ensure_ascii=False))
