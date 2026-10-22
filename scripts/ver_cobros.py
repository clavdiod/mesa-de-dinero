"""Cobros de la cartera real con flujos de MAE (sin avisar nada)."""
from datetime import date

from mesa.datos import cobros as c
from mesa.nucleo.almacen import almacen_por_defecto

a = almacen_por_defecto()
cart = a.get("usuario/cartera") or []
f = c.asegurar_flujos(a, [x["ticker"] for x in cart], date.today())
cs = c.proximos(cart, f, date.today(), 400)
print("::notice::" + f"cartera {[(x['ticker'], x['cantidad']) for x in cart]} || flujos: {list(f)} || " + " | ".join(f"{x['fecha']} {c.texto(x)}" for x in cs[:12]))
