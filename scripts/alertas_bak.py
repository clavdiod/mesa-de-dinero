"""Alertas de BAK en la cartera (stop en el precio de compra, aviso antes, y toma de ganancia)."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
cart = a.get("usuario/cartera") or []
c = next(x for x in cart if str(x.get("ticker", "")).upper() == "BAK")
ids = {x.get("id") for x in c.get("alertas") or []}
for al in [{"id": "bak-c-sube-1100", "tipo": "sube", "nivel": 1100, "moneda": "ARS", "creada": "2026-10-28", "nota": "Tomar ganancia: vender la mitad (95)."},
           {"id": "bak-c-baja-1020", "tipo": "baja", "nivel": 1020, "moneda": "ARS", "creada": "2026-10-28", "nota": "Ojo: se acerca a tu precio de compra."},
           {"id": "bak-c-baja-988", "tipo": "baja", "nivel": 988, "moneda": "ARS", "creada": "2026-10-28", "nota": "Stop en tu precio de compra: salir sin perder."}]:
    if al["id"] not in ids:
        c.setdefault("alertas", []).append(al)
a.put("usuario/cartera", cart)
print("::notice::" + json.dumps(c, ensure_ascii=False))
