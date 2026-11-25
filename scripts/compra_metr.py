"""Compra real: 44 METR a $1.668 promedio el 25/11 11:28 (límite, gastos $444,02), por la recomendación de la mesa de hoy.
La alarma y el objetivo salen del plan de esa propuesta (si no hay, -8%). Solo imprime METR (los logs son públicos)."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
TK, CANT, PRECIO, FECHA, GASTOS = "METR", 44, 1668.0, "2026-11-25", 444.02
a = almacen_por_defecto()
props = [p for p in (a.get("registro/propuestas") or []) if str(p.get("ticker", "")).upper() == TK and "2026-11-20" <= p.get("fecha", "") <= FECHA]
prop = max(props, key=lambda p: (p.get("fecha"), p.get("hora") or "")) if props else {}
pl = prop.get("plan") or {}
stop, obj = pl.get("stop"), pl.get("objetivo")
print(f"::notice::propuesta: {prop.get('fecha') or 'no'} · línea {prop.get('linea', 'corto')} · hora {prop.get('hora')} · "
      f"entrada {pl.get('entrada')} · stop {stop} · objetivo {obj} · vence {pl.get('vence')} · meses {prop.get('meses')}")
if not stop:  # sin plan guardado: alarma a -8%
    stop = round(PRECIO * 0.92)
pos = {"ticker": TK, "cantidad": CANT, "precio": PRECIO, "fecha": FECHA, "gastos_compra": GASTOS,
       "plazo_motivo": f"recomendada por la mesa ({(prop.get('fecha') or '')[8:]}/{(prop.get('fecha') or '')[5:7]} {prop.get('hora') or ''}); comprada con límite el 25/11 11:28",
       "alertas": [{"id": f"stop-{TK}-2511", "tipo": "baja", "nivel": float(stop), "moneda": "ARS", "creada": FECHA,
                    "nota": f"Alarma de venta, stop del plan ({(float(stop) / PRECIO - 1) * 100:+.1f}% de tu compra): la idea no se dio."}]}
if obj:
    pos["objetivo_idea"] = float(obj)
if prop.get("id"):
    pos["propuesta_id"] = prop["id"]
cart = a.get("usuario/cartera") or []
if not any(str(x.get("ticker", "")).upper() == TK for x in cart):
    cart.append(pos)
    a.put("usuario/cartera", cart)
    print("::notice::METR cargada en la cartera")
else:
    print("::notice::METR ya estaba en la cartera (no se tocó)")
print("::notice::posición: " + json.dumps(next(x for x in cart if str(x.get("ticker", "")).upper() == TK), ensure_ascii=False))
