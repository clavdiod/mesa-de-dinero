"""Venta real del usuario: 100 BAK a $999,50 el 28/10 (quedan 90)."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
cart = a.get("usuario/cartera") or []
c = next(x for x in cart if str(x.get("ticker", "")).upper() == "BAK")
ops = a.get("usuario/operaciones") or []
if not any(o.get("ticker") == "BAK" and o.get("fecha") == "2026-10-28" and o.get("cantidad") == 100 for o in ops if isinstance(o, dict)):
    ops = ops if isinstance(ops, list) else []
    ops.insert(0, {"fecha": "2026-10-28", "ticker": "BAK", "cantidad": 100, "precio": 999.5, "compra": c.get("precio"), "fecha_compra": c.get("fecha"),
                   "resultado_pct": round((999.5 / c["precio"] - 1) * 100, 2), "ganancia": round((999.5 - c["precio"]) * 100)})
    c["cantidad"] = int(c["cantidad"]) - 100
a.put("usuario/cartera", [x for x in cart if float(x.get("cantidad") or 0) > 0])
a.put("usuario/operaciones", ops)
dec = a.get("usuario/decisiones_cartera") or {}
dec = dec if isinstance(dec, dict) else {}
dec["BAK"] = {"fecha": "2026-10-28", "accion": "vender_mitad", "sugerida": "vender_mitad", "detalle": "vendiste 100 a 999,50"}
a.put("usuario/decisiones_cartera", dec)
print("::notice::BAK queda: " + json.dumps(c, ensure_ascii=False)[:400] + " | op: " + json.dumps(ops[0], ensure_ascii=False))
