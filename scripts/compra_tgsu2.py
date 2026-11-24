"""Compra real: 33 TGSU2 a $7.000 el 24/11 ~11:26 (límite, en Banco Galicia; comisión $808,55 + derecho $161,70 + IVA $203,75).
Entró por la recomendación de la mesa de hoy, a un precio más bajo que la entrada del plan. La alarma y el objetivo salen
del plan de esa propuesta. Solo imprime la posición de TGSU2 (los logs son públicos: nada del resto de la cartera)."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
TK, CANT, PRECIO, FECHA, GASTOS = "TGSU2", 33, 7000.0, "2026-11-24", round(808.55 + 161.70 + 203.75, 2)
a = almacen_por_defecto()
props = [p for p in (a.get("registro/propuestas") or []) if str(p.get("ticker", "")).upper() == TK and p.get("fecha") == FECHA]
prop = props[0] if props else {}
pl = prop.get("plan") or {}
stop, obj = pl.get("stop"), pl.get("objetivo")
print(f"::notice::propuesta de hoy: {'sí' if prop else 'no'} · línea {prop.get('linea', 'corto')} · hora {prop.get('hora')} · "
      f"entrada {pl.get('entrada')} · stop {stop} · objetivo {obj} · vence {pl.get('vence')} · meses {prop.get('meses')}")
if not stop:  # sin plan guardado: alarma a -8%
    stop = round(PRECIO * 0.92)
pos = {"ticker": TK, "cantidad": CANT, "precio": PRECIO, "fecha": FECHA, "gastos_compra": GASTOS,
       "plazo_motivo": f"recomendada por la mesa (24/11 {prop.get('hora') or ''}); comprada en Banco Galicia más barato que la entrada del plan",
       "alertas": [{"id": f"stop-{TK}-2411", "tipo": "baja", "nivel": float(stop), "moneda": "ARS", "creada": FECHA,
                    "nota": f"Alarma de venta ({(float(stop) / PRECIO - 1) * 100:+.1f}% de tu compra): la idea no se dio."}]}
if obj:
    pos["objetivo_idea"] = float(obj)
if prop.get("id"):
    pos["propuesta_id"] = prop["id"]
cart = a.get("usuario/cartera") or []
if not any(str(x.get("ticker", "")).upper() == TK for x in cart):
    cart.append(pos)
    a.put("usuario/cartera", cart)
    print("::notice::TGSU2 cargada en la cartera")
else:
    print("::notice::TGSU2 ya estaba en la cartera (no se tocó)")
print("::notice::posición: " + json.dumps(next(x for x in cart if str(x.get("ticker", "")).upper() == TK), ensure_ascii=False))
