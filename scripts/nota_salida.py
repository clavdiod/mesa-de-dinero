"""12/11: el aviso al llegar al precio de salida ya no dice 'vendé': los agentes analizan si vender o dejar correr."""
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
cart = a.get("usuario/cartera") or []
n = 0
for c in cart:
    for al in c.get("alertas") or []:
        if str(al.get("id", "")).startswith("salida-"):
            al["nota"] = ("💰 Llegó a tu precio de salida con ganancia. Los agentes analizan si conviene vender o dejarla correr con la ganancia asegurada: "
                          "mirá la sugerencia en la app antes de vender.")
            n += 1
a.put("usuario/cartera", cart)
print(f"::notice::{n} avisos de salida actualizados")
