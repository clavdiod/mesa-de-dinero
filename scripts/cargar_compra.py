"""Saca la línea de IREN duplicada (el usuario ya la había cargado desde la app)."""
import json

from mesa.nucleo.almacen import almacen_por_defecto

a = almacen_por_defecto()
cart = a.get("usuario/cartera") or []
cart = [x for x in cart if not (x.get("ticker") == "IREN" and x.get("fecha") == "2026-10-22")]
a.put("usuario/cartera", cart)
print("::notice::" + json.dumps(cart, ensure_ascii=False)[:1500])
