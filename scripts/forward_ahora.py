from datetime import date
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.agentes import ciclo
a = almacen_por_defecto(); f = ciclo.forward_politico(a, date.today())
print("::notice::" + str(f))
t = a.get(ciclo.CLAVE) or {}
if f and t.get("argentina") and "forward" not in t:
    t["forward"] = f; t["argentina"]["texto"] += " " + f["texto"]; a.put(ciclo.CLAVE, t)
