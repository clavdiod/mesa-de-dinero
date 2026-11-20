"""Compra real: 22 TRAN a $2.050 el 20/11 12:22 (límite, gastos $272,85). Compra grande revisada por la mesa (✅ entrar).
Alarma $1.799 (-12,2%); objetivo $2.462 (~1 mes). Dejar correr: desde $2.300 la alarma sube a $2.075 (sin pérdida)
y después sigue al máximo 10% abajo."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
TK, CANT, PRECIO, FECHA, GASTOS, ALARMA = "TRAN", 22, 2050.0, "2026-11-20", 272.85, 1799.0
a = almacen_por_defecto()
cart = a.get("usuario/cartera") or []
if not any(str(x.get("ticker", "")).upper() == TK for x in cart):
    cart.append({"ticker": TK, "cantidad": CANT, "precio": PRECIO, "fecha": FECHA, "gastos_compra": GASTOS,
                 "plazo_motivo": "compra grande revisada por la mesa (20/11): ✅ entrar, objetivo $2.462, plazo ~1 mes",
                 "objetivo_idea": 2462.0, "objetivo_usuario": 2300.0, "alarma_escalon": 2075.0, "trailing_pct": 10.0,
                 "plan_texto": "Dejar correr: alarma $1.799; desde $2.300 la alarma sube a $2.075 (sin pérdida) y después sigue al máximo 10% abajo. Objetivo $2.462.",
                 "alertas": [{"id": "stop-TRAN-2011", "tipo": "baja", "nivel": ALARMA, "moneda": "ARS", "creada": FECHA,
                              "nota": "Alarma de venta (-12,2% de tu compra): la compra grande no se sostuvo."}]})
    a.put("usuario/cartera", cart)
print("::notice::posición: " + json.dumps(next(x for x in cart if x.get("ticker") == TK), ensure_ascii=False))
print("::notice::cartera: " + ", ".join(str(x.get("ticker")) for x in cart))
