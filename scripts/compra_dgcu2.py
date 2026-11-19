"""Compra real: 158 DGCU2 (Gas Cuyana) a $1.205 el 19/11 15:13 (límite, ejecutada en parte de 164; gastos ~$1.110).
Entró por el aviso de compra grande ⭐ después de la caída. Alarma de venta en $1.110 (-7,9%), la acordada con Clau."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos.cache import CacheHistorico
from mesa.agentes import ficha_frio, estructura
TK, CANT, PRECIO, FECHA, GASTOS, ALARMA = "DGCU2", 158, 1205.0, "2026-11-19", round(1151.84 * 158 / 164, 2), 1110.0
a = almacen_por_defecto()
cart = a.get("usuario/cartera") or []
if not any(str(x.get("ticker", "")).upper() == TK for x in cart):
    cart.append({"ticker": TK, "cantidad": CANT, "precio": PRECIO, "fecha": FECHA, "gastos_compra": GASTOS,
                 "plazo_motivo": "compra propia de Clau (19/11) por el aviso de compra grande después de la caída",
                 "alertas": [{"id": "stop-DGCU2-1911", "tipo": "baja", "nivel": ALARMA, "moneda": "ARS", "creada": FECHA,
                              "nota": "Alarma de venta (-7,9% de tu compra): la compra grande no se sostuvo."}]})
    a.put("usuario/cartera", cart)
vel = CacheHistorico(a).velas(TK)
if vel:
    pr = vel[-1]["cierre"]
    plan = {"ticker": TK, "entrada": PRECIO, "stop": ALARMA, "objetivo": PRECIO * 1.16}
    f = ficha_frio.ficha(vel[-400:], PRECIO, plan, estructura.leer(vel[-300:], PRECIO, "acciones") or {}, [], "acciones")
    print("::notice::FICHA " + ficha_frio.texto(f).replace("\n", " ")[:2500])
    print("::notice::GRAFICO " + estructura.frase(estructura.leer(vel[-300:], PRECIO, "acciones") or {}))
print("::notice::posición: " + json.dumps(next(x for x in cart if x.get("ticker") == TK), ensure_ascii=False))
print("::notice::cartera: " + ", ".join(str(x.get("ticker")) for x in cart))
