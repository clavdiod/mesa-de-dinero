"""Venta real: 92 CEPU a $1.738 el 20/11 11:30 (límite, gastos estimados $967,37)."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
TK, CANT, PRECIO, FECHA, GASTOS = "CEPU", 92, 1738.0, "2026-11-20", 967.37
a = almacen_por_defecto()
cart = a.get("usuario/cartera") or []
pos = next(x for x in cart if str(x.get("ticker", "")).upper() == TK)
print(f"::notice::posición antes: {json.dumps(pos, ensure_ascii=False)[:400]}")
COMPRA = float(pos["precio"]); cant = min(CANT, int(float(pos["cantidad"])))
ops = a.get("usuario/operaciones") or []
ops = ops if isinstance(ops, list) else []
if not any(isinstance(o, dict) and o.get("ticker") == TK and o.get("fecha") == FECHA for o in ops):
    bruta = round((PRECIO - COMPRA) * cant)
    ops.insert(0, {"fecha": FECHA, "ticker": TK, "cantidad": cant, "precio": PRECIO, "compra": COMPRA, "fecha_compra": pos.get("fecha"),
                   "resultado_pct": round((PRECIO / COMPRA - 1) * 100, 2), "ganancia": bruta, "gastos_venta": GASTOS,
                   "ganancia_neta_venta": round(bruta - GASTOS)})
a.put("usuario/operaciones", ops)
resto = int(float(pos["cantidad"])) - cant
if resto > 0:
    pos["cantidad"] = resto
    a.put("usuario/cartera", cart)
else:
    a.put("usuario/cartera", [x for x in cart if str(x.get("ticker", "")).upper() != TK])
    dec = a.get("usuario/decisiones_cartera") or {}
    if isinstance(dec, dict):
        dec.pop(TK, None); a.put("usuario/decisiones_cartera", dec)
    av = a.get("cartera/avisados") or {}
    av.pop(TK, None); a.put("cartera/avisados", av)
o = next(x for x in ops if isinstance(x, dict) and x.get("ticker") == TK and x.get("fecha") == FECHA)
print(f"::notice::CEPU cerrada: {json.dumps(o, ensure_ascii=False)} · quedan {resto}")
print("::notice::total operaciones cerradas: " + str(sum(x.get("ganancia") or 0 for x in ops if isinstance(x, dict))))
print("::notice::cartera: " + ", ".join(str(x.get("ticker")) for x in (a.get("usuario/cartera") or [])))
