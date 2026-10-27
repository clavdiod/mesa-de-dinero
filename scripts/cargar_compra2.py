"""Carga una compra real del usuario (otro broker): cartera, propuesta del Jefe (si hay) con su precio real y alertas.
TK, CANT y PRECIO van fijos abajo; si la propuesta no existe solo carga la cartera y muestra lo que dice la mesa."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
TK, CANT, PRECIO, FECHA = "BAK", 190, 988.0, "2026-10-27"
a = almacen_por_defecto()
cart = a.get("usuario/cartera") or []
ya = [x for x in cart if str(x.get("ticker", "")).upper() == TK]
if not ya:
    cart.append({"ticker": TK, "cantidad": CANT, "precio": PRECIO})
    a.put("usuario/cartera", cart)
print("::notice::CARTERA " + json.dumps(ya or "agregado", ensure_ascii=False))
props = a.get("registro/propuestas") or []
p = next((x for x in reversed(props) if x["ticker"] == TK and x["fecha"] >= "2026-10-26"), None)
if p:
    p["decision"] = "aprobada"
    p["plan"].setdefault("entrada_plan", p["plan"]["entrada"])
    p["plan"]["entrada"] = PRECIO
    p["seguimiento"].update(estado="abierta", fecha_entrada=FECHA, precio_entrada=PRECIO)
    p["seguimiento"].pop("consejo", None)
    a.put("registro/propuestas", props)
print("::notice::PROPUESTA " + json.dumps({k: p.get(k) for k in ("fecha", "hora", "plan", "decision", "resumen_jefe")} if p else None, ensure_ascii=False))
est = a.get("ui/estado") or {}
d = (a.get("ui/debates") or {}).get(TK) or {}
sup = d.get("supervisor") or {}
print(f"::notice::DEBATE {d.get('fecha')} {d.get('hora')} {sup.get('veredicto')} | {sup.get('titulo')} | " + " / ".join(sup.get("detalle") or []) + f" | plan {json.dumps(d.get('plan'))} | precio {json.dumps(d.get('precio'))}")
for lado in ("favor", "contra", "neutral"):
    print(f"::notice::{lado.upper()} " + " || ".join(f"{s.get('agente')} ({s.get('fuerza')}): {s.get('texto')}" for s in (d.get(lado) or []))[:2500])
print("::notice::OTROS " + json.dumps({"anticipos": [x for x in (est.get("anticipos") or []) if x["ticker"] == TK],
      "lista": [x for x in ((est.get("anticipo_lista") or {}).get("lista") or []) if x["ticker"] == TK],
      "pron": [{k: x.get(k) for k in ("origen", "estado", "fecha", "ref", "objetivo_pct", "texto")} for x in (est.get("pronosticos") or []) if x["ticker"] == TK][:5],
      "ops": [o for l in (est.get("oportunidades") or {}).values() for o in l if o["ticker"] == TK],
      "proy": (est.get("proyeccion_cartera") or {}).get(TK), "hora": est.get("hora")}, ensure_ascii=False)[:3500])
