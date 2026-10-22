"""Carga una compra del usuario en "Lo que tengo" (IREN, 22/10)."""
import json

from mesa.nucleo.almacen import almacen_por_defecto

a = almacen_por_defecto()
cart = a.get("usuario/cartera") or []
if not any(x.get("ticker") == "IREN" and x.get("fecha") == "2026-10-22" for x in cart):
    cart.append({"ticker": "IREN", "cantidad": 50, "precio": 3495, "fecha": "2026-10-22"})
    a.put("usuario/cartera", cart)
print("::notice::" + json.dumps(cart, ensure_ascii=False)[:1500])
