"""Carga una compra real (Cocos): cartera con fecha y, si hay, el stop del plan de la idea como alerta."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
TK, CANT, PRECIO, FECHA = "YPFD", 36, 8135.0, "2026-10-29"
a = almacen_por_defecto()
lib = a.get("pronosticos/libreta") or []
ideas = [x for x in lib if x.get("ticker") == TK and x.get("fecha", "") >= "2026-10-20"]
print("::notice::IDEAS " + json.dumps([{k: x.get(k) for k in ("fecha", "origen", "ref", "objetivo_pct", "estado", "plan")} for x in ideas][-4:], ensure_ascii=False)[:1500])
plan = next((x.get("plan") for x in reversed(ideas) if x.get("plan")), None) or {}
est = a.get("ui/estado") or {}
d = (a.get("ui/debates") or {}).get(TK) or {}
sup = d.get("supervisor") or {}
print(f"::notice::DEBATE {d.get('fecha')} {d.get('hora')} {sup.get('veredicto')} | {sup.get('titulo')} | plan {json.dumps(d.get('plan'))}")
print("::notice::COMITE " + json.dumps([c for c in ((est.get("comite") or {}).get("acta") or []) if c.get("ticker") == TK], ensure_ascii=False)[:800])
print("::notice::PROP " + json.dumps([{k: p.get(k) for k in ("fecha", "hora", "plan", "decision", "resumen_jefe")} for p in (a.get("registro/propuestas") or []) if p.get("ticker") == TK][-2:], ensure_ascii=False)[:900])
for l in [{"anticipador": est.get("anticipo_lista") or {}, **(est.get("anticipo_listas") or {})}]:
    for k, v in l.items():
        for x in v.get("lista") or []:
            if x["ticker"] == TK:
                plan = plan or x.get("plan") or {}
                print(f"::notice::LISTA {k} " + json.dumps({kk: x.get(kk) for kk in ("prob", "razones", "plan", "prioridad")}, ensure_ascii=False))
stop = plan.get("stop")
cart = a.get("usuario/cartera") or []
cart = [x for x in cart if str(x.get("ticker", "")).upper() != TK]
e = {"ticker": TK, "cantidad": CANT, "precio": PRECIO, "fecha": FECHA}
if stop and stop < PRECIO:
    e["alertas"] = [{"tipo": "baja", "nivel": round(stop, 2), "moneda": "ARS", "nota": "stop del plan de la idea"}]
cart.append(e)
a.put("usuario/cartera", cart)
print("::notice::CARTERA " + json.dumps(e, ensure_ascii=False))
