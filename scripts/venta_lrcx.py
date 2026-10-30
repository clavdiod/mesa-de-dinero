"""Venta real: 26 LRCX a $7.120 el 30/10 (a mercado). LRCX sale de la cartera."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
TK, CANT, PRECIO, FECHA = "LRCX", 26, 7120.0, "2026-10-30"
a = almacen_por_defecto()
pos = next(x for x in (a.get("usuario/cartera") or []) if str(x.get("ticker", "")).upper() == TK)
COMPRA = float(pos["precio"]); print(f"::notice::posición {pos}")
ops = a.get("usuario/operaciones") or []
ops = ops if isinstance(ops, list) else []
if not any(isinstance(o, dict) and o.get("ticker") == TK and o.get("fecha") == FECHA and o.get("precio") == PRECIO for o in ops):
    ops.insert(0, {"fecha": FECHA, "ticker": TK, "cantidad": CANT, "precio": PRECIO, "compra": COMPRA, "fecha_compra": pos.get("fecha"),
                   "resultado_pct": round((PRECIO / COMPRA - 1) * 100, 2), "ganancia": round((PRECIO - COMPRA) * CANT)})
a.put("usuario/operaciones", ops)
a.put("usuario/cartera", [x for x in (a.get("usuario/cartera") or []) if str(x.get("ticker", "")).upper() != TK])
a.put("usuario/lista", [x for x in (a.get("usuario/lista") or []) if str((x.get("ticker") if isinstance(x, dict) else x) or "").upper() != TK])
dec = a.get("usuario/decisiones_cartera") or {}
if isinstance(dec, dict):
    dec.pop(TK, None)
    a.put("usuario/decisiones_cartera", dec)
av = a.get("cartera/avisados") or {}
av.pop(TK, None); a.put("cartera/avisados", av)
iren = [o for o in ops if isinstance(o, dict) and o.get("ticker") == TK and o.get("fecha") == FECHA]
print("::notice::LRCX cerrada: " + json.dumps(iren, ensure_ascii=False) + f" | total {sum(o['ganancia'] for o in iren)}")
print("::notice::cartera: " + ", ".join(str(x.get("ticker")) for x in (a.get("usuario/cartera") or [])))
