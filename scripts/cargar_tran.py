"""Carga la compra de TRAN (28/10, Cocos): cartera con fecha y el stop del plan del Anticipador ARG como alerta."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
TK, CANT, PRECIO, FECHA = "TRAN", 84, 2158.0, "2026-10-28"
a = almacen_por_defecto()
lib = a.get("pronosticos/libreta") or []
ideas = [x for x in lib if x.get("ticker") == TK and x.get("fecha", "") >= "2026-10-20"]
print("::notice::IDEAS " + json.dumps([{k: x.get(k) for k in ("fecha", "origen", "ref", "objetivo_pct", "estado", "plan")} for x in ideas][-4:], ensure_ascii=False)[:1500])
plan = next((x.get("plan") for x in reversed(ideas) if x.get("plan")), None) or {}
est = a.get("ui/estado") or {}
for l in [est.get("anticipo_listas") or {}]:
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
    e["alertas"] = [{"tipo": "baja", "nivel": round(stop, 2), "moneda": "ARS", "nota": "stop del plan (Anticipador ARG)"}]
cart.append(e)
a.put("usuario/cartera", cart)
print("::notice::CARTERA " + json.dumps(e, ensure_ascii=False))
