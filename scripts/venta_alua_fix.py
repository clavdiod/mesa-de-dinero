"""La venta de ALUA quedó anotada con cantidad 1 (y 394 en cartera): son 395 a 760."""
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
ops = a.get("usuario/operaciones") or []
for o in ops:
    if isinstance(o, dict) and o.get("ticker") == "ALUA" and o.get("fecha") == "2026-11-05":
        o.update(cantidad=395, ganancia=round((760 - 850) * 395))
a.put("usuario/operaciones", ops)
print("::notice::" + " | ".join(f"{o.get('fecha')} {o.get('ticker')} {o.get('cantidad')}: {o.get('ganancia')}" for o in ops if isinstance(o, dict))
      + f" · total {sum(o.get('ganancia') or 0 for o in ops if isinstance(o, dict))}")
print("::notice::cartera: " + ", ".join(str(x.get("ticker")) for x in (a.get("usuario/cartera") or [])))
