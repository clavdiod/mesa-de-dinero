"""Venta real: 25 IREN a $3.667,50 el 29/10 (a mercado). Quedan las otras con stop en $3.619."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
TK, CANT, PRECIO, FECHA, STOP = "IREN", 25, 3667.5, "2026-10-29", 3619.0
a = almacen_por_defecto()
cart = a.get("usuario/cartera") or []
c = next(x for x in cart if str(x.get("ticker", "")).upper() == TK)
ops = a.get("usuario/operaciones") or []
ops = ops if isinstance(ops, list) else []
if not any(isinstance(o, dict) and o.get("ticker") == TK and o.get("fecha") == FECHA and o.get("cantidad") == CANT for o in ops):
    ops.insert(0, {"fecha": FECHA, "ticker": TK, "cantidad": CANT, "precio": PRECIO, "compra": c.get("precio"), "fecha_compra": c.get("fecha"),
                   "resultado_pct": round((PRECIO / float(c["precio"]) - 1) * 100, 2), "ganancia": round((PRECIO - float(c["precio"])) * CANT)})
    c["cantidad"] = int(float(c["cantidad"])) - CANT
al = [x for x in (c.get("alertas") or []) if not (x.get("tipo") == "baja" and "stop" in str(x.get("nota", "")).lower())]
al.append({"tipo": "baja", "nivel": STOP, "moneda": "ARS", "nota": "stop de la mitad que queda (29/10)"})
c["alertas"] = al
a.put("usuario/cartera", [x for x in cart if float(x.get("cantidad") or 0) > 0])
a.put("usuario/operaciones", ops)
dec = a.get("usuario/decisiones_cartera") or {}
dec = dec if isinstance(dec, dict) else {}
dec[TK] = {"fecha": FECHA, "accion": "vender_mitad", "sugerida": "vender_mitad", "detalle": f"vendiste {CANT} a 3.667,50; stop {STOP} para el resto"}
a.put("usuario/decisiones_cartera", dec)
print("::notice::queda " + json.dumps(c, ensure_ascii=False)[:400] + " | op " + json.dumps(ops[0], ensure_ascii=False))
