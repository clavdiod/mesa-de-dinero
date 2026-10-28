"""IBB: fecha de compra 22/10 (la dio el usuario)."""
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
cart = a.get("usuario/cartera") or []
for x in cart:
    if str(x.get("ticker", "")).upper() == "IBB":
        x["fecha"] = "2026-10-22"
a.put("usuario/cartera", cart)
print("::notice::" + str([x for x in cart if str(x.get("ticker", "")).upper() == "IBB"]))
