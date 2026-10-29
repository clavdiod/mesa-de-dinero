"""YPFD: la compra real (36 a 8.135, 29/10) sigue la propuesta del Comité de las 10:55 (stop 7.470, objetivo 10.130, hasta 26/11)."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
TK, PRECIO, FECHA = "YPFD", 8135.0, "2026-10-29"
a = almacen_por_defecto()
props = a.get("registro/propuestas") or []
p = next((x for x in reversed(props) if x["ticker"] == TK and x["fecha"] == FECHA), None)
if p:
    p["decision"] = "aprobada"
    p["plan"].setdefault("entrada_plan", p["plan"]["entrada"])
    p["plan"]["entrada"] = PRECIO
    p.setdefault("seguimiento", {}).update(estado="abierta", fecha_entrada=FECHA, precio_entrada=PRECIO)
    p["seguimiento"].pop("consejo", None)
    a.put("registro/propuestas", props)
cart = a.get("usuario/cartera") or []
c = next(x for x in cart if x.get("ticker") == TK)
c["vence"] = p["plan"]["vence"] if p else None
c["plazo_motivo"] = "plan del Comité (20 ruedas)"
c["alertas"] = [{"tipo": "baja", "nivel": round(p["plan"]["stop"], 2), "moneda": "ARS", "nota": "stop del plan del Comité"}] if p else []
a.put("usuario/cartera", cart)
print("::notice::" + json.dumps(c, ensure_ascii=False) + " | plan " + json.dumps(p and p["plan"]))
