"""Segunda venta: 25 IREN a $3.687,50 (92.187,50) el 29/10. IREN sale de la cartera, de la lista y de las decisiones."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
TK, CANT, PRECIO, FECHA, COMPRA = "IREN", 25, 3687.5, "2026-10-29", 3495.0
a = almacen_por_defecto()
ops = a.get("usuario/operaciones") or []
ops = ops if isinstance(ops, list) else []
if not any(isinstance(o, dict) and o.get("ticker") == TK and o.get("fecha") == FECHA and o.get("precio") == PRECIO for o in ops):
    ops.insert(0, {"fecha": FECHA, "ticker": TK, "cantidad": CANT, "precio": PRECIO, "compra": COMPRA, "fecha_compra": "2026-10-22",
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
print("::notice::IREN cerrada: " + json.dumps(iren, ensure_ascii=False) + f" | total {sum(o['ganancia'] for o in iren)}")
print("::notice::cartera: " + ", ".join(str(x.get("ticker")) for x in (a.get("usuario/cartera") or [])))
