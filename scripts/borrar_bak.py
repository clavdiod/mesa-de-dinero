"""BAK vendido completo el 28/10: se borra de cartera, favoritos, alertas y decisiones. Queda solo el registro de la venta con los netos reales."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
a.put("usuario/cartera", [x for x in (a.get("usuario/cartera") or []) if str(x.get("ticker", "")).upper() != "BAK"])
a.put("usuario/lista", [x for x in (a.get("usuario/lista") or []) if str(x.get("ticker", "")).upper() != "BAK"])
dec = a.get("usuario/decisiones_cartera") or {}
if isinstance(dec, dict):
    dec.pop("BAK", None)
    a.put("usuario/decisiones_cartera", dec)
ops = [o for o in (a.get("usuario/operaciones") or []) if isinstance(o, dict) and o.get("ticker") != "BAK"]
compra_u = 188855.71 / 190  # neto con comisión
ops = [{"fecha": "2026-10-28", "ticker": "BAK", "cantidad": 90, "precio": round(88560.95 / 90, 2), "compra": round(compra_u, 2), "fecha_compra": "2026-10-27",
        "resultado_pct": round((88560.95 / 90 / compra_u - 1) * 100, 2), "ganancia": round(88560.95 - compra_u * 90), "neto": True},
       {"fecha": "2026-10-28", "ticker": "BAK", "cantidad": 100, "precio": round(99355.24 / 100, 2), "compra": round(compra_u, 2), "fecha_compra": "2026-10-27",
        "resultado_pct": round((99355.24 / 100 / compra_u - 1) * 100, 2), "ganancia": round(99355.24 - compra_u * 100), "neto": True}] + ops
a.put("usuario/operaciones", ops)
seg = a.get("cartera/avisados") or {}
seg.pop("BAK", None)
a.put("cartera/avisados", seg)
print("::notice::BAK borrado. Ventas: " + json.dumps(ops[:2], ensure_ascii=False) + " total " + str(sum(o["ganancia"] for o in ops[:2])))
