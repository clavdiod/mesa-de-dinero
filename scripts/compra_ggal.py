"""Compra real: 35 GGAL a $4.460 el 20/11 11:33 (límite, gastos $944,40). Posición recomendada por la mesa (11:20 del 20/11):
rebote en dólares, plazo 1 a 3 meses, alarma de venta en $3.350 (-24,9%)."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos.cache import CacheHistorico
from mesa.agentes import ficha_frio, estructura
TK, CANT, PRECIO, FECHA, GASTOS, ALARMA = "GGAL", 35, 4460.0, "2026-11-20", 944.40, 3350.0
a = almacen_por_defecto()
cart = a.get("usuario/cartera") or []
if not any(str(x.get("ticker", "")).upper() == TK for x in cart):
    cart.append({"ticker": TK, "cantidad": CANT, "precio": PRECIO, "fecha": FECHA, "gastos_compra": GASTOS,
                 "plazo_motivo": "posición recomendada por la mesa (20/11): rebote en dólares, plazo 1 a 3 meses",
                 "alertas": [{"id": "stop-GGAL-2011", "tipo": "baja", "nivel": ALARMA, "moneda": "ARS", "creada": FECHA,
                              "nota": "Alarma de venta (-24,9% de tu compra): el rebote no se dio."}]})
    a.put("usuario/cartera", cart)
vel = CacheHistorico(a).velas(TK)
if vel:
    pr = vel[-1]["cierre"]
    plan = {"ticker": TK, "entrada": PRECIO, "stop": ALARMA, "objetivo": PRECIO * 1.30}
    f = ficha_frio.ficha(vel[-400:], PRECIO, plan, estructura.leer(vel[-300:], PRECIO, "acciones") or {}, [], "acciones")
    print("::notice::FICHA " + ficha_frio.texto(f).replace("\n", " ")[:2500])
    print("::notice::GRAFICO " + estructura.frase(estructura.leer(vel[-300:], PRECIO, "acciones") or {}))
print("::notice::posición: " + json.dumps(next(x for x in cart if x.get("ticker") == TK), ensure_ascii=False))
print("::notice::cartera: " + ", ".join(str(x.get("ticker")) for x in cart))
