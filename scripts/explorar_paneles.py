"""Cuenta cuántos títulos trae cada panel de Bonos/Acciones (diagnóstico, ~20 consultas)."""
from mesa.datos.consumo import Consumo
from mesa.datos.iol import IOL
from mesa.nucleo.almacen import almacen_por_defecto

a = almacen_por_defecto(); c = Consumo(a); iol = IOL(c, almacen=a)
out = []
for inst in ("Bonos", "Cauciones"):
    pans = iol.paneles_disponibles(inst)
    pans = [p.get("panel") if isinstance(p, dict) else p for p in (pans or [])] or ["Todas"]
    for p in pans:
        try:
            t = iol.panel(inst, p)
            out.append(f"{inst}/{p}={len(t)} ej:{','.join(x['simbolo'] or '' for x in t[:4])}")
        except Exception as e:
            out.append(f"{inst}/{p}=ERR {str(e)[:60]}")
c.guardar()
print("::notice::" + " | ".join(out)[:3000])
