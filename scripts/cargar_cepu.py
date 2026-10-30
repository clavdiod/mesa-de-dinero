"""Compra real: 102 CEPU a $1.791 (30/10, Cocos). Sigue la propuesta del Comité del día."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
TK, CANT, PRECIO, FECHA = "CEPU", 102, 1791.0, "2026-10-30"
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
else:  # sin propuesta guardada: el plan del debate de hoy
    d = ((a.get("ui/debates") or {}).get(TK) or {}).get("plan") or {}
    p = {"plan": d} if d else None
cart = [x for x in (a.get("usuario/cartera") or []) if str(x.get("ticker", "")).upper() != TK]
e = {"ticker": TK, "cantidad": CANT, "precio": PRECIO, "fecha": FECHA}
if p and p.get("plan"):
    e.update(vence=p["plan"].get("vence"), plazo_motivo="plan del Comité (20 ruedas)",
             alertas=[{"tipo": "baja", "nivel": round(p["plan"]["stop"], 2), "moneda": "ARS", "nota": "stop del plan del Comité"}])
cart.append(e)
a.put("usuario/cartera", cart)
print("::notice::" + json.dumps(e, ensure_ascii=False) + " | plan " + json.dumps(p and p.get("plan")))
