"""20/11: plan para dejar correr GGAL (pedido de Clau: "seguirá a diario junto al resto de la cartera y me avisás").
Alarma $3.350; al llegar a $5.000 los agentes revisan y la alarma sube a $4.520 (compra + comisiones: ya no se pierde)
y después sigue al máximo 10% abajo (GGAL se mueve mucho: con menos saltaría por ruido)."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
cart = a.get("usuario/cartera") or []
p = next(x for x in cart if x.get("ticker") == "GGAL")
p.update(objetivo_usuario=5000.0, alarma_escalon=4520.0, trailing_pct=10.0,
         plan_texto="Dejar correr: alarma $3.350; desde $5.000 la alarma sube a $4.520 (sin pérdida) y después sigue al máximo 10% abajo.")
a.put("usuario/cartera", cart)
print("::notice::" + json.dumps(p, ensure_ascii=False))
