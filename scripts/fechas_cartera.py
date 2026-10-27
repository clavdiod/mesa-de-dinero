"""Fechas de compra (y plazo) de lo que ya tenías cargado, para el seguimiento diario."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
cart = a.get("usuario/cartera") or []
datos = {"LRCX": {"fecha": "2026-10-26"}, "BAK": {"fecha": "2026-10-27"},
         "IREN": {"fecha": "2026-10-22", "vence": "2026-11-04", "plazo_motivo": "antes del balance del 05/11"}}
for x in cart:
    d = datos.get(str(x.get("ticker", "")).upper())
    if d:
        for k, v in d.items():
            x.setdefault(k, v)
a.put("usuario/cartera", cart)
print("::notice::" + json.dumps([x for x in cart if x.get("fecha")], ensure_ascii=False))
