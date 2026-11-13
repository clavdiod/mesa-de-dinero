"""Compra real: 6 COST (CEDEAR de Costco) a $38.620 el 13/11 (a mercado, gastos $1.401,90). Ficha en frío y alarma de venta."""
import json
import numpy as np
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos import gratis
from mesa.agentes import ficha_frio, estructura
TK, CANT, PRECIO, FECHA = "COST", 6, 38620.0, "2026-11-13"
a = almacen_por_defecto()
v = gratis.yahoo_ohlcv("COST", "10y")
viv = gratis.yahoo_vivo("COST")
vel = [{"fecha": x["fecha"], "cierre": x["c"], "maximo": x["h"], "minimo": x["l"], "apertura": x["o"], "volumen": x["v"]} for x in v]
c = np.array([x["c"] for x in v]); pr = viv.get("precio") or c[-1]
atr = np.mean([x["h"] - x["l"] for x in v[-14:]])
dist = min(0.12, max(0.06, 2.5 * atr / pr))
plan = {"entrada": pr, "stop": pr * (1 - dist), "objetivo": pr * 1.12}
est = estructura.leer(vel[-300:], pr, "cedears") or {}
f = ficha_frio.ficha(vel[-400:], pr, plan, est, [], "cedears")
y1 = c[-252:]
alarma = round(PRECIO * (1 - dist) / 5) * 5
cart = a.get("usuario/cartera") or []
if not any(str(x.get("ticker", "")).upper() == TK for x in cart):
    cart.append({"ticker": TK, "cantidad": CANT, "precio": PRECIO, "fecha": FECHA, "gastos_compra": 1401.90,
                 "plazo_motivo": "compra propia de Clau (13/11)",
                 "alertas": [{"id": "stop-COST-1311", "tipo": "baja", "nivel": float(alarma), "moneda": "ARS", "creada": FECHA,
                              "nota": f"Alarma de venta (-{dist * 100:.0f}% de tu compra, 2,5 veces el movimiento diario normal de Costco)."}]})
    a.put("usuario/cartera", cart)
print(f"::notice::COST USD {pr:.2f} · 1 año máx {y1.max():.2f} mín {y1.min():.2f} · ubicación en el rango {(pr - y1.min()) / (y1.max() - y1.min()) * 100:.0f}% · SMA50 {c[-50:].mean():.2f} SMA200 {c[-200:].mean():.2f} · 5d {(pr / c[-6] - 1) * 100:+.1f}% · 1m {(pr / c[-22] - 1) * 100:+.1f}% · alarma {alarma} (-{dist * 100:.1f}%)")
print("::notice::GRAFICO " + estructura.frase(est))
print("::notice::FICHA " + ficha_frio.texto(f).replace("\n", " ")[:3000])
print("::notice::cartera: " + ", ".join(str(x.get("ticker")) for x in cart))
