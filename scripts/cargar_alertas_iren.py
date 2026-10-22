"""Agrega IREN a favoritos con sus alertas de nivel (pedido del usuario, 22/10)."""
import json

from mesa.nucleo.almacen import almacen_por_defecto

a = almacen_por_defecto()
lista = a.get("usuario/lista") or []
it = next((x for x in lista if x.get("ticker") == "IREN"), None)
if not it:
    it = {"ticker": "IREN", "precio": None, "nota": "Compra 22/10"}
    lista.append(it)
nuevas = [{"id": "iren-sube-275", "tipo": "sube", "nivel": 27.5, "moneda": "USD", "creada": "2026-10-22", "nota": "Recupera la zona 27–28: para sumar la segunda parte."},
          {"id": "iren-baja-23", "tipo": "baja", "nivel": 23.0, "moneda": "USD", "creada": "2026-10-22", "nota": "Zona de stop: la caída sigue."},
          {"id": "iren-baja-204", "tipo": "baja", "nivel": 20.4, "moneda": "USD", "creada": "2026-10-22", "nota": "Objetivo bajista de los técnicos."}]
ids = {x.get("id") for x in it.get("alertas") or []}
it.setdefault("alertas", []).extend(x for x in nuevas if x["id"] not in ids)
a.put("usuario/lista", lista)
print("::notice::" + json.dumps(it, ensure_ascii=False))
