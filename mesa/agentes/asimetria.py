"""Agente asimétrico (12/11). Pedido de Clau a partir del posteo de Franco Tealdi (IEB): "soy fan de la asimetría".

La asimetría de un trade es cuánto podés ganar si la tesis se cumple contra cuánto podés perder si falla.
Se busca MUCHO para ganar y POCO para perder: ganar 30 y perder 10 es 3 a 1 (una ganancia compensa tres pérdidas).

Para los bonos soberanos en dólares, como en la tabla de Tealdi: comprás hoy y vendés en una fecha que pasa por el
evento que puede moverlos (las elecciones de 2027). Lo que recibís es lo que cobrás en el medio (cupones y
amortizaciones) más el precio de venta, que depende de la PARIDAD de salida (precio / valor técnico):
- pesimista: paridad 35%; reestructuración: 50%; optimista: 90%.
Cuanto más caen los bonos, menos queda para perder y más para ganar: la asimetría mejora sola. Ahí está el trade.
Solo información para decidir: no vota ni propone compras (no hay forma de probarlo con historia: depende de un evento).
"""
from __future__ import annotations

from datetime import date

SALIDA = "2027-10-29"  # vendés después de las elecciones de octubre de 2027
ESCENARIOS = {"pesimista": 0.35, "reestructuracion": 0.50, "optimista": 0.90}
BASES = ["AO27", "AO28", "AO29", "AN29", "GD29", "AL29", "GD30", "AL30", "GD35", "AL35", "GD38", "AE38", "GD41", "AL41", "GD46"]


def analizar(tk: str, precio: float, flujos: list[dict], hoy: date, salida: str = SALIDA) -> dict | None:
    """precio: en dólares por 100 nominales originales (como cotiza en BYMA)."""
    hoy_s = hoy.isoformat()
    fut = [f for f in flujos or [] if str(f.get("fecha"))[:10] > hoy_s]
    if not fut or not precio:
        return None
    residual_hoy = sum(float(f.get("amortizacion") or 0) for f in fut)
    cobrado = sum(float(f.get("interes") or 0) + float(f.get("amortizacion") or 0) for f in fut if str(f["fecha"])[:10] <= salida)
    residual_salida = sum(float(f.get("amortizacion") or 0) for f in fut if str(f["fecha"])[:10] > salida)
    vencimiento = max(str(f["fecha"])[:10] for f in fut)
    esc = {k: round(((p * residual_salida + cobrado) / precio - 1) * 100, 1) for k, p in ESCENARIOS.items()}
    gana, pierde = esc["optimista"], esc["pesimista"]
    ratio = round(gana / -pierde, 1) if pierde < 0 and gana > 0 else None
    if residual_salida == 0:
        lectura, color = f"Vence antes de la salida: cobrás todo ({_p((cobrado / precio - 1) * 100)}) pase lo que pase en la elección.", "verde"
    elif ratio is None:
        lectura, color = "Ni el escenario pesimista hace perder: sin riesgo de elección a este precio.", "verde"
    elif ratio >= 3:
        lectura, color = f"Asimétrico: ganás {_r(ratio)} veces lo que podés perder.", "verde"
    elif ratio >= 2:
        lectura, color = f"Aceptable: ganás {_r(ratio)} veces lo que podés perder.", "amar"
    else:
        lectura, color = f"No compensa todavía: ganás solo {_r(ratio)} veces lo que podés perder.", "rojo"
    return {"ticker": tk, "precio": round(precio, 2), "paridad": round(precio / residual_hoy * 100, 1) if residual_hoy else None,
            "vencimiento": vencimiento, "cobras_hasta_salida": round(cobrado, 2), "residual_salida": round(residual_salida, 2),
            "escenarios": esc, "ratio": ratio, "lectura": lectura, "color": color}


def _r(x: float) -> str:
    return f"{x:g}".replace(".", ",")


def _p(x: float) -> str:
    return f"{'+' if x > 0 else ''}{x:.1f}%".replace(".", ",")


def tabla(panel: dict, flujos: dict, hoy: date, tengo: set[str] | None = None) -> dict:
    """panel: {ticker: [ultimo, ...]} (ui/panel). Usa el precio en dólar cable (C) y si no hay, el MEP (D)."""
    filas = []
    for b in BASES:
        fl = (flujos.get(b) or {}).get("flujos")
        x = panel.get(b + "C") or panel.get(b + "D")
        if not fl or not x or not x[0]:
            continue
        r = analizar(b, float(x[0]), fl, hoy)
        if r:
            r["dolar"] = "CCL" if panel.get(b + "C") else "MEP"
            r["lo_tenes"] = bool(tengo and (b in tengo or b + "D" in tengo or b + "C" in tengo))
            filas.append(r)
    con_ratio = [f for f in filas if f["ratio"]]
    mejor = max(con_ratio, key=lambda f: f["ratio"]) if con_ratio else None
    resumen = (f"El más asimétrico hoy es {mejor['ticker']}: si sale bien ganás {_p(mejor['escenarios']['optimista'])}, "
               f"si sale mal perdés {_p(mejor['escenarios']['pesimista'])} ({_r(mejor['ratio'])} a 1).") if mejor else "Sin datos de precios."
    if mejor and mejor["ratio"] < 3:
        resumen += " Ninguno llega todavía a 3 a 1: si los bonos siguen bajando, la asimetría mejora."
    return {"fecha": hoy.isoformat(), "salida": SALIDA, "escenarios": ESCENARIOS, "filas": filas, "resumen": resumen}
