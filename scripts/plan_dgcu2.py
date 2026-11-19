"""19/11: plan para dejar correr DGCU2 (pedido de Clau). Alarma $1.110; al llegar a $1.275 la alarma sube a $1.220
(arriba de la compra) y después sigue al máximo 6% abajo. Los agentes revisan en cada escalón."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
cart = a.get("usuario/cartera") or []
p = next(x for x in cart if x.get("ticker") == "DGCU2")
p.update(objetivo_usuario=1275.0, alarma_escalon=1220.0, trailing_pct=6.0,
         plan_texto="Dejar correr: alarma $1.110; desde $1.275 la alarma sube a $1.220 y después sigue al máximo 6% abajo.")
a.put("usuario/cartera", cart)
print("::notice::" + json.dumps(p, ensure_ascii=False))
